import max30102
import numpy
from typing import Protocol

class I2CDevice(Protocol):
    def setup(self) -> None: ...
    def update(self) -> None: ...

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

class HeartMonitor(Protocol):
    def is_attached(self) -> bool: ...
    def get_heart_rate(self) -> int: ...
    def get_spo2(self) -> float: ...

class Max30102HeartMonitor():
    # If the sensor is't attached, the IR reading should
    # be bellow this threshold.
    ATTACHED_IR_THRESHOLD: int  = 50_000

    # The percentile used to detect if the sensor is
    # attached or not.
    ATTACHED_IR_PERCENTILE: int = 10

    def __init__(self, window: int = 100, channel: int = 1, address: int = 0x57) -> None:
        self.sensor = max30102.MAX30102(channel, address)
        self.window = window

        # Samples are buffers for red and ir light readings,
        # the are written to using a pointer to optimize memory allocations.
        self.red_sample = [(0, 0) for _ in range(window)]
        self.ir_sample = [(0, 0) for _ in range(window)]
        self.pointer = 0

    def setup(self) -> None:
        pass # No setup needed

    def update(self) -> None:
        sample_count = self.sensor.get_data_present()

        for _ in range(sample_count):
            red, ir = self.sensor.read_fifo()
            self.red_sample[self.pointer] = red
            self.ir_sample[self.pointer] = ir
            self.pointer = (self.pointer + 1) % self.window

    def is_attached(self) -> bool:
        reading = numpy.percentile(self.ir_sample, self.ATTACHED_IR_PERCENTILE)
        return reading > self.ATTACHED_IR_THRESHOLD
        
    def get_heart_rate(self) -> int: 
        return 0

    # AI generated because I have no idea how to calculate SpO2
    def get_spo2(self) -> float: 
        red = numpy.array(self.red_sample, dtype=float)
        ir = numpy.array(self.ir_sample, dtype=float)

        # DC component = moving average (baseline)
        red_dc = numpy.mean(red)
        ir_dc = numpy.mean(ir)

        # AC component = signal minus baseline
        red_ac = numpy.std(red)
        ir_ac = numpy.std(ir)

        # Ratio of ratios
        r = (red_ac / red_dc) / (ir_ac / ir_dc)

        # Empirical formula (standard approximation)
        spo2 = 110.0 - 25.0 * r

        return round(min(100.0, max(0.0, spo2)), 1)
