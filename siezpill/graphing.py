import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from drivers import Max30102HeartMonitor


app = QtWidgets.QApplication(sys.argv)

monitor = Max30102HeartMonitor(window=500, sample_rate=100)
monitor.setup()

win = pg.GraphicsLayoutWidget(show=True, title="Heart Monitor")

plot = win.addPlot(title="IR Heartbeat Signal")
plot.showGrid(x=True, y=True)
plot.setLabel("left", "IR amplitude")
plot.setLabel("bottom", "Samples")

curve = plot.plot(pen="r")

# Text overlay
status_text = pg.TextItem(anchor=(0, 0))
plot.addItem(status_text)
status_text.setPos(5, 5)

# Keep a fixed-size display buffer
display_size = monitor.window
display_data = np.zeros(display_size, dtype=float)

def update():
    global display_data

    monitor.update()

    latest_ir = monitor.get_latest_ir()

    # Push newest value into plotting buffer
    display_data = np.roll(display_data, -1)
    display_data[-1] = latest_ir

    # Remove large DC offset for visualization
    centered = display_data.copy()
    nonzero = centered[centered != 0]
    if len(nonzero) > 0:
        centered = centered - np.mean(nonzero)

    curve.setData(centered)

    # Auto-range nicely once data exists
    if len(nonzero) > 10:
        ymin = float(np.min(centered))
        ymax = float(np.max(centered))
        if ymin != ymax:
            margin = max(100.0, (ymax - ymin) * 0.2)
            plot.setYRange(ymin - margin, ymax + margin)

    attached = monitor.is_attached()
    bpm = monitor.get_heart_rate()
    spo2 = monitor.get_spo2()
    red = monitor.get_latest_red()
    ir = monitor.get_latest_ir()

    status_text.setText(
        f"Attached: {attached}\n"
        f"BPM: {bpm}\n"
        f"SpO2: {spo2}%\n"
        f"IR: {ir}\n"
        f"RED: {red}"
    )

    win.setWindowTitle(
        f"Heart Monitor | Attached: {attached} | BPM: {bpm} | SpO2: {spo2}%"
    )

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(20)

exit_code = app.exec()
monitor.close()
sys.exit(exit_code)