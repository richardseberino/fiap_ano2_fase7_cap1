/** Mini-gráfico de linha (react-native-svg) com a faixa de referência do sinal vital. */
import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { useTheme } from '@/hooks/use-theme';

type Props = {
  valores: (number | null | undefined)[];
  cor: string;
  altura?: number;
  /** faixa considerada normal, desenhada ao fundo */
  faixa?: [number, number];
};

export function Sparkline({ valores, cor, altura = 44, faixa }: Props) {
  const p = useTheme();
  const [largura, setLargura] = useState(0);
  const pontos = valores.map((v, i) => [i, v] as const).filter((x): x is readonly [number, number] => x[1] != null);

  const onLayout = (e: LayoutChangeEvent) => setLargura(e.nativeEvent.layout.width);
  if (pontos.length < 2 || largura === 0) {
    return <View onLayout={onLayout} style={{ height: altura }} />;
  }

  const ys = pontos.map(([, v]) => v);
  let min = Math.min(...ys, ...(faixa ?? []));
  let max = Math.max(...ys, ...(faixa ?? []));
  if (max - min < 1e-6) {
    min -= 1;
    max += 1;
  }
  const pad = 4;
  const n = valores.length - 1 || 1;
  const x = (i: number) => (i / n) * (largura - pad * 2) + pad;
  const y = (v: number) => altura - pad - ((v - min) / (max - min)) * (altura - pad * 2);
  const d = pontos.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const [ui, uv] = pontos[pontos.length - 1];

  return (
    <View onLayout={onLayout} style={{ height: altura }}>
      <Svg width={largura} height={altura}>
        {faixa ? (
          <Rect x={0} width={largura} y={y(faixa[1])} height={Math.max(0, y(faixa[0]) - y(faixa[1]))} fill={p.surfaceAlt} />
        ) : null}
        <Path d={d} stroke={cor} strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
        <Circle cx={x(ui)} cy={y(uv)} r={3.5} fill={cor} />
      </Svg>
    </View>
  );
}
