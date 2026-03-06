import netifaces
import time
import driver

def get_address(interface="eth0"):
    if interface not in netifaces.interfaces():
        return None
    
    addrs = netifaces.ifaddresses(interface)
    if netifaces.AF_INET not in addrs:
        return None
    
    return addrs[netifaces.AF_INET][0]["addr"]

def setup():
    print("initializing board...")
    driver.init()

def loop():
    address = get_address("wlan0")
    driver.clear()

    if address:
        driver.print((0, 0), "IP: " + address)
    else:
        driver.print((0, 0), "Not connected")
    
    driver.flush()
    time.sleep(1)

if __name__ == "__main__":
    setup()
    while True: loop()