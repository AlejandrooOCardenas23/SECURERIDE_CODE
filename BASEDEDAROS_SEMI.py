import time
from machine import Pin, SoftI2C
import mpu6050
import network
from utelegram import Bot
import ufirebase as firebase
from utime import time, localtime

# Configura el MPU6050
i2c_mpu = SoftI2C(scl=Pin(22), sda=Pin(21))
mpu = mpu6050.accel(i2c_mpu)

# Configura la red Wi-Fi
def conectaWifi(red, password):
    miRed = network.WLAN(network.STA_IF)
    if not miRed.isconnected():
        miRed.active(True)
        miRed.connect(red, password)
        print('Conectando a la red', red + "…")
        timeout = time.time()
        while not miRed.isconnected():
            if (time.ticks_diff(time.time(), timeout) > 10):
                return False
    return miRed

red_conectada = conectaWifi("SED-CISCO", "Cisco2023")

if red_conectada:
    print("Conexión exitosa!")
    print('Datos de la red (IP/netmask/gw/DNS):', red_conectada.ifconfig())
    TOKEN = '6310029123:AAFHt8FrdHkkEYoGCMkTsvAGGlB-vAcXo9w'
    pin_tactil = Pin(18, Pin.IN)
    pin_externo = Pin(19, Pin.IN)
    led = Pin(2, Pin.OUT)
    contador_toques = 0
    bot = Bot(TOKEN)
    relay = Pin(4, Pin.OUT)

    # Configura la URL de Firebase
    firebase.setURL("https://data-ride-default-rtdb.firebaseio.com/")

    def iniciar_rodada():
        current_time = localtime(time())
        fecha = "{:02d}/{:02d}/{:04d}".format(current_time[2], current_time[1], current_time[0])
        hora = "{:02d}:{:02d}:{:02d}".format(current_time[3], current_time[4], current_time[5])
        mensaje = "Rodada iniciada - Fecha: {} - Hora: {}".format(fecha, hora)
        firebase.put("andina/esp32", {"Mensaje": mensaje, "Timestamp": time()}, bg=0)

    def finalizar_rodada():
        current_time = localtime(time())
        fecha = "{:02d}/{:02d}/{:04d}".format(current_time[2], current_time[1], current_time[0])
        hora = "{:02d}:{:02d}:{:02d}".format(current_time[3], current_time[4], current_time[5])
        mensaje = "Rodada finalizada - Fecha: {} - Hora: {}".format(fecha, hora)
        firebase.put("andina/esp32", {"Mensaje": mensaje, "Timestamp": time()}, bg=0)

    def obtener_datos_rodada():
        data = firebase.get("andina/esp32")
        return data

    initial_orientation = "Centro"  # Definir una orientación inicial
    moved_sides = set()  # Conjunto para rastrear los lados movidos

    def detect_orientation():
        global initial_orientation
        accel_data = mpu.get_values()
        x_accel = accel_data['AcX']
        z_accel = accel_data['AcZ']
        if x_accel > 4500:
            moved_sides.add("Derecha")
        elif x_accel < -4500:
            moved_sides.add("Izquierda")
        if z_accel > 7000:
            moved_sides.add("Adelante")
        elif z_accel < -5000:
            moved_sides.add("Atrás")
        else:
            return "Centro"  # Definir una orientación por defecto

        if len(moved_sides) == 4:
            moved_sides.clear()
            return "Casco bien puesto"
        else:
            return initial_orientation

    while True:
        orientation = detect_orientation()

        # Muestra los lados a los que se ha movido
        print("Lados movidos:", ", ".join(moved_sides))

        # Si la orientación es "Casco bien puesto", muestra el mensaje durante 20 segundos
        if orientation == "Casco bien puesto":
            print("Casco bien puesto")
            time.sleep(20)

        @bot.add_message_handler('Hola')
        def help(update):
            update.reply('Bienvenido a Securide')
            update.reply('Aqui podrás tener un reporte vial de tu recorrido a través de la ciudad')
            update.reply('Escribe "salir a rodar" para iniciar tu recorrido y "terminar rodada" para finalizarlo')

        @bot.add_message_handler('salir a rodar')
        def value(update):
            global contador_toques
            if pin_tactil.value() == 1:
                relay.value(1)
                print("Tocado")
                update.reply('El casco está asegurado ✔')
                update.reply('Todo listo, ya podemos arrancar ✔')
                update.reply('No olvides ser prudente con las normas de tránsito 😉')
                iniciar_rodada()  # Llama a la función para crear el registro de inicio de rodada
            else:
                relay.value(0)
                print("No Tocado")
                update.reply('🚨Asegure su casco🚨')
                update.reply('Así no podemos empezar tu recorrido 😔')

        @bot.add_message_handler('terminar rodada')
        def finish_ride(update):
            update.reply('Recorrido terminado. ¡Gracias por usar Securide!')
            finalizar_rodada()  # Llama a la función para crear el registro de finalización de rodada

        @bot.add_message_handler('Datos de mi rodada')
        def get_rodada_data(update):
            data = obtener_datos_rodada()
            if data:
                message = "Datos de tu rodada:\n"
                for key, value in data.items():
                    message += f"{key}: {value}\n"
                update.reply(message)
            else:
                update.reply('No se encontraron datos de rodada.')

        bot.start_loop()
else:
    print("Imposible conectar a la red Wi-Fi")
