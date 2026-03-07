import drivers
import time
import sys
import math

LINES = 9  # number of printed lines

i2c_manager = drivers.I2CManager()
heart_monitor: drivers.HeartMonitor = drivers.Max30102HeartMonitor()
imu_sensor = drivers.IntertiaSensor = drivers.GY85InertiaSensor()

def setup():
    # Registering sensors
    i2c_manager.register(heart_monitor)
    i2c_manager.register(imu_sensor)

    # Sensor setup
    print("Setting up I2C devices...")
    i2c_manager.setup()

def loop():
    global LINES

    # I2C devices are polled
    i2c_manager.update()

    gx, gy, gz = imu_sensor.get_g_force()
    dx, dy, dz = imu_sensor.get_degrees()

    dx *= 180.0 / math.PI
    dy *= 180.0 / math.PI
    dz *= 180.0 / math.PI

    output = [
        "Heart Monitor:",
        f"Attached: {heart_monitor.is_attached()}",
        f"Oxygenation: {heart_monitor.get_spo2()} %",
        f"Heart rate: {heart_monitor.get_heart_rate()} bps",
        "----",
        "IMU Sensor:",
        f"Acceleration: [{gx:.3f}, {gy:.3f}, {gz:.3f}] g",
        f"Gyroscope: [{dx:.3f}, {dy:.3f}, {dz:.3f}] rad/s",
        "----"
    ]

    # Move cursor up
    sys.stdout.write(f"\033[{LINES}A")

    for line in output:
        sys.stdout.write("\033[2K")  # clear line
        sys.stdout.write(line + "\n")

    sys.stdout.flush()

    time.sleep(0.05)

def cleanup():
    # Cleanly shuts down all sensors.
    i2c_manager.close() 

if __name__ == "__main__":
    setup()

    # TODO: Replace this with a SIGINT handler
    while True: 
        loop()
        time.sleep(0.05)
    
    cleanup()
