import drivers

i2c_manager = drivers.I2CManager()
heart_monitor: drivers.HeartMonitor = drivers.Max30102HeartMonitor()

def setup():
    i2c_manager.register(heart_monitor)
    i2c_manager.setup()

def loop():
    # All I2C devices are polled
    i2c_manager.update()

    # SpO2 is printed
    print("E")

if __name__ == "__main__":
    setup()
    while True: loop()