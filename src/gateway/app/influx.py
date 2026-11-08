"""Acesso de leitura aos sinais vitais gravados pelo Telegraf no InfluxDB 2.x.

Esquema (measurement `sinais_vitais`):
    tags   : paciente_id, setor, dispositivo, origem
    fields : bpm, oxigenacao, temperatura, pa_sistolica, nivel_alerta (0 normal, 1 atenção, 2 crítico), panico
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from influxdb_client import InfluxDBClient

from .config import Settings

log = logging.getLogger("gateway.influx")

CAMPOS = ("bpm", "oxigenacao", "temperatura", "pa_sistolica", "nivel_alerta", "panico")
TAGS = ("setor", "dispositivo", "origem")
_ID_VALIDO = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


def _validar_id(paciente_id: str) -> str:
    # O id entra em uma query Flux; aceitamos só caracteres seguros para evitar injeção.
    if not _ID_VALIDO.match(paciente_id):
        raise ValueError("paciente_id inválido")
    return paciente_id


class RepositorioSinais:
    def __init__(self, settings: Settings):
        self.s = settings
        self._cliente: InfluxDBClient | None = None

    @property
    def cliente(self) -> InfluxDBClient:
        if self._cliente is None:
            self._cliente = InfluxDBClient(url=self.s.influx_url, token=self.s.influx_token,
                                           org=self.s.influx_org, timeout=10_000)
        return self._cliente

    def fechar(self) -> None:
        if self._cliente is not None:
            self._cliente.close()

    def _query(self, flux: str):
        return self.cliente.query_api().query(flux, org=self.s.influx_org)

    def _base(self, inicio: str) -> str:
        return (f'from(bucket: "{self.s.influx_bucket}")\n'
                f'  |> range(start: {inicio})\n'
                f'  |> filter(fn: (r) => r._measurement == "{self.s.influx_measurement}")\n')

    # ------------------------------------------------------------------
    def saude(self) -> dict:
        try:
            ok = self.cliente.ping()
            return {"servico": "influxdb", "ok": bool(ok)}
        except Exception as erro:  # noqa: BLE001
            return {"servico": "influxdb", "ok": False, "erro": str(erro)[:200]}

    def ultimas_leituras(self, horas: int = 24) -> list[dict]:
        """Última leitura de cada paciente (uma linha por paciente)."""
        flux = self._base(f"-{horas}h") + '  |> group(columns: ["paciente_id", "_field"])\n  |> last()'
        pacientes: dict[str, dict] = {}
        for tabela in self._query(flux):
            for r in tabela.records:
                pid = r.values.get("paciente_id")
                if not pid:
                    continue
                item = pacientes.setdefault(pid, {"paciente_id": pid, "horario": None})
                item[r.get_field()] = r.get_value()
                horario: datetime = r.get_time()
                if item["horario"] is None or horario.isoformat() > item["horario"]:
                    item["horario"] = horario.isoformat()
        # tags (setor, dispositivo, origem) vêm de uma consulta leve à última linha de bpm
        flux_tags = self._base(f"-{horas}h") + (
            '  |> filter(fn: (r) => r._field == "bpm")\n'
            '  |> group(columns: ["paciente_id"])\n  |> last()')
        for tabela in self._query(flux_tags):
            for r in tabela.records:
                item = pacientes.get(r.values.get("paciente_id"))
                if item:
                    item.update({t: r.values.get(t) for t in TAGS})
        return sorted(pacientes.values(), key=lambda p: p["paciente_id"])

    def serie(self, paciente_id: str, minutos: int = 60, pontos: int = 120) -> list[dict]:
        """Série temporal agregada (média por janela) para gráficos."""
        pid = _validar_id(paciente_id)
        janela = max(10, (minutos * 60) // pontos)
        flux = self._base(f"-{minutos}m") + (
            f'  |> filter(fn: (r) => r.paciente_id == "{pid}")\n'
            f'  |> group(columns: ["_field"])\n'
            f'  |> aggregateWindow(every: {janela}s, fn: mean, createEmpty: false)')
        pontos_por_horario: dict[str, dict] = {}
        for tabela in self._query(flux):
            for r in tabela.records:
                chave = r.get_time().isoformat()
                ponto = pontos_por_horario.setdefault(chave, {"horario": chave})
                valor = r.get_value()
                ponto[r.get_field()] = round(valor, 2) if isinstance(valor, float) else valor
        return [pontos_por_horario[k] for k in sorted(pontos_por_horario)]

    def contar_episodios_alerta(self, paciente_id: str, minutos: int) -> int:
        """Conta episódios de alerta (transições de normal para atenção/crítico), por minuto."""
        pid = _validar_id(paciente_id)
        flux = self._base(f"-{minutos}m") + (
            f'  |> filter(fn: (r) => r.paciente_id == "{pid}" and r._field == "nivel_alerta")\n'
            f'  |> group()\n'
            f'  |> aggregateWindow(every: 1m, fn: max, createEmpty: false)')
        niveis = [r.get_value() or 0 for tabela in self._query(flux) for r in tabela.records]
        return contar_subidas(niveis)


def contar_subidas(niveis: list[float]) -> int:
    """Número de vezes em que a série sai de 0 (normal) para >= 1 (alerta)."""
    episodios, anterior = 0, 0
    for nivel in niveis:
        if nivel >= 1 and anterior < 1:
            episodios += 1
        anterior = nivel
    return episodios
