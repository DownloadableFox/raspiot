import asyncio
import json
import signal
import drivers
import websockets

i2c_manager = drivers.I2CManager()
heart_monitor: drivers.HeartMonitor = drivers.Max30102HeartMonitor()
imu_sensor = drivers.IntertiaSensor = drivers.GY85InertiaSensor()

clients: set[websockets.WebSocketServerProtocol] = set()
running = True


def setup():
    i2c_manager.register(heart_monitor)
    i2c_manager.register(imu_sensor)

    print("Setting up I2C devices...")
    i2c_manager.setup()


def cleanup():
    i2c_manager.close()
    print("Sensors closed.")


async def ws_handler(websocket):
    clients.add(websocket)
    print(f"Client connected. Total clients: {len(clients)}")

    try:
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(clients)}")


def read_sensor_data() -> dict:
    i2c_manager.update()

    gx, gy, gz = imu_sensor.get_g_force()
    dx, dy, dz = imu_sensor.get_degrees()

    return {
        "heart_monitor": {
            "attached": heart_monitor.is_attached(),
            "spo2": heart_monitor.get_spo2(),
            "heart_rate": heart_monitor.get_heart_rate(),
            "latest_ir": heart_monitor.get_latest_ir(),
            "latest_red": heart_monitor.get_latest_red(),
        },
        "imu_sensor": {
            "acceleration_g": {
                "x": round(gx, 3),
                "y": round(gy, 3),
                "z": round(gz, 3),
            },
            "gyroscope_deg_s": {
                "x": round(dx, 3),
                "y": round(dy, 3),
                "z": round(dz, 3),
            },
        },
    }


async def broadcast_loop():
    global running

    while running:
        data = read_sensor_data()
        message = json.dumps(data)

        if clients:
            disconnected = set()

            for client in clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)

            for client in disconnected:
                clients.discard(client)

        await asyncio.sleep(0.05)


async def main():
    global running

    setup()

    server = await websockets.serve(ws_handler, "0.0.0.0", 8765)
    print("WebSocket server running on ws://0.0.0.0:8765")

    try:
        await broadcast_loop()
    finally:
        server.close()
        await server.wait_closed()
        cleanup()


def handle_sigint():
    global running
    print("\nStopping server...")
    running = False


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.add_signal_handler(signal.SIGINT, handle_sigint)
        loop.add_signal_handler(signal.SIGTERM, handle_sigint)
    except NotImplementedError:
        pass

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        handle_sigint()
    finally:
        loop.close()