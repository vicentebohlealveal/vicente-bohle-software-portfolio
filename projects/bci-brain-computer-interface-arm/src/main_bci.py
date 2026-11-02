"""
main_bci.py - BCI Muse S -> brazo robotico (ESP32 por UDP)

  Embrague   : parpadeo voluntario (EMG en AF7/AF8) -> cambia el eje activo
  Acelerador : indice log10(beta/alfa) en TP9/TP10 -> angulo del eje activo
  Seguridad  : calidad de senal + movimiento (acelerometro) -> 'armed'=0

Protocolo UDP (texto, 20 Hz):  "<eje>,<angulo 0-180>,<armed 0|1>\n"

Uso:
  pixi run python main_bci.py --dry-run               # sin ESP32, solo imprime
  pixi run python main_bci.py --ip 192.168.1.50 --calibrate
"""
import argparse
import json
import socket
import time
from collections import deque
from pathlib import Path

import numpy as np
from scipy import signal
from brainflow.board_shim import (BoardShim, BrainFlowInputParams, BoardIds,
                                  BrainFlowPresets, LogLevels)
from brainflow.exit_codes import BrainFlowError
from brainflow.data_filter import DataFilter, WindowOperations

# ----------------------------- Configuracion -------------------------------
BOARD_ID = BoardIds.MUSE_S_BOARD.value          # 21
FS = BoardShim.get_sampling_rate(BOARD_ID)      # 256 Hz
EEG_ROWS = BoardShim.get_eeg_channels(BOARD_ID)  # orden Muse: TP9, AF7, AF8, TP10
TP9, AF7, AF8, TP10 = EEG_ROWS
AUX = BrainFlowPresets.AUXILIARY_PRESET.value      # el acelerometro vive en otro preset (52 Hz)
ACC_ROWS = BoardShim.get_accel_channels(BOARD_ID, AUX)

N_AXES = 4
TICK_S = 0.05            # lazo principal a 20 Hz
TX_PERIOD_S = 0.05       # envio UDP / heartbeat
WARMUP_S = 3.0           # transitorio de filtros al iniciar

# Parpadeo (embrague)
ENV_WIN_S = 0.25         # ventana de media movil de la envolvente
BLINK_ON_UV = 200.0      # umbral de disparo (tu umbral actual)
BLINK_OFF_UV = 120.0     # histeresis: baja de aqui para rearmar
REFRACTORY_S = 0.8       # tiempo minimo entre cambios de eje
FREEZE_S = 1.0           # congela el acelerador tras un parpadeo (artefacto)

# Acelerador (Alfa/Beta)
WIN_S = 2.0              # ventana de analisis (512 muestras)
IDX_PERIOD_S = 0.25      # cada cuanto se recalcula el indice
EMA = 0.2                # suavizado del indice normalizado
CALIB_FILE = Path("calib.json")
CALIB_S = 15

# Seguridad
MIN_STD_UV, MAX_STD_UV = 0.5, 150.0   # TP9/TP10 en 1 s: plano o saturado => mala senal
MOTION_STD_G = 0.10                   # desviacion de |acc| => movimiento de cabeza
ACC_N = 52                            # ~1 s de acelerometro (Muse ~52 Hz)


# ------------------------------ Deteccion EMG -------------------------------
class BlinkDetector:
    """Bandpass 1-45 Hz + notch 50 Hz + |x| + media movil, todo causal con estado."""

    def __init__(self, on_uv=BLINK_ON_UV, off_uv=BLINK_OFF_UV):
        self.on_uv, self.off_uv = on_uv, off_uv
        bp = signal.butter(4, [1.0, 45.0], btype="bandpass", fs=FS, output="sos")
        b, a = signal.iirnotch(50.0, 30.0, fs=FS)           # red de 50 Hz (Chile)
        self.sos = np.vstack([bp, signal.tf2sos(b, a)])
        self.zi = None
        n = int(ENV_WIN_S * FS)
        self.ma_b = np.ones(n) / n
        self.ma_zi = np.zeros(n - 1)
        self.active = False
        self.last_blink = -1e9
        self.env = 0.0

    def envelope(self, af7, af8):
        x = (af7 + af8) / 2.0
        if self.zi is None:                                  # evita transitorio por DC
            self.zi = signal.sosfilt_zi(self.sos) * x[0]
        y, self.zi = signal.sosfilt(self.sos, x, zi=self.zi)
        env, self.ma_zi = signal.lfilter(self.ma_b, [1.0], np.abs(y), zi=self.ma_zi)
        return env

    def update(self, af7, af8, now):
        env = self.envelope(af7, af8)
        blinks = 0
        for e in env:
            if not self.active and e > self.on_uv and now - self.last_blink > REFRACTORY_S:
                self.active, self.last_blink = True, now
                blinks += 1
            elif self.active and e < self.off_uv:
                self.active = False
        self.env = float(env[-1])
        return blinks


