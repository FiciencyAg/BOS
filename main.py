import asyncio
import struct

import busio
import digitalio
import board
import sdioio
import storage
import camera
from circuitpython_nrf24l01.rf24 import RF24
from adafruit_bmp3xx import BMP3XX_I2C
from adafruit_mpu6050 import MPU6050
import gnss

# SD Card and Camera setup
SD = sdioio.SDCard(
    clock=board.SDIO_CLOCK,
    command=board.SDIO_COMMAND,
    data=board.SDIO_DATA,
    frequency=25000000)
storage.mount(storage.VfsFat(SD), '/sd')
CAMERA = camera.Camera()

# I2C Pins and addresses for Barometer BMP388, and IMU MPU6050 or similar. D15 + D14 (Ext Board)
I2C = busio.I2C(board.SCL, board.SDA)
BAROMETER = BMP3XX_I2C(I2C)
IMU = MPU6050(I2C)

# Radio SPI Pins for nrf24l01 or similar, use RADIO.write() and RADIO.readinto(). D13 + D12 + D11 + D10 + D9 (Ext Board)
RADIO_ENABLE = digitalio.DigitalInOut(board.D10)
RADIO_SELECT = digitalio.DigitalInOut(board.D9)
RADIO_BUS = board.SPI()

# GPS setup
GPS = gnss.GNSS([gnss.SatelliteSystem.GPS, gnss.SatelliteSystem.GLONASS])

# Output Pins. D7 + D6 (Ext Board)
AIR_PUMP = digitalio.DigitalInOut(board.D7)
AIR_BLEED = digitalio.DigitalInOut(board.D6)
AIR_PUMP.direction, AIR_BLEED.direction = digitalio.Direction.OUTPUT


class SensorValues:
    def __init__(self):
        # Barometer Values
        self.altitude_m = 0
        self.temp_c = 0
        self.pressure_hpa = 0

        # IMU Values
        self.accel_x = 0
        self.accel_y = 0
        self.accel_z = 0
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0

        # GPS Values
        self.gps_latitude = 0
        self.gps_longitude = 0


async def read_sensors(sensor_values):
    while True:
        # Let another task run
        await asyncio.sleep(1)

        # Read Task
        sensor_values.altitude_m = BAROMETER.temperature
        sensor_values.temp_c = BAROMETER.temperature
        sensor_values.pressure_hpa = BAROMETER.pressure

        sensor_values.accel_x = IMU.acceleration[0]
        sensor_values.accel_y = IMU.acceleration[1]
        sensor_values.accel_z = IMU.acceleration[2]
        sensor_values.gyro_x = IMU.gyro[0]
        sensor_values.gyro_y = IMU.gyro[1]
        sensor_values.gyro_z = IMU.gyro[2]

        GPS.update()
        sensor_values.gps_latitude = GPS.latitude
        sensor_values.gps_longitude = GPS.longitude


async def radio(sensor_values):
    nrf = RF24(RADIO_BUS, RADIO_SELECT, RADIO_ENABLE)
    nrf.pa_level = -12
    address = [b"1Node", b"2Node"]
    nrf.open_tx_pipe(address[0])
    nrf.open_rx_pipe(1, address[1])

    payload_out = [sensor_values.gps_latitude, sensor_values.gps_longitude,
                   sensor_values.altitude_m, sensor_values.temp_c]

    while True:
        # Let another task run
        await asyncio.sleep(1)

        # Master Task
        nrf.listen = False
        try:
            nrf.send(struct.pack("i", payload_out))
        except OSError:
            print('payload_out lost')

        # Slave Task
        nrf.listen = True
        if nrf.available():
            buffer = nrf.read()
            payload_in = struct.unpack("i", buffer)[0]
            print(payload_in)


async def take_picture():
    buffer = bytearray(512 * 1024)
    file = open("/sd/image.jpg", "wb")
    size = CAMERA.take_picture(buffer, width=1920, height=1080, format=camera.ImageFormat.JPG)
    file.write(buffer, size)
    file.close()


async def keep_altitude(sensor_values):
    while True:
        # Let another task run
        await asyncio.sleep(0)

        # Task
        print("keep_altitude")


async def scheduler():
    # Connect shared sensor variables
    sensor_values = SensorValues()

    # Create and gather async tasks
    task_radio = asyncio.create_task(radio(sensor_values))
    task_read_sensors = asyncio.create_task(read_sensors(sensor_values))
    task_keep_altitude = asyncio.create_task(keep_altitude(sensor_values))
    await asyncio.gather(task_radio, task_read_sensors, task_keep_altitude)


if __name__ == "__main__":
    asyncio.run(scheduler())
