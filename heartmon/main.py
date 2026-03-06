import driver
import time

sensor = driver.MAX30102(channel=1, address=0x57)

print("Place finger on sensor...")
print(f"{'Time':>8} | {'Red LED':>10} | {'IR LED':>10}")
print("-" * 38)

try:
    while True:
        num_samples = sensor.get_data_present()
        if num_samples > 0:
            for _ in range(num_samples):
                red, ir = sensor.read_fifo()
                note = "✓" if ir > 10000 else "--"
                print(f"{time.strftime('%H:%M:%S'):>8} | {red:>10} | {ir:>10}  {note}")
        else:
            time.sleep(0.01)  # only sleep when no data, and much shorter
except KeyboardInterrupt:
    sensor.shutdown()
    print("\nStopped.")