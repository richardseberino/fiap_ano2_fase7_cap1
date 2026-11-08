/** Tela 4 · Envio de imagem de eletrocardiograma para o modelo de visão computacional (CNN). */
import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import { Image, Platform, StyleSheet, View } from 'react-native';

import { Aviso, Barra, Botao, Cartao, Icone, Secao, Selo, T, Tela, Vazio } from '@/components/ui';
import { corClassificacao, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { RespostaEcg } from '@/lib/api';
import { useAjustes } from '@/lib/settings';

type Imagem = { uri: string; nome: string; tipo: string; file?: File | null; largura: number; altura: number };
type Historico = { id: string; uri: string; resultado: RespostaEcg; horario: Date };

export default function EcgScreen() {
  const p = useTheme();
  const { api } = useAjustes();
  const [imagem, setImagem] = useState<Imagem | null>(null);
  const [resultado, setResultado] = useState<RespostaEcg | null>(null);
  const [historico, setHistorico] = useState<Historico[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function escolher(origem: 'galeria' | 'camera') {
    setErro(null);
    if (origem === 'camera') {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) { setErro('Permissão da câmera negada.'); return; }
    }
    const opcoes: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.9, allowsEditing: false };
    const r = origem === 'camera' ? await ImagePicker.launchCameraAsync(opcoes) : await ImagePicker.launchImageLibraryAsync(opcoes);
    if (r.canceled || !r.assets?.length) return;
    const a = r.assets[0];
    const tipo = a.mimeType ?? 'image/jpeg';
    const ext = tipo.split('/')[1]?.replace('jpeg', 'jpg') ?? 'jpg';
    setImagem({ uri: a.uri, nome: a.fileName ?? `ecg.${ext}`, tipo, file: a.file ?? null, largura: a.width, altura: a.height });
    setResultado(null);
  }

  async function analisar() {
    if (!imagem) return;
    setEnviando(true); setErro(null);
    try {
      const r = await api.ecg(imagem);
      setResultado(r);
      setHistorico((h) => [{ id: String(Date.now()), uri: imagem.uri, resultado: r, horario: new Date() }, ...h].slice(0, 5));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  const cor = resultado ? corClassificacao(p, resultado.severidade) : null;

  return (
    <Tela titulo="Exame de ECG" subtitulo="Classificação por rede neural convolucional (4 classes)">
      {imagem ? (
        <Cartao style={{ padding: Spacing.two }}>
          <Image source={{ uri: imagem.uri }} accessibilityLabel="Imagem do ECG selecionada"
            style={[st.preview, { aspectRatio: imagem.largura && imagem.altura ? imagem.largura / imagem.altura : 1.4 }]} resizeMode="contain" />
          <T v="pequeno" cor="textSecondary" numberOfLines={1} style={{ paddingHorizontal: Spacing.two }}>{imagem.nome}</T>
        </Cartao>
      ) : (
        <Cartao>
          <Vazio icone="document-attach-outline" titulo="Envie a imagem do eletrocardiograma"
            texto="Foto ou arquivo do traçado de 12 derivações. O modelo identifica: normal, batimentos anormais, infarto do miocárdio ou histórico de infarto." />
        </Cartao>
      )}

      <View style={st.botoes}>
        <Botao titulo="Galeria" icone="images-outline" variante="secundario" onPress={() => escolher('galeria')} style={{ flex: 1 }} />
        {Platform.OS !== 'web' ? (
          <Botao titulo="Câmera" icone="camera-outline" variante="secundario" onPress={() => escolher('camera')} style={{ flex: 1 }} />
        ) : null}
      </View>

      {imagem ? <Botao titulo="Analisar exame" icone="scan" carregando={enviando} onPress={analisar} /> : null}
      {erro ? <Aviso texto={erro} /> : null}

      {resultado && cor ? (
        <View style={{ gap: Spacing.four }}>
          <Cartao tom={cor.bg} style={{ borderColor: cor.bg }}>
            <View style={st.linha}>
              <T v="rotulo" cor="textSecondary" style={{ flex: 1 }}>Resultado do modelo</T>
              <Selo texto={resultado.severidade} fg={cor.fg} bg={p.surface} />
            </View>
            <T v="titulo" cor={cor.fg}>{resultado.rotulo}</T>
            <T v="pequeno">{resultado.descricao}</T>
            <T v="pequeno" cor="textSecondary">Confiança {(resultado.confianca * 100).toFixed(1)}% · {resultado.duracao_ms} ms</T>
          </Cartao>

          <Secao titulo="Probabilidade por classe">
            <Cartao>
              {resultado.probabilidades.map((c) => (
                <View key={c.classe} style={{ gap: 6 }}>
                  <View style={st.linha}>
                    <T v="pequeno" style={{ flex: 1 }}>{c.rotulo}</T>
                    <T v="pequeno" style={{ fontWeight: '700', fontVariant: ['tabular-nums'] }}>{(c.probabilidade * 100).toFixed(1)}%</T>
                  </View>
                  <Barra valor={c.probabilidade} cor={c.cor} />
                </View>
              ))}
            </Cartao>
          </Secao>
          <Aviso tipo="info" texto={resultado.aviso} />
        </View>
      ) : null}

      {historico.length > 1 ? (
        <Secao titulo="Exames desta sessão">
          {historico.slice(1).map((h) => {
            const c = corClassificacao(p, h.resultado.severidade);
            return (
              <Cartao key={h.id} style={[st.linha, { padding: Spacing.two }]}>
                <Image source={{ uri: h.uri }} style={st.miniatura} />
                <View style={{ flex: 1 }}>
                  <T v="pequeno" style={{ fontWeight: '600' }}>{h.resultado.rotulo}</T>
                  <T v="pequeno" cor="textSecondary">{h.horario.toLocaleTimeString('pt-BR')}</T>
                </View>
                <Icone nome="ellipse" cor={c.fg} tamanho={12} />
              </Cartao>
            );
          })}
        </Secao>
      ) : null}
    </Tela>
  );
}

const st = StyleSheet.create({
  preview: { width: '100%', borderRadius: Radius.md, backgroundColor: '#fff' },
  botoes: { flexDirection: 'row', gap: Spacing.three },
  linha: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  miniatura: { width: 52, height: 40, borderRadius: 6, backgroundColor: '#fff' },
});
