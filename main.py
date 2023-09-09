import asyncio
import struct

import busio
import digitalio
import board
import sdioio
import storage
import camera
from circuitpython_nrf24l01.rf24 import RF24

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
BAROMETER = 0x77
IMU = 0x68

# Radio SPI Pins for nrf24l01 or similar, use RADIO.write() and RADIO.readinto(). D13 + D12 + D11 + D10 + D9 (Ext Board)
RADIO_ENABLE = digitalio.DigitalInOut(board.D10)
RADIO_SELECT = digitalio.DigitalInOut(board.D9)
RADIO_BUS = board.SPI()

# Output Pins. D7 + D6 (Ext Board)
AIR_PUMP = digitalio.DigitalInOut(board.D7)
AIR_BLEED = digitalio.DigitalInOut(board.D6)
AIR_PUMP.direction, AIR_BLEED.direction = digitalio.Direction.OUTPUT


async def take_picture():
    buffer = bytearray(512 * 1024)
    file = open("/sd/image.jpg", "wb")
    size = CAMERA.take_picture(buffer, width=1920, height=1080, format=camera.ImageFormat.JPG)
    file.write(buffer, size)
    file.close()


async def radio():
    nrf = RF24(RADIO_BUS, RADIO_SELECT, RADIO_ENABLE)
    nrf.pa_level = -12
    address = [b"1Node", b"2Node"]
    nrf.open_tx_pipe(address[0])
    nrf.open_rx_pipe(1, address[1])

    payload_out = [0, 0, False, False]

    while True:
        # Let another task run
        await asyncio.sleep(0)

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


async def keep_altitude():
    while True:
        # Let another task run
        await asyncio.sleep(0)

        # Task
        print("keep_altitude")


async def scheduler():
    task_radio = asyncio.create_task(radio())
    task_keep_altitude = asyncio.create_task(keep_altitude())
    await asyncio.gather(task_radio, task_keep_altitude)


asyncio.run(scheduler())
