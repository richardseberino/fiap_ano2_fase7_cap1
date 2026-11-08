import Ionicons from '@expo/vector-icons/Ionicons';
import { DarkTheme, DefaultTheme, Tabs, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Colors } from '@/constants/theme';
import { AjustesProvider } from '@/lib/settings';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

type Aba = { nome: string; titulo: string; icone: keyof typeof Ionicons.glyphMap; iconeAtivo: keyof typeof Ionicons.glyphMap };

const ABAS: Aba[] = [
  { nome: 'index', titulo: 'Sinais', icone: 'pulse-outline', iconeAtivo: 'pulse' },
  { nome: 'analise', titulo: 'Análise IA', icone: 'git-network-outline', iconeAtivo: 'git-network' },
  { nome: 'chat', titulo: 'Assistente', icone: 'chatbubbles-outline', iconeAtivo: 'chatbubbles' },
  { nome: 'ecg', titulo: 'ECG', icone: 'image-outline', iconeAtivo: 'image' },
  { nome: 'ajustes', titulo: 'Ajustes', icone: 'settings-outline', iconeAtivo: 'settings' },
];

export default function Layout() {
  const esquema = useColorScheme() === 'dark' ? 'dark' : 'light';
  const p = Colors[esquema];

  useEffect(() => {
    SplashScreen.hideAsync().catch(() => undefined);
  }, []);

  const base = esquema === 'dark' ? DarkTheme : DefaultTheme;
  const tema: typeof base = {
    ...base,
    colors: { ...base.colors, background: p.background, card: p.surface, primary: p.primary, border: p.border, text: p.text },
  };

  return (
    <SafeAreaProvider>
      <AjustesProvider>
        <ThemeProvider value={tema}>
          <Tabs
            screenOptions={{
              headerShown: false,
              tabBarActiveTintColor: p.primary,
              tabBarInactiveTintColor: p.textSecondary,
              tabBarStyle: { backgroundColor: p.surface, borderTopColor: p.border },
              tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
            }}>
            {ABAS.map((a) => (
              <Tabs.Screen
                key={a.nome}
                name={a.nome}
                options={{
                  title: a.titulo,
                  tabBarIcon: ({ color, focused, size }) => (
                    <Ionicons name={focused ? a.iconeAtivo : a.icone} size={size ?? 22} color={String(color)} />
                  ),
                }}
              />
            ))}
          </Tabs>
        </ThemeProvider>
      </AjustesProvider>
    </SafeAreaProvider>
  );
}
