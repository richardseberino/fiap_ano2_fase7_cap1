/** Tela 3 · Assistente conversacional: triagem (chatbot NLP/Watson) ou perguntas sobre a última análise (multiagente). */
import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useRef, useState, type ComponentRef } from 'react';
import { KeyboardAvoidingView, Linking, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Aviso, Botao, Cartao, Chip, Icone, Selo, T, Tela } from '@/components/ui';
import { corClassificacao, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { ResumoChat } from '@/lib/api';
import { useAjustes } from '@/lib/settings';

type Msg = { id: string; autor: 'usuario' | 'bot'; texto: string; resumo?: ResumoChat | null; emergencia?: boolean; motor?: string };
type Modo = 'triagem' | 'analise';

const SUGESTOES_INICIAIS = ['Estou com dor no peito', 'Sinto falta de ar', 'Quais os fatores de risco para infarto?', 'Para que serve o eletrocardiograma?'];
const SUGESTOES_ANALISE = ['Por que meu risco ficou nesse nível?', 'Qual ação é mais urgente?', 'Quais parâmetros devo acompanhar?'];

const novoId = () => Math.random().toString(36).slice(2, 10);
const BOAS_VINDAS: Msg = {
  id: 'boas-vindas', autor: 'bot',
  texto: 'Olá! Sou o assistente de triagem cardiológica do CardioIA. Conte como você está se sentindo e eu ajudo a orientar o próximo passo.',
};

export default function ChatScreen() {
  const p = useTheme();
  const { api, ultimaAnalise } = useAjustes();
  const params = useLocalSearchParams<{ modo?: string }>();
  const [modo, setModo] = useState<Modo>('triagem');
  const [mensagens, setMensagens] = useState<Msg[]>([BOAS_VINDAS]);
  const [opcoes, setOpcoes] = useState<string[]>(SUGESTOES_INICIAIS);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const conversa = useRef(novoId());
  const lista = useRef<ComponentRef<typeof ScrollView>>(null);
  const analiseLlm = ultimaAnalise?.modo === 'llm' ? ultimaAnalise : null;

  function trocarModo(m: Modo) {
    setModo(m);
    setErro(null);
    if (m === 'analise' && analiseLlm) {
      setMensagens([{ id: novoId(), autor: 'bot', motor: 'multiagente',
        texto: `Análise ${analiseLlm.paciente_id}: risco ${Math.round(analiseLlm.recomendacao.probabilidade_pico_risco * 100)}% (${analiseLlm.recomendacao.classificacao_risco}). Pergunte o que quiser sobre ela.` }]);
      setOpcoes(SUGESTOES_ANALISE);
    } else {
      reiniciar();
    }
  }

  async function reiniciar() {
    api.resetChat(conversa.current).catch(() => undefined);
    conversa.current = novoId();
    setMensagens([BOAS_VINDAS]);
    setOpcoes(SUGESTOES_INICIAIS);
    setErro(null);
  }

  // Vindo do botão "Perguntar sobre esta análise", abre direto no modo multiagente.
  useFocusEffect(
    useCallback(() => {
      if (params.modo === 'analise' && analiseLlm) trocarModo('analise');
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [params.modo, analiseLlm?.analise_id]),
  );

  async function enviar(conteudo = texto) {
    const msg = conteudo.trim();
    if (!msg || enviando) return;
    setTexto('');
    setErro(null);
    setMensagens((m) => [...m, { id: novoId(), autor: 'usuario', texto: msg }]);
    setEnviando(true);
    try {
      const r = await api.chat(msg, conversa.current, modo === 'analise' ? analiseLlm?.analise_id : undefined);
      setMensagens((m) => [...m, {
        id: novoId(), autor: 'bot', texto: r.reply, resumo: r.summary, motor: r.engine,
        emergencia: r.stage === 'emergencia' || r.summary?.classificacao === 'EMERGENCIA',
      }]);
      setOpcoes(modo === 'analise' ? SUGESTOES_ANALISE : r.options ?? []);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
      setTimeout(() => lista.current?.scrollToEnd({ animated: true }), 80);
    }
  }

  return (
    <Tela titulo="Assistente" subtitulo={modo === 'triagem' ? 'Triagem por linguagem natural' : 'Orquestrador do sistema multiagente'}
      rolar={false}
      acao={<Botao titulo="" icone="refresh" variante="fantasma" onPress={() => trocarModo(modo)} style={{ width: 48, paddingHorizontal: 0 }} />}>
      <View style={[st.segmento, { backgroundColor: p.surfaceAlt }]}>
        {(['triagem', 'analise'] as Modo[]).map((m) => {
          const ativo = modo === m;
          const bloqueado = m === 'analise' && !analiseLlm;
          return (
            <Pressable key={m} disabled={bloqueado} onPress={() => trocarModo(m)} accessibilityRole="tab" accessibilityState={{ selected: ativo, disabled: bloqueado }}
              style={[st.segmentoItem, ativo && { backgroundColor: p.surface }, bloqueado && { opacity: 0.45 }]}>
              <T v="pequeno" cor={ativo ? 'primary' : 'textSecondary'} style={{ fontWeight: '700' }}>
                {m === 'triagem' ? 'Triagem' : 'Minha análise'}
              </T>
            </Pressable>
          );
        })}
      </View>
      {!analiseLlm && modo === 'triagem' ? (
        <T v="pequeno" cor="textSecondary" style={{ marginTop: -Spacing.two }}>
          “Minha análise” fica disponível após uma análise com LLM na aba Análise IA.
        </T>
      ) : null}

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <ScrollView ref={lista} style={{ flex: 1 }} contentContainerStyle={{ gap: Spacing.three, paddingVertical: Spacing.two }}
          onContentSizeChange={() => lista.current?.scrollToEnd({ animated: true })} keyboardShouldPersistTaps="handled">
          {mensagens.map((m) => <Balao key={m.id} m={m} />)}
          {enviando ? <View style={[st.balao, st.bot, { backgroundColor: p.surface, borderColor: p.border }]}><T v="pequeno" cor="textSecondary">digitando…</T></View> : null}
          {erro ? <Aviso texto={erro} /> : null}
        </ScrollView>

        {opcoes.length ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }}
            contentContainerStyle={{ gap: Spacing.two, paddingVertical: Spacing.two }} keyboardShouldPersistTaps="handled">
            {opcoes.map((o) => <Chip key={o} texto={o} onPress={() => enviar(o)} />)}
          </ScrollView>
        ) : null}

        <View style={[st.entrada, { backgroundColor: p.surface, borderColor: p.border }]}>
          <TextInput value={texto} onChangeText={setTexto} placeholder="Descreva o que está sentindo…" placeholderTextColor={p.textSecondary}
            style={[st.input, { color: p.text }]} onSubmitEditing={() => enviar()} returnKeyType="send" accessibilityLabel="Mensagem" multiline={false} />
          <Pressable onPress={() => enviar()} disabled={!texto.trim() || enviando} accessibilityRole="button" accessibilityLabel="Enviar"
            style={[st.enviar, { backgroundColor: texto.trim() ? p.primary : p.surfaceAlt }]}>
            <Icone nome="send" cor={texto.trim() ? p.onPrimary : p.textSecondary} />
          </Pressable>
        </View>
        <T v="pequeno" cor="textSecondary" style={{ textAlign: 'center', fontSize: 11, paddingVertical: Spacing.two }}>
          Apoio educacional · não substitui avaliação médica · emergência: 192
        </T>
      </KeyboardAvoidingView>
    </Tela>
  );
}

