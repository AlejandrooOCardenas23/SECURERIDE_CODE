from machine import Pin, UART, I2C
import utime
from ssd1306 import SSD1306_I2C
from micropyGPS import MicropyGPS
import ufirebase as firebase

def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        wlan.active(True)
        wlan.connect(ssid, password)
        print('Conectando a la red', ssid + "…")
        timeout = time.time()
        while not wlan.isconnected():
            if (time.ticks_diff(time.time(), timeout) > 10):
                return False
    return True

if connect_to_wifi("TuSSID", "TuPassword"):  
    print("Conexión exitosa!")
    print('Datos de la red (IP/netmask/gw/DNS):', wlan.ifconfig())
    
    firebase.setURL("https://data-ride-default-rtdb.firebaseio.com/")  

    i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
    oled = SSD1306_I2C(128, 64, i2c)

    gps_uart = UART(2, baudrate=9600, tx=Pin(17), rx=Pin(16))  

    print(gps_uart)

    timezone = -3
    gps = MicropyGPS(timezone)

    def convert_coord(coord, direction):
        if coord == 0:
            return None
        data = coord + (coord / 60.0)
        if direction in ['S', 'W']:
            data = -data
        return '{0:.6f}'.format(data)

    def send_to_firebase(latitude, longitude):
        data = {
            "LATITUD": latitude,
            "LONGITUD": longitude
        }
        firebase.put("UBICACION", data, bg=0)

    while True:
        data_length = gps_uart.any()
        if data_length > 0:
            data = gps_uart.read(data_length)
            for char in data:
                msg = gps.update(chr(char))

        latitude = convert_coord(gps.latitude, gps.lat)
        longitude = convert_coord(gps.longitude, gps.lon)

        if latitude is None or longitude is None:
            oled.fill(0)
            oled.text("Datos no", 35, 25)
            oled.text("disponibles", 22, 40)
            oled.show()
            continue

        timestamp = gps.timestamp
        time_str = '{:02d}:{:02d}:{:02}'.format(timestamp[0], timestamp[1], timestamp[2])

        oled.fill(0)
        oled.text('Satelites: ' + str(gps.satellites_in_use), 10, 0)
        oled.text('Lat:' + latitude, 0, 18)
        oled.text('Lon:' + longitude, 0, 36)
        oled.text('Horario:' + time_str, 0, 54)
        oled.show()

        # Envía los datos de latitud y longitud a Firebase solo si hay cambios significativos
        send_to_firebase(latitude, longitude)
else:
    print("Imposible conectar")
    wlan.active(False)
