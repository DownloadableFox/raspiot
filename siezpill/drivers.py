import numpy
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

class Max30102HeartMonitor:
    # If the sensor isn't attached, the IR reading should
    # be below this threshold.
    ATTACHED_IR_THRESHOLD: int  = 50_000

    # The percentile used to detect if the sensor is
    # attached or not.
    ATTACHED_IR_PERCENTILE: int = 10

    def __init__(self, window: int = 100, sample_rate = 100, channel: int = 1, address: int = 0x57) -> None:
        self.sensor = max30102.MAX30102(channel, address)
        self.window = window
        self.sample_rate = sample_rate

        # Samples are buffers for red and ir light readings,
        # they are written to using a pointer to optimize memory allocations.
        self.red_sample = [0] * window
        self.ir_sample = [0] * window
        self.pointer = 0
        self.count = 0
    
    def setup(self) -> None:
        pass # No setup needed

    def update(self) -> None:
        sample_count = self.sensor.get_data_present()

        for _ in range(sample_count):
            red, ir = self.sensor.read_fifo()
            self.red_sample[self.pointer] = red
            self.ir_sample[self.pointer] = ir
            self.pointer = (self.pointer + 1) % self.window
            self.count = min(self.count + 1, self.window)
    
    def close(self) -> None:
        pass # No close needed

    def _valid_samples(self) -> tuple[list[int], list[int]]:
        if self.count < self.window:
            return self.red_sample[:self.count], self.ir_sample[:self.count]
        else:
            red = self.red_sample[self.pointer:] + self.red_sample[:self.pointer]
            ir  = self.ir_sample[self.pointer:]  + self.ir_sample[:self.pointer]
            return red, ir

    def _valid_red(self) -> list[int]:
        return self._valid_samples()[0]

    def _valid_ir(self) -> list[int]:
        return self._valid_samples()[1]

    def is_attached(self) -> bool:
        if self.count < self.window * 0.10:
            return False
        
        reading = numpy.percentile(self._valid_ir(), self.ATTACHED_IR_PERCENTILE)
        return bool(reading > self.ATTACHED_IR_THRESHOLD)
        
    def get_heart_rate(self) -> int: 
        if self.count < 30:
            return 0

        ir = numpy.array(self._valid_ir(), dtype=float)

        # Remove DC component
        ir = ir - numpy.mean(ir)

        kernel_size = max(5, self.sample_rate // 10)
        if kernel_size % 2 == 0:
            kernel_size += 1  # Keep odd for symmetric smoothing

        kernel = numpy.ones(kernel_size) / kernel_size
        ir = numpy.convolve(ir, kernel, mode="same")

        # Dynamic threshold: only keep strong peaks
        threshold = numpy.mean(ir) + 0.5 * numpy.std(ir)

        peaks: list[int] = []
        min_distance = int(self.sample_rate * 0.4)  # max ~150 BPM

        for i in range(1, len(ir) - 1):
            is_peak = ir[i] > ir[i - 1] and ir[i] > ir[i + 1]
            strong_enough = ir[i] > threshold
            far_enough = not peaks or (i - peaks[-1]) >= min_distance

            if is_peak and strong_enough and far_enough:
                peaks.append(i)

        if len(peaks) < 2:
            return 0

        intervals = numpy.diff(peaks) / self.sample_rate
        mean_interval = numpy.mean(intervals)

        if mean_interval <= 0:
            return 0

        bpm = 60.0 / mean_interval

        # Sanity filter
        if bpm < 30 or bpm > 220:
            return 0

        return int(round(bpm))

    def get_spo2(self) -> float:
        if self.count < self.window * 0.10:
            return 0.0
        
        red = numpy.array(self._valid_red(), dtype=float)
        ir = numpy.array(self._valid_ir(), dtype=float)

        # DC component = mean baseline
        red_dc = numpy.mean(red)
        ir_dc = numpy.mean(ir)

        if red_dc == 0 or ir_dc == 0:
            return 0.0

        # AC component = peak-to-peak amplitude of the pulsatile signal,
        # not std dev — std dev underestimates the true AC swing.
        red_ac = numpy.max(red) - numpy.min(red)
        ir_ac  = numpy.max(ir)  - numpy.min(ir)

        if ir_ac == 0:
            return 0.0

        # Ratio of ratios
        r = (red_ac / red_dc) / (ir_ac / ir_dc)

        # Empirical formula (standard approximation)
        spo2 = 110.0 - 25.0 * r

        return round(min(100.0, max(0.0, spo2)), 1)

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