function Balao({ m }: { m: Msg }) {
  const p = useTheme();
  const usuario = m.autor === 'usuario';
  return (
    <View style={{ gap: Spacing.two, alignItems: usuario ? 'flex-end' : 'flex-start' }}>
      <View style={[st.balao, usuario ? [st.usuario, { backgroundColor: p.primary }] : [st.bot, { backgroundColor: p.surface, borderColor: p.border }]]}>
        <T v="pequeno" cor={usuario ? p.onPrimary : 'text'} style={{ fontSize: 15, lineHeight: 21 }}>{m.texto}</T>
        {m.motor && !usuario ? <T v="pequeno" cor="textSecondary" style={{ fontSize: 11, marginTop: 4 }}>motor: {m.motor}</T> : null}
      </View>
      {m.emergencia ? (
        <Botao titulo="Ligar 192 (SAMU)" icone="call" variante="perigo" onPress={() => Linking.openURL('tel:192')} style={{ alignSelf: 'stretch' }} />
      ) : null}
      {m.resumo?.classificacao ? <Resumo r={m.resumo} /> : null}
    </View>
  );
}

function Resumo({ r }: { r: ResumoChat }) {
  const p = useTheme();
  const cor = corClassificacao(p, r.classificacao);
  return (
    <Cartao style={{ alignSelf: 'stretch', gap: Spacing.two }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.two }}>
        <Icone nome="clipboard-outline" cor={p.primary} />
        <T v="rotulo" cor="textSecondary" style={{ flex: 1 }}>Resumo da triagem</T>
        <Selo texto={(r.classificacao ?? '').replace(/_/g, ' ')} fg={cor.fg} bg={cor.bg} />
      </View>
      {r.conduta_sugerida ? <T v="pequeno" style={{ fontWeight: '600' }}>{r.conduta_sugerida}</T> : null}
      {r.sintomas?.length ? <T v="pequeno" cor="textSecondary">Sintomas: {r.sintomas.join(', ')}</T> : null}
      {r.sinais_de_alarme?.length ? <T v="pequeno" cor="danger">Sinais de alarme: {r.sinais_de_alarme.join('; ')}</T> : null}
    </Cartao>
  );
}

const st = StyleSheet.create({
  segmento: { flexDirection: 'row', padding: 4, borderRadius: Radius.md },
  segmentoItem: { flex: 1, alignItems: 'center', paddingVertical: 8, borderRadius: Radius.sm },
  balao: { maxWidth: '86%', paddingHorizontal: Spacing.three, paddingVertical: Spacing.two + 2, borderRadius: Radius.lg },
  usuario: { borderBottomRightRadius: 4 },
  bot: { borderWidth: StyleSheet.hairlineWidth, borderBottomLeftRadius: 4 },
  entrada: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: Radius.pill, paddingLeft: Spacing.four, paddingRight: 4, minHeight: 50 },
  input: { flex: 1, fontSize: 16, paddingVertical: Spacing.two },
  enviar: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' },
});
