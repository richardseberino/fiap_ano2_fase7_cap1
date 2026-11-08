/** Componentes visuais compartilhados do CardioIA (mobile-first, claro/escuro). */
import Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type TextProps,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Fonts, MaxContentWidth, Radius, Spacing, type ThemeColor } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export type IconName = ComponentProps<typeof Ionicons>['name'];

// ---------- tipografia ----------

type Variante = 'titulo' | 'subtitulo' | 'corpo' | 'rotulo' | 'pequeno' | 'numero' | 'mono';

export function T({
  v = 'corpo',
  cor,
  style,
  ...rest
}: TextProps & { v?: Variante; cor?: ThemeColor | string }) {
  const p = useTheme();
  const color = cor ? ((p as Record<string, string>)[cor] ?? cor) : p.text;
  return <Text style={[{ color, fontFamily: v === 'mono' ? Fonts.mono : Fonts.sans }, tipo[v], style]} {...rest} />;
}

const tipo = StyleSheet.create({
  titulo: { fontSize: 26, lineHeight: 32, fontWeight: '700', letterSpacing: -0.4 },
  subtitulo: { fontSize: 17, lineHeight: 24, fontWeight: '600' },
  corpo: { fontSize: 15, lineHeight: 22 },
  rotulo: { fontSize: 12, lineHeight: 16, fontWeight: '600', letterSpacing: 0.6, textTransform: 'uppercase' },
  pequeno: { fontSize: 13, lineHeight: 18 },
  numero: { fontSize: 30, lineHeight: 34, fontWeight: '700', fontVariant: ['tabular-nums'], letterSpacing: -0.5 },
  mono: { fontSize: 12, lineHeight: 18 },
});

// ---------- estrutura ----------

export function Tela({
  titulo,
  subtitulo,
  acao,
  children,
  rolar = true,
}: {
  titulo: string;
  subtitulo?: string;
  acao?: ReactNode;
  children: ReactNode;
  rolar?: boolean;
}) {
  const p = useTheme();
  const cabecalho = (
    <View style={s.cabecalho}>
      <View style={{ flex: 1 }}>
        <T v="titulo">{titulo}</T>
        {subtitulo ? (
          <T v="pequeno" cor="textSecondary" style={{ marginTop: 2 }}>
            {subtitulo}
          </T>
        ) : null}
      </View>
      {acao}
    </View>
  );
  return (
    <SafeAreaView edges={['top']} style={[s.raiz, { backgroundColor: p.background }]}>
      {rolar ? (
        <ScrollView contentContainerStyle={s.conteudo} keyboardShouldPersistTaps="handled">
          {cabecalho}
          {children}
        </ScrollView>
      ) : (
        <View style={[s.conteudo, { flex: 1, paddingBottom: 0 }]}>
          {cabecalho}
          {children}
        </View>
      )}
    </SafeAreaView>
  );
}

export function Cartao({ children, style, tom }: { children: ReactNode; style?: StyleProp<ViewStyle>; tom?: string }) {
  const p = useTheme();
  return (
    <View style={[s.cartao, { backgroundColor: tom ?? p.surface, borderColor: p.border }, style]}>{children}</View>
  );
}

export function Secao({ titulo, children, direita }: { titulo: string; children: ReactNode; direita?: ReactNode }) {
  return (
    <View style={{ gap: Spacing.two }}>
      <View style={s.linha}>
        <T v="rotulo" cor="textSecondary" style={{ flex: 1 }}>
          {titulo}
        </T>
        {direita}
      </View>
      {children}
    </View>
  );
}

// ---------- controles ----------

export function Botao({
  titulo,
  onPress,
  icone,
  variante = 'primario',
  carregando,
  desabilitado,
  style,
}: {
  titulo: string;
  onPress: () => void;
  icone?: IconName;
  variante?: 'primario' | 'secundario' | 'fantasma' | 'perigo';
  carregando?: boolean;
  desabilitado?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const p = useTheme();
  const cores = {
    primario: { bg: p.primary, fg: p.onPrimary, borda: p.primary },
    secundario: { bg: p.primarySoft, fg: p.primary, borda: p.primarySoft },
    fantasma: { bg: 'transparent', fg: p.primary, borda: p.border },
    perigo: { bg: p.danger, fg: '#fff', borda: p.danger },
  }[variante];
  const inativo = desabilitado || carregando;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inativo, busy: !!carregando }}
      onPress={onPress}
      disabled={inativo}
      style={({ pressed }) => [
        s.botao,
        { backgroundColor: cores.bg, borderColor: cores.borda, opacity: inativo ? 0.55 : pressed ? 0.85 : 1 },
        style,
      ]}>
      {carregando ? (
        <ActivityIndicator color={cores.fg} />
      ) : icone ? (
        <Ionicons name={icone} size={18} color={cores.fg} />
      ) : null}
      <Text style={[s.botaoTexto, { color: cores.fg }]}>{titulo}</Text>
    </Pressable>
  );
}

export function Chip({
  texto,
  ativo,
  onPress,
  corPonto,
}: {
  texto: string;
  ativo?: boolean;
  onPress?: () => void;
  corPonto?: string;
}) {
  const p = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: !!ativo }}
      style={({ pressed }) => [
        s.chip,
        {
          backgroundColor: ativo ? p.primary : p.surface,
          borderColor: ativo ? p.primary : p.border,
          opacity: pressed ? 0.8 : 1,
        },
      ]}>
      {corPonto ? <View style={[s.ponto, { backgroundColor: corPonto }]} /> : null}
      <Text style={{ color: ativo ? p.onPrimary : p.text, fontSize: 14, fontWeight: '600' }}>{texto}</Text>
    </Pressable>
  );
}

