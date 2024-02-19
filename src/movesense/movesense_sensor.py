import struct
import datetime
import numpy as np

from enum import Enum


class MovesenseSensorType(Enum):
    ACCELEROMETER = ('Acc', 3)
    GYROSCOPE = ('Gyro', 3)
    MAGNETOMETER = ('Magn', 3)
    TEMPERATURE = ('Temp', 1)
    ECG = ('ECG', 1)
    HEART_RATE = ('HR', 1)
    IMU6 = ('IMU6', 6)
    IMU9 = ('IMU9', 9)

    def __new__(cls, value, axes):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.axes = axes
        return obj

    @classmethod
    def from_string(cls, value):
        for member in cls:
            if member.value == value:
                return member
            elif value.startswith(member.value):
                return member
            elif value == "IMU":
                return MovesenseSensorType.IMU9
        raise ValueError(f"No member with the value {value} in {cls.__name__}")


class MovesenseSamplingRate(Enum):
    _13_HZ = 13
    _26_HZ = 26
    _52_HZ = 52
    _104_HZ = 104
    _208_HZ = 208
    _416_HZ = 416
    _833_HZ = 833
    _1666_HZ = 1666

    # ECG Sample rates
    _125_HZ = 125
    _128_HZ = 128
    _200_HZ = 200
    _250_HZ = 250
    _256_HZ = 256
    _500_HZ = 500
    _512_HZ = 512

    @classmethod
    def from_int(cls, value):
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"No member with the value {value} in {cls.__name__}")


"""
Acts as an instance for datacollection, maintaining the sensor type and unpacking the data appropriately.
Movesense data packets have shape: c c uint32 float32 float32 float32... Where the float sequence is the data.
Depending on the sensor, the data might represent multiple axes. Timestamp is the time of the first data sample.
"""
class MovesenseSensor:
    # 'Serial number' used as an id for the REST path calls
    id_counter = 0

    def __init__(self, sensor_type, sampling_rate):
        # Allow creating from strings, not just enums. Enums simply force typechecking.
        self.sensor_type = sensor_type if sensor_type is MovesenseSensorType \
            else MovesenseSensorType.from_string(sensor_type)
        self.sampling_rate = sampling_rate if sampling_rate is MovesenseSamplingRate \
            else MovesenseSamplingRate.from_int(sampling_rate)

        self.id = MovesenseSensor.id_counter
        MovesenseSensor.id_counter += 1

        # Path which is subscribed to for collecting data from this sensor
        self.path = (bytearray([1, self.id]) +
                     bytearray(f"/Meas/{self.sensor_type.value}/{self.sampling_rate.value}", "utf-8"))

        self.data = []

    @classmethod
    def from_path(cls, path):
        _, _, sensor_type, sampling_rate = path.split("/")
        return MovesenseSensor(sensor_type, int(sampling_rate))

    async def notification_handler(self, device_address, data):

        # Timestamp by arrival time
        local_timestamp = datetime.datetime.now().timestamp()

        # Shape the data
        data = np.array(data).reshape(-1, self.sensor_type.axes)

        # Sampling period
        T_s = 1. / self.sampling_rate.value

        # Extend timestamp to each instance, starting from past since recorded timestamp is arrival time.
        local_timestamp = np.linspace(-T_s*data.shape[0], 0, data.shape[0]) + local_timestamp

        # Each row should be a new entry, appending in samples to maintain labels.
        # Maybe just refactoring to pands would be more convenient?
        for i, row in enumerate(data):
            sample = {
                "timestamp": local_timestamp[i],
                "device": device_address,
                "sensor_type": self.sensor_type.value,
                "sensor_data": row,
            }
            self.data.append(sample)


