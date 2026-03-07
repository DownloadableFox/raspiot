import drivers
import time

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
    # All I2C devices are polled
    i2c_manager.update()

    print("Heart Monitor:")
    print("Attached:", heart_monitor.is_attached())
    print("Oxygenation:", heart_monitor.get_spo2(), "%")
    print("Heart rate:", heart_monitor.get_heart_rate(), "bps")
    print("----")

    gx, gy, gz = imu_sensor.get_g_force()
    dx, dy, dz = imu_sensor.get_degrees()

    print("IMU Sensor:")
    print(f"Acceleration: [{gx}, {gy}, {gz}] g")
    print(f"Gyroscope: [{dx}, {dy}, {dz}] rad/s")
    print("----")

    time.sleep(0.25)

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