# ------------------------------ Indice Alfa/Beta ----------------------------
class BandIndex:
    """log10(potencia beta / potencia alfa) promediado en TP9 y TP10."""

    def __init__(self):
        self.n = int(WIN_S * FS)
        self.buf = {"TP9": deque(maxlen=self.n), "TP10": deque(maxlen=self.n)}

    def clear(self):
        for q in self.buf.values():
            q.clear()

    def push(self, tp9, tp10):
        self.buf["TP9"].extend(tp9)
        self.buf["TP10"].extend(tp10)

    def compute(self):
        if any(len(q) < self.n for q in self.buf.values()):
            return None
        vals = []
        for q in self.buf.values():
            x = np.asarray(q, dtype=np.float64)
            x = x - x.mean()
            psd = DataFilter.get_psd_welch(x, 256, 128, FS, WindowOperations.HANNING.value)
            alfa = DataFilter.get_band_power(psd, 8.0, 12.0)
            beta = DataFilter.get_band_power(psd, 13.0, 30.0)
            vals.append(np.log10((beta + 1e-9) / (alfa + 1e-9)))
        return float(np.mean(vals))


def calibrate(board, bi):
    """Mide el indice en reposo (lo) y en concentracion (hi) y lo guarda."""
    out = {}
    pasos = (
        ("lo", "RELAJADO (ojos cerrados o mirada suave, sin pensar en nada)"),
        ("hi", "CONCENTRADO (ojos abiertos, resta mental 100-7-7-7...)"),
    )
    for clave, texto in pasos:
        input(f"\nProximo: {texto}\nENTER para comenzar ({CALIB_S} s)... ")
        board.get_board_data()
        bi.clear()
        vals, t0 = [], time.time()
        while time.time() - t0 < CALIB_S + WIN_S:
            time.sleep(IDX_PERIOD_S)
            d = board.get_board_data()
            bi.push(d[TP9], d[TP10])
            v = bi.compute()
            if v is not None:
                vals.append(v)
        out[clave] = float(np.median(vals))
        print(f"  indice {clave} = {out[clave]:.3f}")
    if out["hi"] - out["lo"] < 0.05:
        print("AVISO: rango muy pequeno; repite la calibracion (mejor contacto de sensores).")
    CALIB_FILE.write_text(json.dumps(out))
    return out


def calibrate_blink(board):
    """Mide la envolvente de 3 parpadeos voluntarios y fija el umbral al 50 % del pico."""
    input("\nProximo: PARPADEOS. Parpadea 3 veces de forma voluntaria y marcada, "
          "con ~2 s entre cada uno.\nENTER para comenzar (10 s)... ")
    board.get_board_data()
    det = BlinkDetector()
    envs, t0 = [], time.time()
    while time.time() - t0 < 10:
        time.sleep(TICK_S)
        d = board.get_board_data()
        if d.shape[1]:
            envs.append(det.envelope(d[AF7], d[AF8]))
    env = np.concatenate(envs)[FS:]                  # descarta 1 s de transitorio
    _, props = signal.find_peaks(env, height=20.0, distance=FS)
    if len(props["peak_heights"]) < 2:
        print(f"AVISO: no se detectaron picos claros; uso umbral por defecto ({BLINK_ON_UV:.0f} uV).")
        return BLINK_ON_UV
    top = np.sort(props["peak_heights"])[-3:]
    on = max(0.5 * float(np.median(top)), 30.0)
    print(f"  picos de envolvente: {np.round(top, 0)} uV -> umbral = {on:.0f} uV")
    return on


def connect(params, retries=4):
    """prepare_session con reintentos: la busqueda BLE a veces no ve el Muse a la primera."""
    for i in range(1, retries + 1):
        board = BoardShim(BOARD_ID, params)
        try:
            board.prepare_session()
            return board
        except BrainFlowError as e:
            print(f"Intento {i}/{retries} fallido ({e}). Reintentando en 2 s...")
            time.sleep(2)
    raise SystemExit("No se pudo conectar. Enciende el Muse, cierra la app Muse del celular y reintenta.")


# ------------------------------- Seguridad ---------------------------------
def signal_stats(h9, h10):
    """(ok, std_TP9, std_TP10) tras quitar la deriva lenta de la ventana de ~1 s."""
    stds = []
    for q in (h9, h10):
        if len(q) < FS // 2:
            return False, 0.0, 0.0
        stds.append(float(np.std(signal.detrend(np.asarray(q, dtype=np.float64)))))
    ok = all(MIN_STD_UV <= v <= MAX_STD_UV for v in stds)
    return ok, stds[0], stds[1]


