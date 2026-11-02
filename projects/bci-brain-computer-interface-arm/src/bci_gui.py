"""
bci_gui.py - Interfaz en vivo: BCI Muse S + gemelo digital del brazo (3 ejes + pinza)

Muestra: brazo simulado (vista lateral + vista superior de la base), el indice
beta/alfa en tiempo real con tus limites de calibracion, y el estado de seguridad.
El brazo simulado imita al ESP32 real (misma velocidad maxima de 60 deg/s).

Teclas:  1 = calibrar RELAJADO     2 = calibrar CONCENTRADO     3 = calibrar PARPADEOS
         0 = brazo a posicion inicial                           q = salir

Uso (necesita main_bci.py en la misma carpeta):
  pixi run python bci_gui.py                          # solo simulacion
  pixi run python bci_gui.py --ip 192.168.1.50        # simulacion + envia al ESP32
"""
import argparse
import json
import socket
import time
from collections import deque

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy import signal
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels

from main_bci import (FS, AF7, AF8, TP9, TP10, AUX, ACC_ROWS, N_AXES, WARMUP_S,
                      FREEZE_S, IDX_PERIOD_S, EMA, WIN_S, CALIB_S, CALIB_FILE,
                      BLINK_ON_UV, TX_PERIOD_S, ACC_N, MOTION_STD_G, TICK_S,
                      BlinkDetector, BandIndex, signal_stats, connect)

NAMES = ["BASE (giro)", "HOMBRO", "CODO", "PINZA"]
L1, L2, LG = 1.0, 0.85, 0.35          # largo brazo, antebrazo, dedos de la pinza
MAX_SPEED_DPS = 60.0                  # igual que el firmware del ESP32
HINTS = {
    "relax": "RELAJATE: suelta la mandibula, mirada suave, respira lento",
    "focus": "CONCENTRATE: ojos abiertos, resta de 7 en 7 desde 1000",
    "blink": "PARPADEA 3 veces, marcado, con ~2 s entre cada uno",
}


