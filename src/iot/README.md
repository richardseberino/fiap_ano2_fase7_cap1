# IoT · Monitor de sinais vitais em MicroPython

Firmware do monitor de sinais vitais do CardioIA, reescrito para ser **portável entre placas**. A camada de hardware (`placa.py`) isola pinos e periféricos. A lógica de edge computing (`edge.py`) é Python puro e roda igual em MicroPython e em CPython.

| Plataforma | Onde roda | CPU / memória | Projeto |
|---|---|---|---|
| ESP32 DevKitC v4 | Wokwi / placa física | Xtensa dual-core 240 MHz · 520 KB | [wokwi/esp32](wokwi/esp32/diagram.json) |
| **ESP32-S3 DevKitC-1** | Wokwi / placa física | Xtensa LX7 dual-core 240 MHz · 512 KB + PSRAM · instruções vetoriais | [wokwi/esp32-s3](wokwi/esp32-s3/diagram.json) |
| **Raspberry Pi Pico W / Pico 2 W** | Wokwi / placa física | RP2040 / RP2350 | [wokwi/pico-w](wokwi/pico-w/diagram.json) |
| **Linux** (Raspberry Pi 4/5, PC, container) | CPython 3.10+ | ARM/x86 multi-core | `python main.py` / imagem `cardioia-iot-simulador` |

> Na fase anterior o firmware era um script único, preso aos pinos do ESP32. Ele usava a umidade do DHT22 como se fosse SpO2 e não guardava nada quando a rede caía. Esta versão corrige esses pontos e roda sem alteração em dispositivos mais potentes.

## Sensores e atuadores (simulação no Wokwi)

| Elemento | Sinal | ESP32 | ESP32-S3 | Pico W |
|---|---|---|---|---|
| Potenciômetro 1 | Frequência cardíaca (40–180 bpm) | GPIO34 | GPIO4 | GP26 (ADC0) |
| Potenciômetro 2 | SpO2 (80–100%) | GPIO35 | GPIO5 | GP27 (ADC1) |
| Potenciômetro 3 | PA sistólica (70–200 mmHg) | GPIO32 | GPIO6 | GP28 (ADC2) |
| DHT22 | Temperatura corporal | GPIO15 | GPIO15 | GP15 |
| OLED SSD1306 (I2C 0x3C) | Painel local | SDA21 / SCL22 | SDA8 / SCL9 | SDA GP4 / SCL GP5 |
| LED verde / vermelho | Normal / alerta (pisca no crítico) | 19 / 23 | 17 / 16 | GP13 / GP14 |
| Buzzer (PWM) | Alarme crítico e pânico | GPIO18 | GPIO18 | GP12 |
| Botão vermelho | Pânico: envio imediato | GPIO4 | GPIO21 | GP16 |

Os potenciômetros fazem o papel dos sensores analógicos, como oxímetro e monitor de pressão. Em hardware real, eles seriam trocados por um MAX30102 (FC e SpO2) e um sensor de pressão; nesse caso, basta mudar `PlacaMicro.ler()`.

## Edge computing

1. **Amostragem a cada 1 s** e **média móvel de 10 amostras**, que filtra o ruído antes de transmitir. O DHT22 é lido no máximo a cada 2 s.
2. **Classificação local** em `NORMAL`, `ATENCAO` ou `CRITICO`. Os limites de crítico são os mesmos que acionam protocolos no serviço multiagente (SpO2 < 88, FC > 120, T > 38 °C, PAS < 90); a faixa de atenção é a margem antes deles. O alarme local funciona mesmo sem rede.
3. **Publicação inteligente:** a média vai a cada 10 s, e a publicação é **imediata** quando o nível piora ou quando o botão de pânico é pressionado.
4. **Store-and-forward:** até 60 mensagens (cerca de 10 min) ficam na fila enquanto o broker está fora. Na reconexão, elas são enviadas em ordem, com número de sequência (`seq`).
5. **Reconexão automática** de Wi-Fi e MQTT, sem travar o ciclo de leitura.

## Como executar no Wokwi

1. Crie um projeto MicroPython para a placa:
   - ESP32-S3: https://wokwi.com/projects/new/micropython-esp32-s3
   - Pico W: https://wokwi.com/projects/new/micropython-pi-pico-w
   - ESP32: https://wokwi.com/projects/new/micropython-esp32
