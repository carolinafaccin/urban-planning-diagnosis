import { KpiCard } from "@wri-brasil/design-system";
import type { Report } from "../types";

const ORDEM_PRIORIDADE = ["muito alta", "alta", "média", "baixa"];

interface StatsBarProps {
  report: Report;
}

export default function StatsBar({ report }: StatsBarProps) {
  return (
    <section className="grid grid-cols-2 gap-3 py-6 sm:grid-cols-3 lg:grid-cols-6">
      <KpiCard label="Hexágonos (H3)" value={report.n_hex} />
      {report.n_pop != null && <KpiCard label="Com população" value={report.n_pop} />}
      {ORDEM_PRIORIDADE.filter((classe) => report.dist[classe] != null).map((classe) => (
        <KpiCard
          key={classe}
          label={`Prioridade ${classe}`}
          value={report.dist[classe]}
          accent={classe === "muito alta"}
        />
      ))}
    </section>
  );
}
