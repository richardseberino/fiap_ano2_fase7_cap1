/** Tela 1 · Sinais vitais coletados pelos dispositivos IoT (via InfluxDB → gateway). */
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';

import { Sparkline } from '@/components/sparkline';
import { Aviso, Botao, Cartao, Chip, Icone, T, Tela, Vazio, type IconName } from '@/components/ui';
import { corNivel, NIVEL_TEXTO, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Leitura, SinaisPaciente } from '@/lib/api';
import { useAjustes } from '@/lib/settings';

const ATUALIZACAO_MS = 10000;
const JANELAS = [
  { rotulo: '15 min', minutos: 15 },
  { rotulo: '1 h', minutos: 60 },
  { rotulo: '6 h', minutos: 360 },
];

type Metrica = {
  campo: 'bpm' | 'oxigenacao' | 'temperatura' | 'pa_sistolica';
  nome: string;
  unidade: string;
  icone: IconName;
  casas: number;
  faixa: [number, number];
  nivel: (v: number) => 0 | 1 | 2;
};

// Mesmos limites usados no edge (firmware) e na base de protocolos do multiagente.
const METRICAS: Metrica[] = [
  { campo: 'bpm', nome: 'Freq. cardíaca', unidade: 'bpm', icone: 'heart', casas: 0, faixa: [55, 110],
    nivel: (v) => (v > 120 || v < 45 ? 2 : v > 110 || v < 55 ? 1 : 0) },
  { campo: 'oxigenacao', nome: 'SpO2', unidade: '%', icone: 'water', casas: 1, faixa: [92, 100],
    nivel: (v) => (v < 88 ? 2 : v < 92 ? 1 : 0) },
  { campo: 'temperatura', nome: 'Temperatura', unidade: '°C', icone: 'thermometer', casas: 1, faixa: [35.5, 37.5],
    nivel: (v) => (v > 38 || v < 35 ? 2 : v > 37.5 || v < 35.5 ? 1 : 0) },
  { campo: 'pa_sistolica', nome: 'PA sistólica', unidade: 'mmHg', icone: 'speedometer', casas: 0, faixa: [100, 160],
    nivel: (v) => (v < 90 || v > 180 ? 2 : v < 100 || v > 160 ? 1 : 0) },
];

function haQuanto(iso?: string | null) {
  if (!iso) return '—';
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `há ${s}s`;
  if (s < 3600) return `há ${Math.round(s / 60)} min`;
  return `há ${Math.round(s / 3600)} h`;
}