2. Na aba `diagram.json`, cole o conteúdo de `wokwi/<placa>/diagram.json`.
3. Substitua o `main.py` e crie os arquivos (botão **+** → *New file*) `config.py`, `placa.py`, `edge.py`, `conectividade.py`, `compat.py` e `ssd1306.py` com o conteúdo de [`firmware/`](firmware). Não é preciso o `simulador.py`.
4. Se quiser, edite `PACIENTE_ID` em `config.py` para identificar o dispositivo no app.
5. Clique em **Play**. O monitor serial mostra a conexão e cada envio:
   ```
   CardioIA monitor | placa=ESP32S3 | paciente=PAC-WOKWI-01 | broker=broker.hivemq.com
   MQTT conectado em broker.hivemq.com:1883 como cardioia-esp32s3-...
   [PAC-WOKWI-01 #3] FC=118 SpO2=89.4 T=36.8 PAS=135 -> ATENCAO SpO2 baixa (89.4); Taquicardia (118)
   ```
6. Gire os potenciômetros, clique no DHT22 para mudar a temperatura e pressione o botão de pânico. Os LEDs, o buzzer e o OLED reagem na hora. Os dados aparecem na aba **Sinais** do app e no Grafana.

### Como os dados saem do Wokwi e chegam ao cluster

A rede `Wokwi-GUEST` acessa a internet, mas não o seu cluster. Por isso o firmware publica em `broker.hivemq.com`, no tópico `fiap-drell/cardioia/sinais-vitais/<paciente>`, e o Mosquitto do cluster mantém um **bridge** que assina esse tópico ([config/mosquitto/mosquitto.conf](../../config/mosquitto/mosquitto.conf)). O Telegraf consome o tópico local e o tópico do bridge.

Com o **Wokwi Private Gateway** ou um **dispositivo físico** na mesma rede, aponte `MQTT_BROKER` para o IP do Mosquitto (Service `mosquitto-externo`, porta 1883) e `MQTT_PREFIXO` para `cardioia/sinais-vitais`.

> O broker público serve só para a demonstração. Em produção, use um listener MQTT com TLS (8883) e autenticação por dispositivo.

## Como executar em Linux (dispositivo mais potente)

```bash
cd firmware
pip install -r requirements.txt
MQTT_BROKER=localhost MQTT_PREFIXO=cardioia/sinais-vitais PACIENTE_ID=PAC-RPI-01 PERFIL_SIMULADO=hipoxemia python main.py
# vários pacientes virtuais com o mesmo firmware (é o que roda no pod iot-simulador):
PACIENTES="PAC-101:estavel,PAC-105:choque" MQTT_BROKER=localhost MQTT_PREFIXO=cardioia/sinais-vitais python simulador.py
```

Os perfis clínicos simulados são `estavel`, `taquicardia`, `hipoxemia`, `febril` e `choque`. Os valores fazem um passeio aleatório com reversão à média e têm episódios transitórios ocasionais.

## Testes

```bash
pip install -r firmware/requirements.txt
pytest -q tests                       # 11 testes: edge, fila offline, ciclo do dispositivo
pip install mpy-cross && for f in firmware/*.py; do mpy-cross "$f"; done   # valida a sintaxe MicroPython
```

## Estrutura

```
iot/
├── firmware/
│   ├── main.py            ciclo do dispositivo (leitura → edge → alarme → MQTT)
│   ├── config.py          Wi-Fi, broker, paciente, intervalos (sobrescrevível por env no Linux)
│   ├── placa.py           HAL: ESP32 / ESP32-S3 / Pico W / Linux
│   ├── edge.py            média móvel, classificação, fila offline, payload (Python puro)
│   ├── conectividade.py   Wi-Fi + MQTT com reconexão e store-and-forward
│   ├── compat.py          compatibilidade MicroPython ↔ CPython
│   ├── ssd1306.py         driver mínimo do OLED
│   └── simulador.py       vários monitores virtuais (Linux/container)
├── wokwi/{esp32,esp32-s3,pico-w}/diagram.json
├── tests/test_firmware.py
└── Dockerfile             imagem cardioia-iot-simulador
```
