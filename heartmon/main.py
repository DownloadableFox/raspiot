import driver
import time
import numpy as np

sensor = driver.MAX30102(channel=1, address=0x57)

def calculate_spo2(red_buf, ir_buf):
    red = np.array(red_buf, dtype=float)
    ir = np.array(ir_buf, dtype=float)

    # DC component = moving average (baseline)
    red_dc = np.mean(red)
    ir_dc = np.mean(ir)

    # AC component = signal minus baseline
    red_ac = np.std(red)
    ir_ac = np.std(ir)

    # Ratio of ratios
    r = (red_ac / red_dc) / (ir_ac / ir_dc)

    # Empirical formula (standard approximation)
    spo2 = 110.0 - 25.0 * r

    return round(min(100.0, max(0.0, spo2)), 1)

print("Place finger on sensor...")
print(f"{'Time':>8} | {'Red LED':>10} | {'IR LED':>10}")
print("-" * 38)

WINDOW = 100  # samples — ~1 second of data at 100Hz
red_buf = []
ir_buf  = []

try:
    while True:
        num_samples = sensor.get_data_present()
        if num_samples > 0:
            for _ in range(num_samples):
                red, ir = sensor.read_fifo()
                red_buf.append(red)
                ir_buf.append(ir)

                # keep buffer at fixed window size
                if len(red_buf) > WINDOW:
                    red_buf.pop(0)
                    ir_buf.pop(0)

                # only calculate once we have enough data
                if len(red_buf) == WINDOW:
                    spo2 = calculate_spo2(red_buf, ir_buf)
                    note = "✓" if ir > 50000 else "-- (no finger?)"
                    print(f"{time.strftime('%H:%M:%S'):>8} | {red:>10} | {ir:>10} | {spo2:>5}%  {note}")
                else:
                    print(f"{time.strftime('%H:%M:%S'):>8} | {red:>10} | {ir:>10} | {'...':>6}  (collecting)")
        else:
            time.sleep(0.01)
except KeyboardInterrupt:
    sensor.shutdown()
    print("\nStopped.")