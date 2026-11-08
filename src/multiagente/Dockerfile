# Serviço multiagente: FastAPI + OpenAI Agents SDK + Random Forest (scikit-learn)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HISTORICO_DB=/var/lib/multiagente/historico_atendimentos.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/pacientes/ ./data/pacientes/
COPY data/base_sintetica_pico_risco.csv ./data/

RUN useradd --uid 10001 --create-home app \
 && mkdir -p /var/lib/multiagente && chown -R app /var/lib/multiagente /app/data
USER 10001

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8001/health')"
CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8001"]
