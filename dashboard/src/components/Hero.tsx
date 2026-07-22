interface HeroProps {
  titulo: string;
  data: string;
}

export default function Hero({ titulo, data }: HeroProps) {
  return (
    <header className="border-b border-wri-line py-8">
      <p className="text-sm font-semibold uppercase tracking-wide text-wri-muted">
        Diagnóstico territorial urbanístico
      </p>
      <h1 className="mt-1 text-3xl font-semibold text-wri-ink">{titulo}</h1>
      <p className="mt-1 text-sm text-wri-muted">Gerado em {data}</p>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-wri-muted">
        Este diagnóstico identifica, dentro da área analisada, onde intervenções de
        adaptação climática — como arborização, despavimentação e infraestrutura verde —
        têm maior impacto. Indicadores de calor, déficit de vegetação, impermeabilização do
        solo e vulnerabilidade socioeconômica são cruzados numa malha de hexágonos de alta
        resolução, resultando num mapa-síntese de prioridade para orientar decisões locais.
      </p>
    </header>
  );
}
