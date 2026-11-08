/** Configurações do app (URL do gateway, paciente monitorado) e estado compartilhado entre telas. */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { API_URL_PADRAO, criarApi, type Api, type RespostaAnalise } from './api';

const CHAVE = 'cardioia.ajustes.v1';

type Ajustes = { apiUrl: string; pacienteId: string | null };

type Contexto = Ajustes & {
  api: Api;
  carregado: boolean;
  definirApiUrl: (url: string) => void;
  definirPaciente: (id: string | null) => void;
  ultimaAnalise: RespostaAnalise | null;
  definirUltimaAnalise: (a: RespostaAnalise | null) => void;
};

const Ctx = createContext<Contexto | null>(null);

export function normalizarUrl(url: string) {
  const limpa = url.trim().replace(/\/+$/, '');
  if (!limpa) return API_URL_PADRAO;
  return /^https?:\/\//i.test(limpa) ? limpa : `https://${limpa}`;
}

export function AjustesProvider({ children }: { children: ReactNode }) {
  const [ajustes, setAjustes] = useState<Ajustes>({ apiUrl: API_URL_PADRAO, pacienteId: null });
  const [carregado, setCarregado] = useState(false);
  const [ultimaAnalise, definirUltimaAnalise] = useState<RespostaAnalise | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(CHAVE)
      .then((bruto) => {
        if (bruto) setAjustes((a) => ({ ...a, ...JSON.parse(bruto) }));
      })
      .catch(() => undefined)
      .finally(() => setCarregado(true));
  }, []);

  useEffect(() => {
    if (carregado) AsyncStorage.setItem(CHAVE, JSON.stringify(ajustes)).catch(() => undefined);
  }, [ajustes, carregado]);

  const valor = useMemo<Contexto>(
    () => ({
      ...ajustes,
      api: criarApi(ajustes.apiUrl),
      carregado,
      definirApiUrl: (url) => setAjustes((a) => ({ ...a, apiUrl: normalizarUrl(url) })),
      definirPaciente: (id) => setAjustes((a) => ({ ...a, pacienteId: id })),
      ultimaAnalise,
      definirUltimaAnalise,
    }),
    [ajustes, carregado, ultimaAnalise],
  );

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useAjustes() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAjustes fora do AjustesProvider');
  return ctx;
}
