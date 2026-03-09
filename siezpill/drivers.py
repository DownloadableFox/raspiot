import time
import collections
import numpy
import heartpy as hp
from typing import Protocol
from i2c import max30102, adxl345, itg3205

class I2CDevice(Protocol):
    def setup(self) -> None: ...
    def update(self) -> None: ...
    def close(self) -> None: ...

class I2CManager():
    def __init__(self) -> None:
        self.initialized = False
        self.devices: list[I2CDevice] = []

    def register(self, device: I2CDevice) -> None:
        self.devices.append(device)

    def setup(self) -> None:
        if self.initialized:
            print("Warning: I2CManager setup() called twice.")
            return

        # All devices are setup
        for device in self.devices:
            device.setup()
        
        # Manager is marked as initialized
        self.initialized = True

    def update(self) -> None:
        for device in self.devices:
            device.update()

    def close(self) -> None:
        for device in self.devices:
            device.close()

class HeartMonitor(Protocol):
    def is_attached(self) -> bool: ...
    def get_heart_rate(self) -> int: ...
    def get_spo2(self) -> float: ...
    def get_latest_ir(self) -> int: ...
    def get_latest_red(self) -> int: ...
    
class Max30102HeartMonitor:
    ATTACHED_IR_THRESHOLD: int = 50_000
    ATTACHED_IR_PERCENTILE: int = 10

    def __init__(
        self,
        window: int = 500,       # Full rolling buffer (kept for SpO2 / attachment detection)
        sample_rate: int = 100,
        channel: int = 1,
        address: int = 0x57,
        bpm_history_size: int = 3,          # ← was 5; smaller = faster response
        bpm_analysis_seconds: int = 6,      # ← NEW: only analyse recent N seconds for BPM
        bpm_update_interval: float = 0.5,   # ← NEW: explicit update cadence
    ) -> None:
        self.sensor = max30102.MAX30102(channel, address)
        self.sample_rate = sample_rate
        self.window = window
        self.bpm_history_size = bpm_history_size
        self.bpm_analysis_samples = bpm_analysis_seconds * sample_rate  # e.g. 600
        self.bpm_update_interval = bpm_update_interval

        # ✅ deque: O(1) append/pop on both ends
        self.red_samples: collections.deque[int] = collections.deque(maxlen=window)
        self.ir_samples:  collections.deque[int] = collections.deque(maxlen=window)

        self.bpm_history: list[float] = []
        self.last_bpm_time: float = 0.0
        self.last_bpm: int = 0

    def setup(self) -> None:
        pass

    def update(self) -> None:
        sample_count = self.sensor.get_data_present()
        for _ in range(sample_count):
            red, ir = self.sensor.read_fifo()
            self.red_samples.append(red)   # deque handles maxlen automatically
            self.ir_samples.append(ir)

    def close(self) -> None:
        pass

    def is_attached(self) -> bool:
        if len(self.ir_samples) < max(10, int(self.window * 0.10)):
            return False
        reading = numpy.percentile(list(self.ir_samples), self.ATTACHED_IR_PERCENTILE)
        return bool(reading > self.ATTACHED_IR_THRESHOLD)

    def _push_bpm_history(self, bpm: float) -> None:
        self.bpm_history.append(bpm)
        if len(self.bpm_history) > self.bpm_history_size:
            self.bpm_history.pop(0)

    def _smoothed_bpm(self) -> int:
        if not self.bpm_history:
            return 0
        return int(round(float(numpy.median(self.bpm_history))))  # ✅ median over mean: rejects outliers

    def get_heart_rate(self) -> int:
        if not self.is_attached():
            self.bpm_history.clear()
            self.last_bpm = 0
            return 0

        # ✅ Use only the most recent N seconds, not the full buffer
        analysis_len = min(self.bpm_analysis_samples, len(self.ir_samples))
        min_samples = self.sample_rate * 4
        if analysis_len < min_samples:
            return self.last_bpm

        # Slice from the right (most recent data)
        ir = numpy.array(list(self.ir_samples)[-analysis_len:], dtype=float)

        # ✅ Remove DC offset — let HeartPy do its own peak filtering
        ir = ir - numpy.mean(ir)

        # Throttle: skip expensive HeartPy call if not due yet
        now = time.time()
        if self.last_bpm_time != 0.0 and (now - self.last_bpm_time) < self.bpm_update_interval:
            return self.last_bpm

        try:
            _, measures = hp.process(
                ir,
                sample_rate=self.sample_rate,
                bpmmin=40,
                bpmmax=180,
                clean_rr=True,
                clean_rr_method="quotient-filter",
            )

            bpm = float(measures["bpm"])
            if numpy.isnan(bpm) or not (30 <= bpm <= 220):
                return self.last_bpm

            self._push_bpm_history(bpm)
            self.last_bpm_time = now
            self.last_bpm = self._smoothed_bpm()
            return self.last_bpm

        except Exception:
            return self.last_bpm

    def get_spo2(self) -> float:
        if not self.is_attached():
            return 0.0

        min_samples = max(self.sample_rate * 3, int(self.window * 0.10))
        if len(self.red_samples) < min_samples or len(self.ir_samples) < min_samples:
            return 0.0

        red = numpy.array(list(self.red_samples), dtype=float)
        ir  = numpy.array(list(self.ir_samples),  dtype=float)

        red_dc = numpy.mean(red)
        ir_dc  = numpy.mean(ir)
        if red_dc <= 0 or ir_dc <= 0:
            return 0.0

        half_sr = max(3, self.sample_rate // 2)
        kernel  = numpy.ones(half_sr) / half_sr
        red_ac_wave = red - numpy.convolve(red, kernel, mode="same")
        ir_ac_wave  = ir  - numpy.convolve(ir,  kernel, mode="same")

        red_ac = numpy.sqrt(numpy.mean(red_ac_wave ** 2))
        ir_ac  = numpy.sqrt(numpy.mean(ir_ac_wave  ** 2))
        if red_ac <= 0 or ir_ac <= 0:
            return 0.0

        r    = (red_ac / red_dc) / (ir_ac / ir_dc)
        spo2 = 110.0 - 25.0 * r
        return round(min(100.0, max(0.0, spo2)), 1)

    def get_latest_ir(self) -> int:
        return self.ir_samples[-1] if self.ir_samples else 0

    def get_latest_red(self) -> int:
        return self.red_samples[-1] if self.red_samples else 0

class IntertiaSensor(Protocol):
    def get_g_force(self) -> tuple[int, int, int]: ...
    def get_degrees(self) -> tuple[int, int, int]: ...

class GY85InertiaSensor:
    def __init__(self, channel = 1, accelerometer_address = 0x53, gyroscope_address = 0x68):
        self.accelerometer = adxl345.ADXL345(channel, accelerometer_address)
        self.gyroscope = itg3205.ITG3205(channel, gyroscope_address)

    def setup(self) -> None:
        pass # Not needed

    def update(self) -> None:
        pass # Not needed

    def close(self) -> None:
        self.accelerometer.close()
        self.gyroscope.close()

    def get_g_force(self) -> tuple[int, int, int]: 
        return self.accelerometer.read_g()
    
    def get_degrees(self) -> tuple[int, int, int]:
        return self.gyroscope.read_dps()