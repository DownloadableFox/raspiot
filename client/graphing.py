import sys
import json
import asyncio
import threading
import numpy as np
import pyqtgraph as pg
import websockets
from pyqtgraph.Qt import QtCore, QtWidgets


WS_URL = "ws://127.0.0.1:8765"

app = QtWidgets.QApplication(sys.argv)

win = pg.GraphicsLayoutWidget(show=True, title="Heart Monitor")

plot = win.addPlot(title="IR Heartbeat Signal")
plot.showGrid(x=True, y=True)
plot.setLabel("left", "IR amplitude")
plot.setLabel("bottom", "Samples")

curve = plot.plot(pen="r")

status_text = pg.TextItem(anchor=(0, 0))
plot.addItem(status_text)
status_text.setPos(5, 5)

display_size = 500
display_data = np.zeros(display_size, dtype=float)

latest_data = {
    "heart_monitor": {
        "attached": False,
        "spo2": 0.0,
        "heart_rate": 0,
        "latest_ir": 0,
        "latest_red": 0,
    },
    "imu_sensor": {
        "acceleration_g": {"x": 0.0, "y": 0.0, "z": 0.0},
        "gyroscope_deg_s": {"x": 0.0, "y": 0.0, "z": 0.0},
    },
}
data_lock = threading.Lock()
running = True


async def websocket_loop():
    global latest_data, running

    while running:
        try:
            async with websockets.connect(WS_URL) as ws:
                print(f"Connected to {WS_URL}")

                while running:
                    message = await ws.recv()
                    packet = json.loads(message)

                    with data_lock:
                        latest_data = packet

        except Exception as e:
            print(f"WebSocket error: {e}")
            await asyncio.sleep(1.0)


def start_websocket_thread():
    def runner():
        asyncio.run(websocket_loop())

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread


def update():
    global display_data

    with data_lock:
        packet = latest_data.copy()

    heart = packet.get("heart_monitor", {})
    imu = packet.get("imu_sensor", {})

    attached = heart.get("attached", False)
    bpm = heart.get("heart_rate", 0)
    spo2 = heart.get("spo2", 0.0)
    ir = heart.get("latest_ir", 0)
    red = heart.get("latest_red", 0)

    acc = imu.get("acceleration_g", {})
    gyro = imu.get("gyroscope_deg_s", {})

    gx = acc.get("x", 0.0)
    gy = acc.get("y", 0.0)
    gz = acc.get("z", 0.0)

    dx = gyro.get("x", 0.0)
    dy = gyro.get("y", 0.0)
    dz = gyro.get("z", 0.0)

    display_data = np.roll(display_data, -1)
    display_data[-1] = ir

    centered = display_data.copy()
    nonzero = centered[centered != 0]
    if len(nonzero) > 0:
        centered = centered - np.mean(nonzero)

    curve.setData(centered)

    if len(nonzero) > 10:
        ymin = float(np.min(centered))
        ymax = float(np.max(centered))
        if ymin != ymax:
            margin = max(100.0, (ymax - ymin) * 0.2)
            plot.setYRange(ymin - margin, ymax + margin)

    status_text.setText(
        f"Attached: {attached}\n"
        f"BPM: {bpm}\n"
        f"SpO2: {spo2}%\n"
        f"IR: {ir}\n"
        f"RED: {red}\n"
        f"\n"
        f"Accel: [{gx:.3f}, {gy:.3f}, {gz:.3f}] g\n"
        f"Gyro: [{dx:.3f}, {dy:.3f}, {dz:.3f}] deg/s"
    )

    win.setWindowTitle(
        f"Heart Monitor | Attached: {attached} | BPM: {bpm} | SpO2: {spo2}%"
    )


def on_exit():
    global running
    running = False


app.aboutToQuit.connect(on_exit)

ws_thread = start_websocket_thread()

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(20)

exit_code = app.exec()
sys.exit(exit_code)