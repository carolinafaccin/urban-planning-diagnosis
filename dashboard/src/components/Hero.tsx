interface HeroProps {
  cidade: string;
  data: string;
}

export default function Hero({ cidade, data }: HeroProps) {
  return (
    <header className="border-b border-wri-line py-8">
      <p className="text-sm font-semibold uppercase tracking-wide text-wri-muted">
        Diagnóstico territorial urbanístico
      </p>
      <h1 className="mt-1 text-3xl font-semibold text-wri-ink">{cidade}</h1>
      <p className="mt-1 text-sm text-wri-muted">Gerado em {data}</p>
    </header>
  );
}