# --------------------------------- Main ------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="192.168.1.50", help="IP del ESP32")
    ap.add_argument("--port", type=int, default=4210)
    ap.add_argument("--mac", default="", help="MAC del Muse S (opcional)")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="no envia UDP")
    args = ap.parse_args()

    BoardShim.set_log_level(LogLevels.LEVEL_WARN.value)   # solo avisos y errores
    params = BrainFlowInputParams()
    params.timeout = 15                                    # busqueda BLE (antes: 6 s)
    if args.mac:
        params.mac_address = args.mac
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.ip, args.port)

    def send(axis, angle, armed):
        if not args.dry_run:
            sock.sendto(f"{axis},{angle:.1f},{int(armed)}\n".encode(), dest)

    print("Conectando al Muse S...")
    board = connect(params)
    board.start_stream()
    try:
        time.sleep(2.0)
        bi = BandIndex()

        if args.calibrate or not CALIB_FILE.exists():
            cal = calibrate(board, bi)
            cal["blink_on"] = calibrate_blink(board)
            CALIB_FILE.write_text(json.dumps(cal))
        else:
            cal = json.loads(CALIB_FILE.read_text())
        lo, hi = cal["lo"], max(cal["hi"], cal["lo"] + 1e-3)
        on = cal.get("blink_on", BLINK_ON_UV)
        blink = BlinkDetector(on, 0.6 * on)               # detector nuevo, sin estado viejo

        axis, u = 0, 0.5
        angles = [90.0] * N_AXES            # ultimo angulo comandado por eje
        freeze_until = 0.0
        h9, h10 = deque(maxlen=FS), deque(maxlen=FS)
        acc_hist = deque(maxlen=ACC_N)
        acc_warned = False
        t0 = last_idx = last_tx = last_log = time.time()
        board.get_board_data()
        bi.clear()
        print(f"Listo. Eje activo: {axis}. Parpadea para cambiar de eje. Ctrl+C para salir.")

        while True:
            time.sleep(TICK_S)
            d = board.get_board_data()
            if d.shape[1] == 0:
                continue
            now = time.time()
            warm = now - t0 > WARMUP_S

            # --- Embrague: parpadeo => siguiente eje ---
            n_blinks = blink.update(d[AF7], d[AF8], now)
            if warm and n_blinks:
                axis = (axis + 1) % N_AXES
                u = angles[axis] / 180.0            # el nuevo eje parte de su angulo actual
                print(f"[BLINK] eje activo -> {axis}")
            if warm and (n_blinks or blink.active):
                freeze_until = now + FREEZE_S

            # --- Acelerador: indice alfa/beta -> u en [0,1] ---
            bi.push(d[TP9], d[TP10])
            if now - last_idx >= IDX_PERIOD_S:
                last_idx = now
                v = bi.compute()
                if v is not None and now > freeze_until:
                    norm = float(np.clip((v - lo) / (hi - lo), 0.0, 1.0))
                    u = (1 - EMA) * u + EMA * norm

            # --- Seguridad ---
            h9.extend(d[TP9])
            h10.extend(d[TP10])
            a = board.get_board_data(preset=AUX)    # acelerometro: arreglo aparte, 52 Hz
            if a.shape[1]:
                acc_hist.extend(np.linalg.norm(a[ACC_ROWS], axis=0))
            if now - t0 > 5.0 and not acc_hist and not acc_warned:
                print("AVISO: no llegan datos del acelerometro; la proteccion por movimiento esta INACTIVA.")
                acc_warned = True
            moving = len(acc_hist) >= 10 and float(np.std(acc_hist)) > MOTION_STD_G
            sig_ok, s9, s10 = signal_stats(h9, h10)
            armed = warm and sig_ok and not moving and now > freeze_until

            if armed:
                angles[axis] = u * 180.0

            # --- Envio (tambien actua como heartbeat) ---
            if now - last_tx >= TX_PERIOD_S:
                last_tx = now
                send(axis, angles[axis], armed)

            if now - last_log > 0.5:
                last_log = now
                print(f"eje={axis} ang={angles[axis]:5.1f} env={blink.env:6.1f}uV "
                      f"armed={int(armed)} sig={int(sig_ok)} mov={int(moving)} "
                      f"tp9={s9:.0f} tp10={s10:.0f}uV")
    except KeyboardInterrupt:
        pass
    finally:
        send(0, 90.0, False)                         # desarma el brazo
        board.stop_stream()
        board.release_session()
        print("\nSesion cerrada.")


if __name__ == "__main__":
    main()