export default function SinaisScreen() {
  const p = useTheme();
  const { api, pacienteId, definirPaciente, carregado } = useAjustes();
  const [pacientes, setPacientes] = useState<Leitura[] | null>(null);
  const [detalhe, setDetalhe] = useState<SinaisPaciente | null>(null);
  const [minutos, setMinutos] = useState(15);
  const [erro, setErro] = useState<string | null>(null);
  const [atualizando, setAtualizando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const lista = await api.sinaisTodos();
      setPacientes(lista);
      let alvo = pacienteId;
      if (!alvo || !lista.some((l) => l.paciente_id === alvo)) {
        alvo = lista.find((l) => (l.nivel_alerta ?? 0) >= 2)?.paciente_id ?? lista[0]?.paciente_id ?? null;
        if (alvo) definirPaciente(alvo);
      }
      setDetalhe(alvo ? await api.sinaisPaciente(alvo, minutos) : null);
      setErro(null);
    } catch (e) {
      setErro((e as Error).message);
    }
  }, [api, minutos, pacienteId, definirPaciente]);

  // Atualiza ao entrar na aba, ao trocar paciente/janela e a cada 10 s enquanto a aba estiver visível.
  useFocusEffect(
    useCallback(() => {
      if (!carregado) return;
      carregar();
      const id = setInterval(carregar, ATUALIZACAO_MS);
      return () => clearInterval(id);
    }, [carregar, carregado]),
  );

  const atualizarManual = async () => {
    setAtualizando(true);
    await carregar();
    setAtualizando(false);
  };

  const ultimo = detalhe?.ultimo;
  const nivelGeral = ultimo?.nivel_alerta ?? null;
  const cor = corNivel(p, nivelGeral);
  const criticos = (pacientes ?? []).filter((l) => (l.nivel_alerta ?? 0) >= 2).length;

  return (
    <Tela
      titulo="Sinais vitais"
      subtitulo={pacientes ? `${pacientes.length} monitorados · ${criticos} em estado crítico` : 'Monitoramento IoT em tempo real'}
      acao={
        <Botao titulo="" icone="refresh" variante="fantasma" onPress={atualizarManual} carregando={atualizando}
          style={{ width: 48, paddingHorizontal: 0 }} />
      }>
      {erro ? <Aviso texto={erro} acao={<Botao titulo="Abrir ajustes" variante="fantasma" onPress={() => router.push('/ajustes')} />} /> : null}

      {pacientes === null && !erro ? <ActivityIndicator style={{ marginTop: 40 }} color={p.primary} /> : null}

      {pacientes && pacientes.length === 0 ? (
        <Vazio icone="hardware-chip-outline" titulo="Nenhum dispositivo enviando dados"
          texto="Inicie o simulador Wokwi (ESP32-S3 / Pico W) ou o iot-simulador do cluster. As leituras aparecem aqui em até 10 s." />
      ) : null}

      {pacientes && pacientes.length > 0 ? (
        <>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: Spacing.two }}>
            {pacientes.map((l) => (
              <Chip key={l.paciente_id} texto={l.paciente_id} ativo={l.paciente_id === pacienteId}
                corPonto={corNivel(p, l.nivel_alerta).fg} onPress={() => definirPaciente(l.paciente_id)} />
            ))}
          </ScrollView>

          {ultimo ? (
            <Cartao tom={cor.bg} style={{ borderColor: cor.bg }}>
              <View style={st.linha}>
                <Icone nome={nivelGeral && nivelGeral >= 1 ? 'warning' : 'checkmark-circle'} cor={cor.fg} tamanho={28} />
                <View style={{ flex: 1 }}>
                  <T v="subtitulo" cor={cor.fg}>
                    {nivelGeral != null ? NIVEL_TEXTO[Math.min(2, Math.round(nivelGeral))] : 'Sem classificação'}
                    {ultimo.panico ? ' · botão de pânico' : ''}
                  </T>
                  <T v="pequeno" cor="textSecondary">
                    {[ultimo.setor, ultimo.origem === 'wokwi' ? 'dispositivo Wokwi' : ultimo.origem, haQuanto(ultimo.horario)]
                      .filter(Boolean).join(' · ')}
                  </T>
                </View>
              </View>
            </Cartao>
          ) : null}

          <View style={st.janelas}>
            {JANELAS.map((j) => (
              <Chip key={j.minutos} texto={j.rotulo} ativo={minutos === j.minutos} onPress={() => setMinutos(j.minutos)} />
            ))}
          </View>

          <View style={st.grade}>
            {METRICAS.map((m) => {
              const valor = ultimo?.[m.campo];
              const nv = valor != null ? m.nivel(valor) : null;
              const c = corNivel(p, nv);
              return (
                <Cartao key={m.campo} style={st.metrica}>
                  <View style={st.linha}>
                    <Icone nome={m.icone} cor={c.fg} tamanho={16} />
                    <T v="pequeno" cor="textSecondary" style={{ flex: 1 }} numberOfLines={1}>{m.nome}</T>
                  </View>
                  <View style={[st.linha, { alignItems: 'baseline' }]}>
                    <T v="numero" cor={nv ? c.fg : 'text'}>{valor != null ? valor.toFixed(m.casas) : '--'}</T>
                    <T v="pequeno" cor="textSecondary">{m.unidade}</T>
                  </View>
                  <Sparkline valores={(detalhe?.serie ?? []).map((pt) => pt[m.campo])} cor={c.fg === p.textSecondary ? p.primary : c.fg} faixa={m.faixa} />
                </Cartao>
              );
            })}
          </View>

          {pacienteId ? (
            <Botao titulo="Analisar com a IA multiagente" icone="git-network"
              onPress={() => router.push({ pathname: '/analise', params: { paciente: pacienteId } })} />
          ) : null}
          <T v="pequeno" cor="textSecondary" style={{ textAlign: 'center' }}>
            Atualização automática a cada 10 s · médias móveis calculadas no dispositivo (edge)
          </T>
        </>
      ) : null}
    </Tela>
  );
}

const st = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  janelas: { flexDirection: 'row', gap: Spacing.two },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three },
  metrica: { flexBasis: '47%', flexGrow: 1, gap: Spacing.one, padding: Spacing.three },
});