# ------------------------------- Motor BCI ---------------------------------
class Engine:
    """Misma logica que main_bci.py, pero por pasos (sin bloquear) y calibrable en vivo."""

    def __init__(self, board, send):
        self.board, self.send = board, send
        self.bi = BandIndex()
        self.lo, self.hi, self.blink_on = 0.2, 0.5, BLINK_ON_UV
        self.msg = "SIN CALIBRAR: usa las teclas 1, 2 y 3"
        if CALIB_FILE.exists():
            c = json.loads(CALIB_FILE.read_text())
            self.lo, self.hi = c["lo"], c["hi"]
            self.blink_on = c.get("blink_on", BLINK_ON_UV)
            self.msg = "Calibracion cargada de calib.json"
        self.blink = BlinkDetector(self.blink_on, 0.6 * self.blink_on)
        self.axis, self.u, self.v, self.norm = 0, 0.5, None, 0.5
        self.angles = [90.0] * N_AXES
        self.freeze_until = 0.0
        self.h9, self.h10 = deque(maxlen=FS), deque(maxlen=FS)
        self.acc_hist = deque(maxlen=ACC_N)
        self.hist = deque(maxlen=150)                    # (t, indice) ~30 s
        self.t0 = self.last_idx = self.last_tx = time.time()
        self.armed, self.reason = False, "calentando"
        self.s9 = self.s10 = 0.0
        self.cal_task = None
        board.get_board_data()
        board.get_board_data(preset=AUX)

    # --- calibracion no bloqueante ---
    def start_cal(self, name):
        dur = 10.0 if name == "blink" else CALIB_S + WIN_S
        self.board.get_board_data()
        self.bi.clear()
        if name == "blink":
            self.blink = BlinkDetector()
        self.cal_task = dict(name=name, t_end=time.time() + dur, dur=dur, vals=[], env=[])

    def _finish_cal(self):
        t, name = self.cal_task, self.cal_task["name"]
        self.cal_task = None
        if name in ("relax", "focus"):
            if len(t["vals"]) < 5:
                self.msg = "Muy pocos datos, repite la calibracion"
            else:
                val = float(np.median(t["vals"]))
                if name == "relax":
                    self.lo = val
                else:
                    self.hi = val
                self.msg = f"Guardado {'relajado' if name == 'relax' else 'concentrado'}: {val:.3f}"
        else:
            env = np.concatenate(t["env"])[FS:] if t["env"] else np.array([])
            _, props = signal.find_peaks(env, height=20.0, distance=FS) if env.size else (0, {"peak_heights": []})
            if len(props["peak_heights"]) < 2:
                self.msg = "No vi 3 parpadeos claros; se mantiene el umbral anterior"
            else:
                top = np.sort(props["peak_heights"])[-3:]
                self.blink_on = max(0.5 * float(np.median(top)), 30.0)
                self.msg = f"Umbral de parpadeo = {self.blink_on:.0f} uV"
        self.blink = BlinkDetector(self.blink_on, 0.6 * self.blink_on)
        CALIB_FILE.write_text(json.dumps(dict(lo=self.lo, hi=self.hi, blink_on=self.blink_on)))
        if self.hi - self.lo < 0.05:
            self.msg += "  | AVISO: rango lo-hi muy chico"

    # --- un paso del lazo ---
    def step(self):
        d = self.board.get_board_data()
        now = time.time()
        if d.shape[1] == 0:
            return
        warm = now - self.t0 > WARMUP_S
        cal = self.cal_task
        calibrating = cal is not None

        if calibrating and cal["name"] == "blink":
            env = self.blink.envelope(d[AF7], d[AF8])
            cal["env"].append(env)
            self.blink.env = float(env[-1])
            n_b = 0
        else:
            n_b = self.blink.update(d[AF7], d[AF8], now)

        if warm and not calibrating:
            if n_b:
                self.axis = (self.axis + 1) % N_AXES
                self.u = self.angles[self.axis] / 180.0
            if n_b or self.blink.active:
                self.freeze_until = now + FREEZE_S

        self.bi.push(d[TP9], d[TP10])
        if now - self.last_idx >= IDX_PERIOD_S:
            self.last_idx = now
            v = self.bi.compute()
            if v is not None:
                self.v = v
                self.hist.append((now, v))
                if calibrating and cal["name"] in ("relax", "focus"):
                    cal["vals"].append(v)
                hi = max(self.hi, self.lo + 1e-3)
                self.norm = float(np.clip((v - self.lo) / (hi - self.lo), 0.0, 1.0))
                if now > self.freeze_until:
                    self.u = (1 - EMA) * self.u + EMA * self.norm

        self.h9.extend(d[TP9])
        self.h10.extend(d[TP10])
        a = self.board.get_board_data(preset=AUX)
        if a.shape[1]:
            self.acc_hist.extend(np.linalg.norm(a[ACC_ROWS], axis=0))
        self.moving = len(self.acc_hist) >= 10 and float(np.std(self.acc_hist)) > MOTION_STD_G
        self.sig_ok, self.s9, self.s10 = signal_stats(self.h9, self.h10)

        if not warm:
            self.reason = "calentando"
        elif calibrating:
            self.reason = "calibrando"
        elif not self.sig_ok:
            self.reason = "senal mala"
        elif self.moving:
            self.reason = "movimiento de cabeza"
        elif now <= self.freeze_until:
            self.reason = "artefacto de parpadeo"
        else:
            self.reason = "OK"
        self.armed = self.reason == "OK"

        if self.armed:
            self.angles[self.axis] = self.u * 180.0
        if now - self.last_tx >= TX_PERIOD_S:
            self.last_tx = now
            self.send(self.axis, self.angles[self.axis], self.armed)

        if calibrating and now >= cal["t_end"]:
            self._finish_cal()


# --------------------------- Gemelo digital del brazo ----------------------
class Twin:
    def __init__(self):
        self.actual = np.full(N_AXES, 90.0)
        self.target = self.actual.copy()

    def home(self):
        self.actual[:] = 90.0
        self.target[:] = 90.0

    def step(self, dt, armed, axis, angle):
        if armed:
            self.target[axis] = angle
        else:
            self.target[:] = self.actual          # el ESP32 se congela al desarmar
        lim = MAX_SPEED_DPS * dt
        self.actual += np.clip(self.target - self.actual, -lim, lim)


