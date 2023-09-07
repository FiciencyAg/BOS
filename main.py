import busio
import digitalio
import board
import sdioio
import storage
import camera

# SD Card and Camera setup
SD = sdioio.SDCard(
    clock=board.SDIO_CLOCK,
    command=board.SDIO_COMMAND,
    data=board.SDIO_DATA,
    frequency=25000000)
VFS = storage.VfsFat(SD)
storage.mount(VFS, '/sd')
CAMERA = camera.Camera()

# I2C Pins and addresses for Barometer BMP388, and IMU MPU6050 or similar. D15 + D14
I2C = busio.I2C(board.SCL, board.SDA)
BAROMETER = 0x77
IMU = 0x68

# Radio SPI Pins for nrf24l01 or similar, use RADIO.write() and RADIO.readinto(). D13 + D12 + D11
RADIO_ENABLE = digitalio.DigitalInOut(board.D18)
RADIO_ENABLE.direction = digitalio.Direction.OUTPUT
RADIO = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Output Pins. D7 + D6
AIR_PUMP = digitalio.DigitalInOut(board.D7)
AIR_BLEED = digitalio.DigitalInOut(board.D6)
AIR_PUMP.direction, AIR_BLEED.direction = digitalio.Direction.OUTPUT


def take_picture():
    buffer = bytearray(512 * 1024)
    file = open("/sd/image.jpg", "wb")
    size = CAMERA.take_picture(buffer, width=1920, height=1080, format=camera.ImageFormat.JPG)
    file.write(buffer, size)
    file.close()
