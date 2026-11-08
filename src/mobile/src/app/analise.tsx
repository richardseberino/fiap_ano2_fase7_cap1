/** Tela 2 · Entrada manual (ou pré-preenchida pelo IoT) para análise pelo sistema multiagente. */
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { Aviso, Barra, Botao, Campo, Cartao, Chip, Icone, Secao, Selo, T, Tela } from '@/components/ui';
import { corClassificacao, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { DadosPaciente, RespostaAnalise } from '@/lib/api';
import { useAjustes } from '@/lib/settings';

type Chave = keyof DadosPaciente;
type Def = { chave: Chave; rotulo: string; unidade?: string; min: number; max: number; inteiro?: boolean; dica?: string };

// Faixas idênticas às validações Pydantic do serviço multiagente (DadosPaciente).
const GRUPOS: { titulo: string; campos: Def[] }[] = [
  { titulo: 'Sinais vitais', campos: [
    { chave: 'fc_media', rotulo: 'Freq. cardíaca', unidade: 'bpm', min: 20, max: 250 },
    { chave: 'spo2_media', rotulo: 'SpO2', unidade: '%', min: 50, max: 100 },
    { chave: 'pa_sistolica', rotulo: 'PA sistólica', unidade: 'mmHg', min: 40, max: 260 },
    { chave: 'temperatura', rotulo: 'Temperatura', unidade: '°C', min: 30, max: 45 },
  ] },
  { titulo: 'Paciente e histórico', campos: [
    { chave: 'idade_media', rotulo: 'Idade', unidade: 'anos', min: 0, max: 120 },
    { chave: 'eventos_24h', rotulo: 'Eventos em 24 h', min: 0, max: 100, inteiro: true },
    { chave: 'densidade_eventos', rotulo: 'Densidade de eventos', min: 0, max: 100, inteiro: true, dica: 'Eventos na janela recente' },
  ] },
  { titulo: 'Contexto operacional', campos: [
    { chave: 'carga_sistema', rotulo: 'Carga do sistema', unidade: '%', min: 0, max: 100 },
    { chave: 'tempo_espera', rotulo: 'Tempo de espera', unidade: 'min', min: 0, max: 600 },
    { chave: 'disponibilidade_recursos', rotulo: 'Recursos disponíveis', unidade: '%', min: 0, max: 100 },
  ] },
];
const DEFS = GRUPOS.flatMap((g) => g.campos);
const vazio = Object.fromEntries(DEFS.map((d) => [d.chave, ''])) as Record<Chave, string>;

const AGENTES = [
  { nome: 'Orquestrador', papel: 'coordena o fluxo e os handoffs' },
  { nome: 'Analista de Risco', papel: 'modelo Random Forest (pico de risco)' },
  { nome: 'Especialista em Protocolos', papel: 'cruza risco e sinais com a base' },
  { nome: 'Planejador de Resposta', papel: 'ações, responsáveis e prazos' },
];

function validar(valores: Record<Chave, string>) {
  const erros: Partial<Record<Chave, string>> = {};
  const dados = {} as DadosPaciente;
  for (const d of DEFS) {
    const bruto = valores[d.chave].replace(',', '.').trim();
    if (!bruto) { erros[d.chave] = 'Obrigatório'; continue; }
    const n = Number(bruto);
    if (!Number.isFinite(n)) erros[d.chave] = 'Número inválido';
    else if (n < d.min || n > d.max) erros[d.chave] = `Entre ${d.min} e ${d.max}`;
    else if (d.inteiro && !Number.isInteger(n)) erros[d.chave] = 'Número inteiro';
    else dados[d.chave] = n;
  }
  return { erros, dados };
}

export default function AnaliseScreen() {
  const p = useTheme();
  const { api, pacienteId, definirUltimaAnalise } = useAjustes();
  const params = useLocalSearchParams<{ paciente?: string }>();
  const [valores, setValores] = useState(vazio);
  const [idPaciente, setIdPaciente] = useState('');
  const [erros, setErros] = useState<Partial<Record<Chave, string>>>({});
  const [exemplos, setExemplos] = useState<{ paciente_id: string; dados: DadosPaciente }[]>([]);
  const [info, setInfo] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregandoIot, setCarregandoIot] = useState(false);
  const [analisando, setAnalisando] = useState(false);
  const [resultado, setResultado] = useState<RespostaAnalise | null>(null);

  useEffect(() => {
    api.exemplos().then(setExemplos).catch(() => setExemplos([]));
  }, [api]);

  useEffect(() => {
    if (params.paciente) preencherIot(params.paciente);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.paciente]);

  const aplicar = (dados: Partial<Record<Chave, number | null>>, manter = false) =>
    setValores((v) => {
      const novo = { ...v };
      for (const d of DEFS) {
        const x = dados[d.chave];
        if (x != null) novo[d.chave] = String(x);
        else if (!manter) novo[d.chave] = '';
      }
      return novo;
    });

  async function preencherIot(id = pacienteId ?? '') {
    if (!id) { setErro('Selecione um paciente na aba Sinais para usar os dados do IoT.'); return; }
    setCarregandoIot(true); setErro(null); setResultado(null);
    try {
      const s = await api.sugestao(id);
      aplicar(s.dados, true);
      setIdPaciente(id);
      setInfo(`Sinais de ${id} preenchidos com a média de ${s.amostras} leituras (últimos ${s.janela_minutos} min). Complete os dados operacionais.`);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregandoIot(false);
    }
  }

  async function analisar() {
    const { erros: e, dados } = validar(valores);
    setErros(e);
    if (Object.keys(e).length) { setErro('Revise os campos destacados.'); return; }
    setErro(null); setInfo(null); setAnalisando(true); setResultado(null);
    try {
      const r = await api.analisar(idPaciente.trim() || undefined, dados);
      setResultado(r);
      definirUltimaAnalise(r);
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setAnalisando(false);
    }
  }

  return (
    <Tela titulo="Análise IA" subtitulo="Sistema multiagente · modelo preditivo + protocolos">
      <Cartao>
        <T v="pequeno" cor="textSecondary">Preencha manualmente, use os sinais do IoT ou carregue um caso de exemplo.</T>
        <Botao titulo={pacienteId ? `Usar sinais do IoT (${pacienteId})` : 'Usar sinais do IoT'} icone="pulse"
          variante="secundario" carregando={carregandoIot} onPress={() => preencherIot()} />
        {exemplos.length ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: Spacing.two }}>
            {exemplos.map((ex) => (
              <Chip key={ex.paciente_id} texto={ex.paciente_id.replace(/^PAC-\d+-?/, '') || ex.paciente_id}
                onPress={() => { aplicar(ex.dados); setIdPaciente(ex.paciente_id); setResultado(null); setInfo(null); }} />
            ))}
          </ScrollView>
        ) : null}
      </Cartao>

      {info ? <Aviso tipo="info" texto={info} /> : null}

      <Campo rotulo="Identificação do paciente (opcional)" value={idPaciente} onChangeText={setIdPaciente}
        placeholder="PAC-001" autoCapitalize="characters" />

      {GRUPOS.map((g) => (
        <Secao key={g.titulo} titulo={g.titulo}>
          <View style={st.grade}>
            {g.campos.map((d) => (
              <Campo key={d.chave} rotulo={d.rotulo} unidade={d.unidade} dica={d.dica} erro={erros[d.chave]}
                value={valores[d.chave]} keyboardType="decimal-pad" inputMode="decimal" style={st.campo}
                onChangeText={(t) => { setValores((v) => ({ ...v, [d.chave]: t })); setErros((x) => ({ ...x, [d.chave]: undefined })); }} />
            ))}
          </View>
        </Secao>
      ))}

      {erro ? <Aviso texto={erro} /> : null}

      <Botao titulo={analisando ? 'Agentes trabalhando…' : 'Executar análise multiagente'} icone="sparkles"
        carregando={analisando} onPress={analisar} />

      {analisando ? (
        <Cartao>
          {AGENTES.map((a, i) => (
            <View key={a.nome} style={st.agente}>
              <View style={[st.numero, { backgroundColor: p.primarySoft }]}><T v="pequeno" cor="primary" style={{ fontWeight: '700' }}>{i + 1}</T></View>
              <View style={{ flex: 1 }}>
                <T style={{ fontWeight: '600' }}>{a.nome}</T>
                <T v="pequeno" cor="textSecondary">{a.papel}</T>
              </View>
            </View>
          ))}
        </Cartao>
      ) : null}

      {resultado ? <Resultado r={resultado} /> : null}
    </Tela>
  );
}

