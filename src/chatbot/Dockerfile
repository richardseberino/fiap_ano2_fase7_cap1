# Serviço chatbot: assistente de triagem cardiológica (Flask + NLP local / IBM Watson Assistant)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FLASK_HOST=0.0.0.0 FLASK_PORT=5000 FLASK_DEBUG=false USE_WATSON=false

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY run.py .

RUN useradd --uid 10001 app
USER 10001

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:5000/api/health')"
# 1 worker com threads: as sessões de conversa ficam em memória no processo.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "backend.app:app"]
