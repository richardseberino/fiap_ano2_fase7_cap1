/** Cliente HTTP do CardioIA Gateway (único backend consumido pelo app). */
import { Platform } from 'react-native';

export const API_URL_PADRAO = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8080').replace(/\/+$/, '');

// ---------- tipos (espelham os esquemas do gateway/serviços) ----------

export type Leitura = {
  paciente_id: string;
  horario: string | null;
  bpm?: number;
  oxigenacao?: number;
  temperatura?: number;
  pa_sistolica?: number;
  nivel_alerta?: number;
  panico?: number;
  setor?: string;
  dispositivo?: string;
  origem?: string;
};

export type PontoSerie = Omit<Leitura, 'paciente_id' | 'setor' | 'dispositivo' | 'origem'> & { horario: string };

export type SinaisPaciente = { paciente_id: string; minutos: number; ultimo: Leitura | null; serie: PontoSerie[] };

export type DadosPaciente = {
  idade_media: number;
  carga_sistema: number;
  tempo_espera: number;
  fc_media: number;
  spo2_media: number;
  pa_sistolica: number;
  temperatura: number;
  densidade_eventos: number;
  eventos_24h: number;
  disponibilidade_recursos: number;
};

export type Sugestao = {
  paciente_id: string;
  janela_minutos: number;
  amostras: number;
  dados: { [K in keyof DadosPaciente]: number | null };
};

export type AcaoOperacional = { prioridade: number; acao: string; responsavel: string; prazo: string; protocolo_origem: string };

export type Recomendacao = {
  paciente_id: string;
  probabilidade_pico_risco: number;
  classificacao_risco: 'BAIXO' | 'MODERADO' | 'ALTO';
  fatores_de_risco: string[];
  protocolos_sugeridos: string[];
  acoes_operacionais: AcaoOperacional[];
  parametros_em_atencao: string[];
  justificativa: string;
  aviso: string;
};

export type RespostaAnalise = {
  analise_id: string;
  paciente_id: string;
  modo: 'llm' | 'offline';
  recomendacao: Recomendacao;
  trilha: string[];
  guardrail_bloqueou: boolean;
  problemas: string[];
  observacao?: string | null;
  duracao_ms: number;
};

export type ResumoChat = {
  classificacao?: string;
  conduta_sugerida?: string;
  sintomas?: string[];
  sinais_de_alarme?: string[];
  [k: string]: unknown;
};

export type RespostaChat = {
  reply: string;
  conversation_id?: string | null;
  options?: string[];
  summary?: ResumoChat | null;
  stage?: string;
  engine?: string;
  intent?: string;
};

export type RespostaEcg = {
  classe: string;
  rotulo: string;
  confianca: number;
  severidade: 'BAIXO' | 'MODERADO' | 'ALTO' | 'CRITICO';
  descricao: string;
  probabilidades: { classe: string; rotulo: string; probabilidade: number; cor: string }[];
  duracao_ms: number;
  aviso: string;
};

export type Saude = {
  status: 'ok' | 'degradado';
  horario: string;
  servicos: { servico: string; ok: boolean; erro?: string; detalhes?: Record<string, unknown> }[];
};

// ---------- cliente ----------

export class ErroApi extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function requisitar<T>(base: string, caminho: string, init: RequestInit = {}, timeoutMs = 30000): Promise<T> {
  const controle = new AbortController();
  const timer = setTimeout(() => controle.abort(), timeoutMs);
  try {
    const resp = await fetch(`${base}${caminho}`, { ...init, signal: controle.signal });
    const texto = await resp.text();
    const corpo = texto ? safeJson(texto) : null;
    if (!resp.ok) {
      const detalhe = corpo?.detail ?? corpo?.error ?? texto;
      throw new ErroApi(typeof detalhe === 'string' ? detalhe : JSON.stringify(detalhe), resp.status);
    }
    return corpo as T;
  } catch (e) {
    if (e instanceof ErroApi) throw e;
    if ((e as Error).name === 'AbortError') throw new ErroApi('Tempo esgotado ao contatar o servidor.');
    throw new ErroApi(`Não foi possível conectar ao gateway (${base}). Verifique a URL em Ajustes.`);
  } finally {
    clearTimeout(timer);
  }
}

function safeJson(texto: string) {
  try {
    return JSON.parse(texto);
  } catch {
    return null;
  }
}

const json = (corpo: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(corpo),
});

export function criarApi(base: string) {
  return {
    saude: () => requisitar<Saude>(base, '/api/health', {}, 8000),
    sinaisTodos: (horas = 24) => requisitar<Leitura[]>(base, `/api/sinais-vitais?horas=${horas}`),
    sinaisPaciente: (id: string, minutos = 30) =>
      requisitar<SinaisPaciente>(base, `/api/sinais-vitais/${encodeURIComponent(id)}?minutos=${minutos}`),
    sugestao: (id: string, minutos = 30) =>
      requisitar<Sugestao>(base, `/api/analise/sugestao/${encodeURIComponent(id)}?minutos=${minutos}`),
    exemplos: () => requisitar<{ paciente_id: string; dados: DadosPaciente }[]>(base, '/api/analise/exemplos'),
    analisar: (paciente_id: string | undefined, dados: DadosPaciente) =>
      requisitar<RespostaAnalise>(base, '/api/analise', json({ paciente_id, dados, modo: 'auto' }), 200000),
    chat: (message: string, conversation_id?: string, analise_id?: string) =>
      requisitar<RespostaChat>(base, '/api/chat', json({ message, conversation_id, analise_id }), 200000),
    resetChat: (conversation_id?: string) => requisitar(base, '/api/chat/reset', json({ conversation_id })),
    ecg: async (imagem: { uri: string; nome: string; tipo: string; file?: File | null }) => {
      const form = new FormData();
      if (Platform.OS === 'web') {
        // No navegador o picker entrega um File; sem ele, convertemos a URI (blob:/data:) em Blob.
        const blob = imagem.file ?? (await (await fetch(imagem.uri)).blob());
        form.append('image', blob, imagem.nome);
      } else {
        // No Android/iOS o FormData do React Native aceita { uri, name, type }.
        form.append('image', { uri: imagem.uri, name: imagem.nome, type: imagem.tipo } as unknown as Blob);
      }
      return requisitar<RespostaEcg>(base, '/api/ecg', { method: 'POST', body: form }, 120000);
    },
  };
}

export type Api = ReturnType<typeof criarApi>;
