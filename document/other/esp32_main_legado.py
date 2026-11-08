import network
import time
from machine import Pin, ADC
import dht
import ujson
from umqtt.simple import MQTTClient

# MQTT Server Parameters
MQTT_CLIENT_ID = "wokwi"
MQTT_BROKER    = "192.168.0.3"
MQTT_USER      = ""
MQTT_PASSWORD  = ""
MQTT_TOPIC     = "dados-medicos"

sensor = dht.DHT22(Pin(15))
pot = ADC(Pin(34))
led_vermelho = Pin(23, Pin.OUT)

def ler_batimentos():
  # Lê o valor bruto (0 a 4095)
  valor_bruto = pot.read()
    
  # 3. Transformando o valor em BPM (Batimentos Por Minuto)
  # Vamos mapear: 0 -> 60 BPM (repouso) e 4095 -> 180 BPM (exercício intenso)
  bpm = int(60 + (valor_bruto / 4095) * 120)
    
  return bpm

def verifica_sinais(bpm, oxigenacao, temperatura):

  # Definição dos critérios de normalidade
  bpm_fora = bpm < 60 or bpm > 110
  oxigenacao_fora = oxigenacao < 95
  temperatura_fora = temperatura < 35.0 or temperatura > 37.5

  # Se qualquer um dos critérios for "fora", retorna False indicando que os sinais vitais não estão bons
  if bpm_fora or oxigenacao_fora or temperatura_fora:
    return False
    
  # SInais vitais estão normais
  return True  


print("Conectando na rede WiFi", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '')
while not sta_if.isconnected():
  print(".", end="")
  time.sleep(0.1)
#print(" Conectado!")
print("\nConectado! IP do ESP32:", sta_if.ifconfig()[0])

print("COnectando no Servidor MQTT local (mosquito)... ", end="")
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
client.connect()

print("Conectado ao Broker MQTT!")

prev_weather = ""
while True:
  print("Measuring weather conditions... ", end="")
  sensor.measure() 
  meu_bpm = ler_batimentos()
  meu_oxi = sensor.humidity()
  meu_temp = sensor.temperature()
  message = ujson.dumps({
    "temp":meu_temp,
    "oxi": meu_oxi,
    "bpm": meu_bpm
  })

  print("Enviado dados o Topico MQTT {}: {}".format(MQTT_TOPIC, message))
  client.publish(MQTT_TOPIC, message)

  if verifica_sinais(meu_bpm, meu_oxi,meu_temp):
    led_vermelho.value(0)
  else:
    led_vermelho.value(1)

  time.sleep(10)
