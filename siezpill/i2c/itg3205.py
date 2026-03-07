from smbus2 import SMBus
import time

class ITG3205:
    ADDRESS = 0x68

    REG_SMPLRT_DIV = 0x15
    REG_DLPF_FS = 0x16
    REG_INT_CFG = 0x17
    REG_PWR_MGM = 0x3E

    REG_TEMP_OUT_H = 0x1B

    REG_GYRO_XOUT_H = 0x1D
    REG_GYRO_YOUT_H = 0x1F
    REG_GYRO_ZOUT_H = 0x21

    SENSITIVITY = 14.375  # LSB per °/s

    def __init__(self, channel = 1, address = ADDRESS):
        self.bus = SMBus(channel)
        self.address = address

        self._initialize()

    def _initialize(self):
        # Wake up the sensor
        self.bus.write_byte_data(self.address, self.REG_PWR_MGM, 0x00)

        # Sample rate divider
        self.bus.write_byte_data(self.address, self.REG_SMPLRT_DIV, 0x07)

        # Full scale = 2000 deg/s, low pass filter
        self.bus.write_byte_data(self.address, self.REG_DLPF_FS, 0x18)

        time.sleep(0.1)

    def _read_i16(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)

        value = (high << 8) | low

        if value >= 0x8000:
            value = -((65535 - value) + 1)

        return value

    def read_raw(self):
        gx = self._read_i16(self.REG_GYRO_XOUT_H)
        gy = self._read_i16(self.REG_GYRO_YOUT_H)
        gz = self._read_i16(self.REG_GYRO_ZOUT_H)

        return gx, gy, gz

    def read_dps(self):
        gx, gy, gz = self.read_raw()

        gx /= self.SENSITIVITY
        gy /= self.SENSITIVITY
        gz /= self.SENSITIVITY

        return gx, gy, gz

    def read_temperature(self):
        temp_raw = self._read_i16(self.REG_TEMP_OUT_H)

        # Datasheet conversion
        temp_c = 35 + ((temp_raw + 13200) / 280)

        return temp_c

    def close(self):
        self.bus.close()