def fk(a):
    """Cinematica directa lateral. 90/90 = brazo vertical y recto."""
    th1 = np.radians(a[1])                        # 0 = derecha, 90 = arriba
    th2 = th1 + np.radians(a[2] - 90.0)           # 90 = antebrazo alineado
    s = np.array([0.0, 0.3])
    e = s + L1 * np.array([np.cos(th1), np.sin(th1)])
    w = e + L2 * np.array([np.cos(th2), np.sin(th2)])
    return s, e, w, th2


# --------------------------------- Interfaz --------------------------------
class Dashboard:
    def __init__(self, eng, twin):
        self.eng, self.twin = eng, twin
        plt.ion()
        self.fig = plt.figure(figsize=(12.5, 6.8))
        try:
            self.fig.canvas.manager.set_window_title("BCI Muse S - gemelo digital del brazo")
        except Exception:
            pass
        gs = self.fig.add_gridspec(3, 2, width_ratios=[1.15, 1], height_ratios=[3, 0.7, 2.3],
                                   hspace=0.5, wspace=0.15, left=0.03, right=0.98,
                                   top=0.92, bottom=0.06)

        # brazo (vista lateral)
        a = self.ax_arm = self.fig.add_subplot(gs[:, 0])
        a.set_xlim(-2.2, 2.2)
        a.set_ylim(-0.3, 2.7)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        a.axhline(0, color="0.4", lw=3)
        a.add_patch(Rectangle((-0.35, 0), 0.7, 0.3, color="0.6"))
        self.ghost, = a.plot([], [], "--", color="tab:blue", alpha=0.35, lw=5)
        self.link, = a.plot([], [], "-", color="tab:blue", lw=8, solid_capstyle="round")
        self.jaws = [a.plot([], [], "-", color="tab:green", lw=5)[0] for _ in range(2)]
        self.joints = [a.plot([], [], "o", ms=13, color="0.55", zorder=5)[0] for _ in range(N_AXES)]

        # vista superior (giro de la base)
        t = a.inset_axes([0.66, 0.62, 0.32, 0.36])
        t.set_xlim(-1.2, 1.2)
        t.set_ylim(-0.2, 1.2)
        t.set_aspect("equal")
        t.set_xticks([])
        t.set_yticks([])
        t.set_title("Base (vista superior)", fontsize=8)
        th = np.linspace(0, np.pi, 50)
        t.plot(np.cos(th), np.sin(th), color="0.8")
        self.top_line, = t.plot([0, 0], [0, 1], lw=4, color="tab:blue")

        # indice en el tiempo
        i = self.ax_idx = self.fig.add_subplot(gs[0, 1])
        i.set_title("Indice log10(beta/alfa) en TP9+TP10", fontsize=10)
        i.set_xlim(-30, 0)
        i.set_xlabel("segundos", fontsize=8)
        self.l_idx, = i.plot([], [], color="tab:blue", lw=1.5)
        self.l_lo = i.axhline(0, color="tab:green", ls="--")
        self.l_hi = i.axhline(0, color="tab:red", ls="--")
        i.legend([self.l_idx, self.l_lo, self.l_hi],
                 ["indice", "relajado (lo)", "concentrado (hi)"], loc="upper left", fontsize=8)

        # barra normalizada
        b = self.ax_bar = self.fig.add_subplot(gs[1, 1])
        b.set_xlim(0, 1)
        b.set_ylim(0, 1)
        b.set_yticks([])
        b.set_xticks([0, 0.5, 1])
        b.set_xticklabels(["relajado", "", "concentrado"], fontsize=8)
        self.bar = Rectangle((0, 0.1), 0.5, 0.8, color="tab:orange")
        b.add_patch(self.bar)

        # panel de texto
        x = self.ax_txt = self.fig.add_subplot(gs[2, 1])
        x.axis("off")
        self.txt = x.text(0, 1, "", va="top", family="monospace", fontsize=9)

        self.fig.canvas.mpl_connect("key_press_event", self.on_key)

    def on_key(self, ev):
        if ev.key in ("1", "2", "3") and self.eng.cal_task is None:
            self.eng.start_cal({"1": "relax", "2": "focus", "3": "blink"}[ev.key])
        elif ev.key == "0":
            self.eng.angles = [90.0] * N_AXES
            self.eng.u = 0.5
            self.twin.home()

    def update(self):
        e, tw, now = self.eng, self.twin, time.time()

        # brazo real simulado + fantasma de la consigna
        s, el, w, th2 = fk(tw.actual)
        self.link.set_data([s[0], el[0], w[0]], [s[1], el[1], w[1]])
        sg, eg, wg, _ = fk(tw.target)
        self.ghost.set_data([sg[0], eg[0], wg[0]], [sg[1], eg[1], wg[1]])
        phi = np.radians(tw.actual[3] / 180.0 * 40.0)
        for jaw, sign in zip(self.jaws, (1, -1)):
            tip = w + LG * np.array([np.cos(th2 + sign * phi), np.sin(th2 + sign * phi)])
            jaw.set_data([w[0], tip[0]], [w[1], tip[1]])
        pts = [(0.0, 0.05), tuple(s), tuple(el), tuple(w)]
        for k, (j, p) in enumerate(zip(self.joints, pts)):
            j.set_data([p[0]], [p[1]])
            j.set_color("tab:orange" if k == e.axis else "0.55")
        a0 = np.radians(tw.actual[0])
        self.top_line.set_data([0, np.cos(a0)], [0, np.sin(a0)])

        flash = " [PARPADEO]" if now - e.blink.last_blink < 0.6 else ""
        self.ax_arm.set_title(f"Eje activo: {NAMES[e.axis]}{flash}", fontsize=13,
                              color="tab:green" if e.armed else "tab:red")

        # indice
        if e.hist:
            ts = np.array([t - now for t, _ in e.hist])
            vs = np.array([v for _, v in e.hist])
            self.l_idx.set_data(ts, vs)
            self.ax_idx.set_ylim(min(e.lo, vs.min()) - 0.1, max(e.hi, vs.max()) + 0.1)
        self.l_lo.set_ydata([e.lo, e.lo])
        self.l_hi.set_ydata([e.hi, e.hi])
        self.bar.set_width(e.u)

        # texto
        if e.cal_task:
            c = e.cal_task
            rest = max(0.0, c["t_end"] - now)
            cal_line = f"CALIBRANDO ({rest:3.0f} s)\n{HINTS[c['name']]}"
        else:
            cal_line = e.msg
        v_txt = f"{e.v:+.3f}" if e.v is not None else "  -- "
        self.txt.set_text("\n".join([
            f"Eje activo   : {e.axis} - {NAMES[e.axis]}",
            "Angulos (deg): " + "  ".join(f"{x:5.1f}" for x in tw.actual),
            f"Armado       : {'SI' if e.armed else 'NO'}  ({e.reason})",
            f"Senal TP9/10 : {e.s9:4.0f} / {e.s10:4.0f} uV   (valido 0.5-150)",
            f"Parpadeo EMG : {e.blink.env:5.1f} uV   umbral {e.blink.on_uv:.0f} uV",
            f"Indice       : {v_txt}   normalizado {e.norm:.2f}",
            "",
            cal_line,
            "",
            "[1] relajado  [2] concentrado  [3] parpadeos  [0] inicio  [q] salir",
        ]))
        self.fig.canvas.draw_idle()


# ----------------------------------- Main ----------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="", help="IP del ESP32 (si se omite, solo simula)")
    ap.add_argument("--port", type=int, default=4210)
    ap.add_argument("--mac", default="")
    args = ap.parse_args()

    BoardShim.set_log_level(LogLevels.LEVEL_WARN.value)
    params = BrainFlowInputParams()
    params.timeout = 15
    if args.mac:
        params.mac_address = args.mac
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(axis, angle, armed):
        if args.ip:
            sock.sendto(f"{axis},{angle:.1f},{int(armed)}\n".encode(), (args.ip, args.port))

    print("Conectando al Muse S...")
    board = connect(params)
    board.start_stream()
    try:
        time.sleep(2.0)
        eng, twin = Engine(board, send), Twin()
        dash = Dashboard(eng, twin)
        last = time.time()
        while plt.fignum_exists(dash.fig.number):
            eng.step()
            now = time.time()
            twin.step(now - last, eng.armed, eng.axis, eng.angles[eng.axis])
            last = now
            dash.update()
            plt.pause(TICK_S)
    except KeyboardInterrupt:
        pass
    finally:
        send(0, 90.0, False)
        board.stop_stream()
        board.release_session()
        print("Sesion cerrada.")


if __name__ == "__main__":
    main()