function Resultado({ r }: { r: RespostaAnalise }) {
  const p = useTheme();
  const rec = r.recomendacao;
  const cor = corClassificacao(p, rec.classificacao_risco);
  const pct = Math.round(rec.probabilidade_pico_risco * 100);

  return (
    <View style={{ gap: Spacing.four }}>
      <Cartao tom={cor.bg} style={{ borderColor: cor.bg }}>
        <View style={st.linha}>
          <T v="rotulo" cor="textSecondary" style={{ flex: 1 }}>Risco de pico · {rec.paciente_id}</T>
          <Selo texto={r.modo === 'llm' ? 'LLM + agentes' : 'Offline (ML + regras)'} fg={p.info} bg={p.infoSoft}
            icone={r.modo === 'llm' ? 'sparkles' : 'hardware-chip'} />
        </View>
        <View style={[st.linha, { alignItems: 'baseline' }]}>
          <T v="numero" cor={cor.fg} style={{ fontSize: 44, lineHeight: 48 }}>{pct}%</T>
          <T v="subtitulo" cor={cor.fg}>{rec.classificacao_risco}</T>
        </View>
        <Barra valor={rec.probabilidade_pico_risco} cor={cor.fg} altura={10} />
        <T v="pequeno">{rec.justificativa}</T>
      </Cartao>

      {r.observacao ? <Aviso tipo="alerta" texto={r.observacao} /> : null}
      {r.guardrail_bloqueou ? <Aviso tipo="alerta" texto={`Guardrail de saída corrigiu a resposta do LLM: ${r.problemas.join('; ')}`} /> : null}

      {rec.fatores_de_risco.length ? (
        <Secao titulo="Fatores de risco">
          <Cartao style={{ gap: Spacing.two }}>
            {rec.fatores_de_risco.map((f) => (
              <View key={f} style={st.linha}><Icone nome="alert-circle" cor={p.warning} /><T v="pequeno" style={{ flex: 1 }}>{f}</T></View>
            ))}
          </Cartao>
        </Secao>
      ) : null}

      <Secao titulo={`Ações operacionais (${rec.acoes_operacionais.length})`}>
        {[...rec.acoes_operacionais].sort((a, b) => a.prioridade - b.prioridade).map((a, i) => {
          const c = a.prioridade === 1 ? { fg: p.danger, bg: p.dangerSoft } : a.prioridade === 2 ? { fg: p.warning, bg: p.warningSoft } : { fg: p.info, bg: p.infoSoft };
          return (
            <Cartao key={`${a.acao}-${i}`} style={{ gap: Spacing.two }}>
              <View style={st.linha}>
                <Selo texto={`P${a.prioridade}`} fg={c.fg} bg={c.bg} />
                <T v="pequeno" cor="textSecondary" style={{ flex: 1 }} numberOfLines={1}>{a.prazo}</T>
              </View>
              <T style={{ fontWeight: '600' }}>{a.acao}</T>
              <View style={st.linha}><Icone nome="person-circle-outline" /><T v="pequeno" cor="textSecondary">{a.responsavel}</T></View>
            </Cartao>
          );
        })}
      </Secao>

      {rec.protocolos_sugeridos.length ? (
        <Secao titulo="Protocolos acionados">
          <Cartao style={{ gap: Spacing.two }}>
            {rec.protocolos_sugeridos.map((pr) => (
              <View key={pr} style={st.linha}><Icone nome="document-text-outline" cor={p.primary} /><T v="pequeno" style={{ flex: 1 }}>{pr}</T></View>
            ))}
          </Cartao>
        </Secao>
      ) : null}

      {rec.parametros_em_atencao.length ? (
        <Secao titulo="Parâmetros perto do limite">
          <Cartao style={{ gap: Spacing.two }}>
            {rec.parametros_em_atencao.map((x) => <T key={x} v="pequeno">• {x}</T>)}
          </Cartao>
        </Secao>
      ) : null}

      <Secao titulo={`Trilha dos agentes · ${(r.duracao_ms / 1000).toFixed(1)} s`}>
        <Cartao style={{ gap: Spacing.two }}>
          {r.trilha.map((t, i) => (
            <View key={`${i}-${t}`} style={[st.linha, { alignItems: 'flex-start' }]}>
              <View style={[st.marcador, { backgroundColor: p.primary }]} />
              <T v="pequeno" style={{ flex: 1 }}>{t}</T>
            </View>
          ))}
        </Cartao>
      </Secao>

      {r.modo === 'llm' ? (
        <Botao titulo="Perguntar sobre esta análise" icone="chatbubbles" variante="secundario"
          onPress={() => router.push({ pathname: '/chat', params: { modo: 'analise' } })} />
      ) : null}
      <T v="pequeno" cor="textSecondary" style={{ textAlign: 'center' }}>{rec.aviso}</T>
    </View>
  );
}

const st = StyleSheet.create({
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three },
  campo: { flexBasis: '47%', flexGrow: 1 },
  linha: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  agente: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  numero: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  marcador: { width: 6, height: 6, borderRadius: 3, marginTop: 7 },
});
