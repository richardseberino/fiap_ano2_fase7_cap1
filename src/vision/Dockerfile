# Serviço vision: classificação de imagens de ECG com CNN (TensorFlow/Keras) + Flask/Gunicorn
#
# O modelo treinado (cnn_ecg_model.keras, ~centenas de MB) não cabe no GitHub. Ele é obtido de:
#   1) um arquivo local cnn_ecg_model.keras na pasta src/vision (se existir), ou
#   2) da imagem publicada na Fase 4 (docker.io/seberino/fiap_2_4:1.0), padrão.
# O arquivo .keras não depende de arquitetura, por isso o stage abaixo fixa linux/amd64.
ARG MODEL_IMAGE=docker.io/seberino/fiap_2_4:1.0
FROM --platform=linux/amd64 ${MODEL_IMAGE} AS modelo

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TF_CPP_MIN_LOG_LEVEL=2 \
    MODEL_PATH=/app/cnn_ecg_model.keras
WORKDIR /app

COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=modelo /app/cnn_ecg_model.keras /app/cnn_ecg_model.keras
COPY webapp/ ./webapp/

RUN useradd --uid 10001 app
USER 10001

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:5000/health')"
# 1 worker: o modelo TensorFlow é carregado uma vez por processo; threads atendem em paralelo.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "--chdir", "/app/webapp", "app:app"]
