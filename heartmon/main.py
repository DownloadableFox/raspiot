import driver
import time

sensor = driver.MAX30102(channel=1, address=57)

print("Place finger on sensor...")
print(f"{'Time':>8} | {'Red LED':>10} | {'IR LED':>10}")
print("-" * 38)

try:
    while True:
        if sensor.get_data_present():
            red, ir = sensor.read_fifo()
            note = "✓" if ir > 10000 else "--"
            print(f"{time.strftime('%H:%M:%S'):>8} | {red:>10} | {ir:>10}  {note}")
        time.sleep(0.1)

except KeyboardInterrupt:
    sensor.shutdown()
    print("\nStopped.")