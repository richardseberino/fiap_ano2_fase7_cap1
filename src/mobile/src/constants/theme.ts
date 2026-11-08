import '@/global.css';

import { Platform } from 'react-native';

/** Paleta clínica (azul-petróleo) com variantes claro/escuro. */
export const Colors = {
  light: {
    background: '#F3F6F7',
    surface: '#FFFFFF',
    surfaceAlt: '#EAF0F2',
    text: '#0E1A1F',
    textSecondary: '#5B6B73',
    border: '#DDE5E8',
    primary: '#0B7A84',
    primarySoft: '#DDF0F1',
    onPrimary: '#FFFFFF',
    success: '#23905A',
    successSoft: '#DDF3E6',
    warning: '#B57F00',
    warningSoft: '#FBF0D2',
    danger: '#C93B3B',
    dangerSoft: '#FBE1E1',
    info: '#2F6FD0',
    infoSoft: '#E1EBFA',
  },
  dark: {
    background: '#0A1114',
    surface: '#121C20',
    surfaceAlt: '#1A262B',
    text: '#E7EEF0',
    textSecondary: '#93A4AB',
    border: '#24333A',
    primary: '#3DB7C1',
    primarySoft: '#123238',
    onPrimary: '#06191C',
    success: '#4CC27F',
    successSoft: '#123222',
    warning: '#F0C04C',
    warningSoft: '#3A2F10',
    danger: '#F06B6B',
    dangerSoft: '#3D1717',
    info: '#7AA8F0',
    infoSoft: '#16263F',
  },
} as const;

export type Palette = { [K in keyof typeof Colors.light]: string };
export type ThemeColor = keyof Palette;

export const Fonts = Platform.select({
  web: { sans: 'var(--font-display)', mono: 'var(--font-mono)' },
  ios: { sans: 'system-ui', mono: 'ui-monospace' },
  default: { sans: 'normal', mono: 'monospace' },
});

export const Spacing = { half: 2, one: 4, two: 8, three: 12, four: 16, five: 24, six: 32 } as const;
export const Radius = { sm: 8, md: 12, lg: 16, pill: 999 } as const;

/** Largura máxima do conteúdo: no navegador o app mantém o formato de celular. */
export const MaxContentWidth = 560;

export type Nivel = 0 | 1 | 2;
export const NIVEL_TEXTO = ['Normal', 'Atenção', 'Crítico'] as const;

export function corNivel(p: Palette, nivel: number | null | undefined) {
  if (nivel == null) return { fg: p.textSecondary, bg: p.surfaceAlt };
  if (nivel >= 2) return { fg: p.danger, bg: p.dangerSoft };
  if (nivel >= 1) return { fg: p.warning, bg: p.warningSoft };
  return { fg: p.success, bg: p.successSoft };
}

export function corClassificacao(p: Palette, classe: string | undefined) {
  switch ((classe ?? '').toUpperCase()) {
    case 'ALTO':
    case 'CRITICO':
    case 'EMERGENCIA':
      return { fg: p.danger, bg: p.dangerSoft };
    case 'MODERADO':
    case 'PRIORIDADE ALTA':
      return { fg: p.warning, bg: p.warningSoft };
    case 'BAIXO':
      return { fg: p.success, bg: p.successSoft };
    default:
      return { fg: p.info, bg: p.infoSoft };
  }
}
