from smbus2 import SMBus

ADXL345_ADDR = 0x53

REG_POWER_CTL = 0x2D
REG_DATA_FORMAT = 0x31
REG_BW_RATE = 0x2C
REG_DATAX0 = 0x32

class ADXL345:
    def __init__(self, channel=1, addr=ADXL345_ADDR):
        self.bus = SMBus(channel)
        self.addr = addr

        # Measurement mode
        self.bus.write_byte_data(self.addr, REG_POWER_CTL, 0x08)

        # Full resolution, +/- 2g
        self.bus.write_byte_data(self.addr, REG_DATA_FORMAT, 0x08)

        # Output data rate = 100 Hz
        self.bus.write_byte_data(self.addr, REG_BW_RATE, 0x0A)

    def _read_i16(self, reg):
        low = self.bus.read_byte_data(self.addr, reg)
        high = self.bus.read_byte_data(self.addr, reg + 1)
        value = (high << 8) | low
        if value & 0x8000:
            value -= 65536
        return value

    def read_raw(self):
        x = self._read_i16(REG_DATAX0)
        y = self._read_i16(REG_DATAX0 + 2)
        z = self._read_i16(REG_DATAX0 + 4)
        return x, y, z

    def read_g(self):
        x, y, z = self.read_raw()
        scale = 0.004
        return x * scale, y * scale, z * scale

    def close(self):
        self.bus.close()
