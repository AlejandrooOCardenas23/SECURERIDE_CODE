import machine
from hcsr04 import HCSR04
import uasyncio as asyncio
import ufirebase as firebase
from utime import time, localtime
import network
import urequests  # Importa la librería urequests para hacer solicitudes HTTP

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
else:
    print("Imposible conectar a la red Wi-Fi")

# Configura la URL de Firebase
firebase.setURL("https://data-ride-default-rtdb.firebaseio.com/")

# Configura los parámetros de ThingSpeak
thingspeak_api_key = "K86ES8KSZU85X0TC"  # Reemplaza con tu clave de escritura de ThingSpeak
thingspeak_url = "https://api.thingspeak.com/update?api_key=K86ES8KSZU85X0TC&field1=0"

# Función para enviar datos a ThingSpeak
def enviar_datos_thingspeak(api_key, field1, field2, field3):
    try:
        payload = "api_key=" + api_key + "&field1=" + str(field1) + "&field2=" + str(field2) + "&field3=" + str(field3)
        response = urequests.post(thingspeak_url, data=payload)
        response.close()
        print("Datos enviados a ThingSpeak")
    except Exception as e:
        print("Error al enviar datos a ThingSpeak:", e)

# Función para medir la distancia y mostrar la alerta o no hay nadie
async def medir_distancia(sensor, umbral, nombre_sensor):
    while True:
        try:
            distancia = sensor.distance_cm()
            distancia_str = f"{distancia:.2f} cm"  # Formatear la distancia con 2 decimales
            etiqueta = f"{nombre_sensor}:"
            espacio = " " * (20 - len(etiqueta + distancia_str))
            print(f"{etiqueta}{espacio}{distancia_str}")
            if distancia <= umbral:
                print(f"Alerta en {nombre_sensor}")
                # Enviar una alerta a Firebase
                current_time = localtime(time())
                fecha = "{:02d}/{:02d}/{:04d}".format(current_time[2], current_time[1], current_time[0])
                hora = "{:02d}:{:02d}:{:02d}".format(current_time[3], current_time[4], current_time[5])
                ruta = f"SISTEMA DE COLISIÓN/{nombre_sensor}/DISTANCIA"
                mensaje = f"Distancia en {nombre_sensor}: {distancia} cm - Fecha: {fecha} - Hora: {hora}"
                firebase.put(ruta, {"Medida": distancia, "Fecha": fecha, "Hora": hora}, bg=0)
                # Enviar datos a ThingSpeak
                enviar_datos_thingspeak(thingspeak_api_key, distancia, distancia, distancia)
            else:
                print(f"No hay nadie en {nombre_sensor}")
            await asyncio.sleep(5)

        except Exception as e:
            print(f"Error en {nombre_sensor}: {e}")

async def main():
    # Crear objetos HCSR04
    medidor = HCSR04(trigger_pin=4, echo_pin=5)
    medidor2 = HCSR04(trigger_pin=18, echo_pin=19)
    medidor3 = HCSR04(trigger_pin=33, echo_pin=32)

    # Crear tareas asincrónicas para cada sensor
    medicion_izquierda = medir_distancia(medidor, 300, "IZQUIERDA")
    medicion_derecha = medir_distancia(medidor2, 300, "DERECHA")
    medicion_adelante = medir_distancia(medidor3, 50, "ADELANTE")

    # Iniciar las tareas asincrónicas
    asyncio.create_task(medicion_izquierda)
    asyncio.create_task(medicion_derecha)
    asyncio.create_task(medicion_adelante)

    # Ejecutar el bucle de eventos
    while True:
        await asyncio.sleep(1)

# Iniciar el bucle de eventos de uasyncio
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
