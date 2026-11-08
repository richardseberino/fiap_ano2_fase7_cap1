# Executa vários monitores virtuais (um por paciente) com o MESMO firmware do Wokwi,
# usando a placa Linux (sensores simulados por perfil clínico).
#
#   PACIENTES="PAC-101:estavel:UTI_01,PAC-102:hipoxemia:UTI_01" MQTT_BROKER=localhost python simulador.py
import os
import threading

import config
from main import Dispositivo
from placa import PlacaLinux

PADRAO = "PAC-101:estavel:UTI_01,PAC-102:taquicardia:UTI_01,PAC-103:hipoxemia:UTI_02,PAC-104:febril:ENFERMARIA,PAC-105:choque:UTI_02"


def main():
    especificacao = os.getenv("PACIENTES", PADRAO)
    threads = []
    for item in especificacao.split(","):
        paciente_id, perfil, setor = (item.strip().split(":") + ["estavel", config.SETOR])[:3]
        placa = PlacaLinux(perfil, id_dispositivo="sim-%s" % paciente_id.lower())
        t = threading.Thread(target=Dispositivo(placa, paciente_id, setor).executar, name=paciente_id, daemon=True)
        t.start()
        threads.append(t)
        print("Monitor virtual iniciado: %s (perfil %s, setor %s)" % (paciente_id, perfil, setor))
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
