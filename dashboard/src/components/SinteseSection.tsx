import { Card } from "@wri-brasil/design-system";
import type { ReportCard } from "../types";

// Classes/cores da classificação de prioridade — espelham MAPAS["prioridade"]
// em dashboard/data_prep/build_web_assets.py. O RampLegend do design system
// não serve aqui: é hardcoded para a rampa de 5 classes verde→vermelho do
// índice nacional (iicRamp), e esta classificação é outra (4 classes,
// amarelo→vermelho) — ver decisão registrada no plano de migração.
const CLASSES: { label: string; cor: string }[] = [
  { label: "baixa", cor: "#ffffb2" },
  { label: "média", cor: "#fecc5c" },
  { label: "alta", cor: "#fd8d3c" },
  { label: "muito alta", cor: "#e31a1c" },
];

interface SinteseSectionProps {
  card: ReportCard;
}

export default function SinteseSection({ card }: SinteseSectionProps) {
  return (
    <section id="mapa-sintese" className="py-6">
      <h2 className="text-xl font-semibold text-wri-ink">{card.titulo}</h2>
      <p className="mt-1 max-w-2xl text-sm text-wri-muted">{card.descricao}</p>
      <Card className="mt-4 overflow-hidden p-0">
        <img
          src={`${import.meta.env.BASE_URL}data/${card.img}`}
          alt={card.titulo}
          className="w-full max-w-2xl mx-auto"
        />
        <div className="flex flex-wrap items-center gap-4 border-t border-wri-line p-4">
          {CLASSES.map((c) => (
            <span key={c.label} className="flex items-center gap-2 text-sm text-wri-ink">
              <span
                className="inline-block h-3 w-3 rounded-sm"
                style={{ backgroundColor: c.cor }}
                aria-hidden
              />
              {c.label}
            </span>
          ))}
        </div>
      </Card>
    </section>
  );
}
