/** Tela 5 · Configuração do gateway e diagnóstico da plataforma. */
import Constants from 'expo-constants';
import { useEffect, useState } from 'react';
import { Linking, View } from 'react-native';

import { Aviso, Botao, Campo, Cartao, Icone, Secao, Selo, T, Tela } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { API_URL_PADRAO, criarApi, type Saude } from '@/lib/api';
import { normalizarUrl, useAjustes } from '@/lib/settings';

const NOMES: Record<string, string> = {
  multiagente: 'Multiagente (OpenAI Agents + Random Forest)',
  chatbot: 'Chatbot de triagem (NLP / Watson)',
  vision: 'Visão computacional (CNN ECG)',
  influxdb: 'InfluxDB (sinais IoT)',
};

export default function AjustesScreen() {
  const p = useTheme();
  const { apiUrl, definirApiUrl } = useAjustes();
  const [rascunho, setUrl] = useState<string | null>(null);
  const url = rascunho ?? apiUrl;
  const [saude, setSaude] = useState<Saude | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [testando, setTestando] = useState(false);

  async function testar(alvo = url) {
    setTestando(true); setErro(null); setSaude(null);
    try {
      setSaude(await criarApi(normalizarUrl(alvo)).saude());
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setTestando(false);
    }
  }

  // Diagnóstico automático ao abrir a tela ou trocar a URL salva.
  useEffect(() => {
    let ativo = true;
    criarApi(apiUrl).saude()
      .then((r) => ativo && setSaude(r))
      .catch((e: Error) => ativo && setErro(e.message));
    return () => { ativo = false; };
  }, [apiUrl]);

  return (
    <Tela titulo="Ajustes" subtitulo="Conexão com a plataforma CardioIA">
      <Secao titulo="Gateway da API">
        <Cartao>
          <Campo rotulo="URL do gateway" value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false}
            keyboardType="url" placeholder="https://cardioia.exemplo.com" dica={`Padrão do build: ${API_URL_PADRAO}`} />
          <View style={{ flexDirection: 'row', gap: Spacing.three }}>
            <Botao titulo="Testar" icone="pulse" variante="fantasma" carregando={testando} onPress={() => testar()} style={{ flex: 1 }} />
            <Botao titulo="Salvar" icone="save-outline" onPress={() => { definirApiUrl(url); setUrl(null); }} style={{ flex: 1 }} />
          </View>
        </Cartao>
      </Secao>

      {erro ? <Aviso texto={erro} /> : null}

      {saude ? (
        <Secao titulo="Estado dos serviços" direita={<Selo texto={saude.status === 'ok' ? 'OPERACIONAL' : 'DEGRADADO'}
          fg={saude.status === 'ok' ? p.success : p.warning} bg={saude.status === 'ok' ? p.successSoft : p.warningSoft} />}>
          <Cartao style={{ gap: Spacing.three }}>
            {saude.servicos.map((s) => (
              <View key={s.servico} style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.three }}>
                <Icone nome={s.ok ? 'checkmark-circle' : 'close-circle'} cor={s.ok ? p.success : p.danger} tamanho={22} />
                <View style={{ flex: 1 }}>
                  <T v="pequeno" style={{ fontWeight: '600' }}>{NOMES[s.servico] ?? s.servico}</T>
                  <T v="pequeno" cor="textSecondary" numberOfLines={2}>
                    {s.ok ? detalhe(s.servico, s.detalhes) : s.erro ?? 'indisponível'}
                  </T>
                </View>
              </View>
            ))}
          </Cartao>
        </Secao>
      ) : null}

      <Secao titulo="Sobre">
        <Cartao style={{ gap: Spacing.two }}>
          <T style={{ fontWeight: '700' }}>CardioIA · Grupo DRELL (FIAP)</T>
          <T v="pequeno" cor="textSecondary">
            Plataforma integrada: IoT (MicroPython) → MQTT → InfluxDB, sistema multiagente, chatbot de triagem e visão computacional, servidos por um gateway único em Kubernetes.
          </T>
          <T v="pequeno" cor="textSecondary">Versão {Constants.expoConfig?.version ?? '—'}</T>
          <Botao titulo="Documentação da API" icone="code-slash" variante="fantasma" onPress={() => Linking.openURL(`${apiUrl}/api/docs`)} />
        </Cartao>
      </Secao>
      <T v="pequeno" cor="textSecondary" style={{ textAlign: 'center' }}>
        Projeto acadêmico com dados simulados. Não substitui avaliação médica.
      </T>
    </Tela>
  );
}

function detalhe(servico: string, d?: Record<string, unknown>) {
  if (!d) return 'ok';
  if (servico === 'multiagente') return d.llm_disponivel ? `LLM ${d.modelo_llm} + ${d.modelo_ml}` : `Modo offline · ${d.modelo_ml}`;
  if (servico === 'chatbot') return `Motor ${d.engine}`;
  if (servico === 'vision') return String(d.modelo ?? 'ok');
  return 'ok';
}