export function Selo({ texto, fg, bg, icone }: { texto: string; fg: string; bg: string; icone?: IconName }) {
  return (
    <View style={[s.selo, { backgroundColor: bg }]}>
      {icone ? <Ionicons name={icone} size={13} color={fg} /> : null}
      <Text style={{ color: fg, fontSize: 12, fontWeight: '700', letterSpacing: 0.3 }}>{texto}</Text>
    </View>
  );
}

export function Campo({
  rotulo,
  unidade,
  dica,
  erro,
  style,
  ...rest
}: TextInputProps & { rotulo: string; unidade?: string; dica?: string; erro?: string | null }) {
  const p = useTheme();
  return (
    <View style={[{ gap: 4 }, style as StyleProp<ViewStyle>]}>
      <T v="pequeno" cor="textSecondary" style={{ fontWeight: '600' }}>
        {rotulo}
      </T>
      <View style={[s.campo, { backgroundColor: p.surface, borderColor: erro ? p.danger : p.border }]}>
        <TextInput
          placeholderTextColor={p.textSecondary}
          style={[s.campoInput, { color: p.text }]}
          accessibilityLabel={rotulo}
          {...rest}
        />
        {unidade ? (
          <T v="pequeno" cor="textSecondary">
            {unidade}
          </T>
        ) : null}
      </View>
      {erro ? (
        <T v="pequeno" cor="danger">
          {erro}
        </T>
      ) : dica ? (
        <T v="pequeno" cor="textSecondary" style={{ fontSize: 12 }}>
          {dica}
        </T>
      ) : null}
    </View>
  );
}

export function Aviso({
  texto,
  tipo = 'erro',
  acao,
}: {
  texto: string;
  tipo?: 'erro' | 'info' | 'alerta' | 'sucesso';
  acao?: ReactNode;
}) {
  const p = useTheme();
  const m = {
    erro: { fg: p.danger, bg: p.dangerSoft, i: 'alert-circle' as IconName },
    alerta: { fg: p.warning, bg: p.warningSoft, i: 'warning' as IconName },
    info: { fg: p.info, bg: p.infoSoft, i: 'information-circle' as IconName },
    sucesso: { fg: p.success, bg: p.successSoft, i: 'checkmark-circle' as IconName },
  }[tipo];
  return (
    <View style={[s.aviso, { backgroundColor: m.bg }]}>
      <Ionicons name={m.i} size={20} color={m.fg} />
      <View style={{ flex: 1, gap: Spacing.two }}>
        <Text style={{ color: m.fg, fontSize: 14, lineHeight: 20 }}>{texto}</Text>
        {acao}
      </View>
    </View>
  );
}

export function Vazio({ icone, titulo, texto, children }: { icone: IconName; titulo: string; texto?: string; children?: ReactNode }) {
  const p = useTheme();
  return (
    <View style={s.vazio}>
      <View style={[s.vazioIcone, { backgroundColor: p.primarySoft }]}>
        <Ionicons name={icone} size={28} color={p.primary} />
      </View>
      <T v="subtitulo" style={{ textAlign: 'center' }}>
        {titulo}
      </T>
      {texto ? (
        <T v="pequeno" cor="textSecondary" style={{ textAlign: 'center', maxWidth: 320 }}>
          {texto}
        </T>
      ) : null}
      {children}
    </View>
  );
}

export function Barra({ valor, cor, altura = 8 }: { valor: number; cor: string; altura?: number }) {
  const p = useTheme();
  const pct = Math.max(0, Math.min(1, valor)) * 100;
  return (
    <View style={{ height: altura, borderRadius: altura, backgroundColor: p.surfaceAlt, overflow: 'hidden' }}>
      <View style={{ width: `${pct}%`, height: '100%', backgroundColor: cor, borderRadius: altura }} />
    </View>
  );
}

export function Icone({ nome, cor, tamanho = 18 }: { nome: IconName; cor?: string; tamanho?: number }) {
  const p = useTheme();
  return <Ionicons name={nome} size={tamanho} color={cor ?? p.textSecondary} />;
}

export const s = StyleSheet.create({
  raiz: { flex: 1 },
  conteudo: {
    width: '100%',
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.three,
    paddingBottom: Spacing.six * 2,
    gap: Spacing.four,
  },
  cabecalho: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three, marginBottom: Spacing.one },
  cartao: { borderRadius: Radius.lg, borderWidth: StyleSheet.hairlineWidth, padding: Spacing.four, gap: Spacing.three },
  linha: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  botao: {
    minHeight: 48,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.four,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
  },
  botaoTexto: { fontSize: 15, fontWeight: '700' },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    minHeight: 36,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.pill,
    borderWidth: 1,
  },
  ponto: { width: 8, height: 8, borderRadius: 4 },
  selo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.two,
    paddingVertical: 3,
    borderRadius: Radius.pill,
  },
  campo: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.three,
    minHeight: 46,
    gap: Spacing.two,
  },
  campoInput: { flex: 1, fontSize: 16, paddingVertical: Spacing.two },
  aviso: { flexDirection: 'row', gap: Spacing.three, padding: Spacing.three, borderRadius: Radius.md, alignItems: 'flex-start' },
  vazio: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.six },
  vazioIcone: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
});
