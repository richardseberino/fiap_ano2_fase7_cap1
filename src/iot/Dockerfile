# Monitor IoT em Linux: o mesmo firmware MicroPython rodando em CPython com sensores simulados.
# Usado no cluster para gerar dados contínuos de vários pacientes (deployment iot-simulador).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 MQTT_BROKER=mosquitto MQTT_PREFIXO=cardioia/sinais-vitais
WORKDIR /app
RUN pip install --no-cache-dir "paho-mqtt>=2.1"
COPY firmware/*.py ./
RUN useradd --uid 10001 app
USER 10001
CMD ["python", "simulador.py"]
