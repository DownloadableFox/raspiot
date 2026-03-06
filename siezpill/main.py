import drivers
import time

i2c_manager = drivers.I2CManager()
heart_monitor: drivers.HeartMonitor = drivers.Max30102HeartMonitor()

def setup():
    i2c_manager.register(heart_monitor)
    
    print("Setting up I2C devices...")
    i2c_manager.setup()

def loop():
    # All I2C devices are polled
    i2c_manager.update()

    # SpO2 is printed
    print("Heart Monitor:")
    print("Attached:", heart_monitor.is_attached())
    print("Oxygenation:", heart_monitor.get_spo2(), "%")
    print("Heart rate:", heart_monitor.get_heart_rate(), "bps")
    print("----")

if __name__ == "__main__":
    setup()
    while True: 
        loop()
        time.sleep(0.05)