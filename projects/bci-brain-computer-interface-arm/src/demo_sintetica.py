"""
demo_sintetica.py - Prueba la interfaz de bci_gui.py SIN diadema Muse ni ESP32.

Reemplaza la Muse S por una placa falsa que genera EEG sintetico:
  - la relacion beta/alfa sube y baja lentamente (simula concentrarse y relajarse);
  - cada cierto tiempo aparece un parpadeo fuerte en AF7/AF8 (cambia el eje activo).
El resto (filtros, indice, deteccion de parpadeos, seguridad, gemelo digital) es el
codigo real de main_bci.py y bci_gui.py.

Uso (desde esta carpeta):
  pixi run python demo_sintetica.py               # ventana en vivo
  pixi run python demo_sintetica.py --gif demo    # guarda cuadros PNG en ./demo para armar un GIF
"""
import argparse
import os
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--gif", default="", help="carpeta donde guardar cuadros PNG (modo sin ventana)")
ap.add_argument("--segundos", type=float, default=28.0)
args = ap.parse_args()

# En modo GIF se usa un reloj simulado para que el resultado no dependa del PC.
clock = [time.time()]
if args.gif:
    import matplotlib
    matplotlib.use("Agg")
    time.time = lambda: clock[0]

import matplotlib.pyplot as plt  # noqa: E402
from bci_gui import FS, Dashboard, Engine, Twin  # noqa: E402

rng = np.random.default_rng(3)


class FakeMuse:
    """Imita BoardShim.get_board_data() de la Muse S: 4 canales EEG a 256 Hz + acelerometro a 52 Hz."""

    def __init__(self):
        self.t0 = self.t = self.ta = time.time()

    def get_board_data(self, preset=None):
        now = time.time()
        if preset is not None:  # acelerometro (preset auxiliar): cabeza quieta, |acc| ~ 1 g
            n = int((now - self.ta) * 52)
            self.ta += n / 52
            d = np.zeros((9, n))
            d[3] = 1 + rng.normal(0, 0.01, n)
            return d
        n = int((now - self.t) * FS)
        t = self.t + np.arange(n) / FS
        self.t += n / FS
        d = np.zeros((8, n))
        rel = t - self.t0
        focus = 0.5 + 0.45 * np.sin(2 * np.pi * rel / 14.0)
        for ch in (1, 2, 3, 4):  # TP9, AF7, AF8, TP10
            alpha = (1.2 - focus) * 18 * np.sin(2 * np.pi * 10 * t + ch)
            beta = (0.4 + focus) * 9 * np.sin(2 * np.pi * 20 * t + 2 * ch)
            d[ch] = alpha + beta + rng.normal(0, 4, n)
        for tb in (6.0, 13.0, 21.0, 30.0, 38.0):  # parpadeos voluntarios
            m = np.abs((rel % 45.0) - tb) < 0.15
            if m.sum():
                d[2][m] += 1100 * np.hanning(m.sum())
                d[3][m] += 1100 * np.hanning(m.sum())
        return d


eng, twin = Engine(FakeMuse(), lambda *a: None), Twin()
eng.lo, eng.hi = -1.0, 0.6
eng.msg = "DEMO: senal EEG sintetica (sin Muse)"
dash = Dashboard(eng, twin)
dash.fig.suptitle("BCI Muse S -> brazo robotico | gemelo digital (demo con senal EEG sintetica)", fontsize=11)

last, frame = time.time(), 0
if args.gif:
    os.makedirs(args.gif, exist_ok=True)
    start = clock[0]
    for i in range(int(args.segundos / 0.05)):
        clock[0] += 0.05
        eng.step()
        twin.step(clock[0] - last, eng.armed, eng.axis, eng.angles[eng.axis])
        last = clock[0]
        if i % 4 == 0 and clock[0] - start > 3:
            dash.update()
            dash.fig.canvas.draw()
            dash.fig.savefig(os.path.join(args.gif, f"f{frame:04d}.png"), dpi=72)
            frame += 1
    print(f"{frame} cuadros guardados en {args.gif}/")
else:
    while plt.fignum_exists(dash.fig.number):
        eng.step()
        now = time.time()
        twin.step(now - last, eng.armed, eng.axis, eng.angles[eng.axis])
        last = now
        dash.update()
        plt.pause(0.05)
