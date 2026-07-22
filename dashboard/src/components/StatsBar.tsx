import { KpiCard } from "@wri-brasil/design-system";
import type { Report } from "../types";

interface StatsBarProps {
  report: Report;
}

// % de área (hexágonos têm área ~igual entre si, então % de contagem ≈ %
// de área) em prioridade alta ou muito alta — mais direto pra um gestor
// local do que a contagem bruta de hexágonos por classe de prioridade.
function pctPrioridade(report: Report, classes: string[]): number | null {
  if (!report.n_hex) return null;
  const soma = classes.reduce((acc, c) => acc + (report.dist[c] ?? 0), 0);
  return Math.round((100 * soma) / report.n_hex);
}

export default function StatsBar({ report }: StatsBarProps) {
  const pctAltaOuMais = pctPrioridade(report, ["muito alta", "alta"]);
  return (
    <section className="grid grid-cols-2 gap-3 py-6 sm:grid-cols-4">
      {report.area_km2 != null && (
        <KpiCard label="Área analisada" value={`${report.area_km2.toLocaleString("pt-BR")} km²`} />
      )}
      {report.pop_total != null && (
        <KpiCard label="População estimada" value={report.pop_total.toLocaleString("pt-BR")} />
      )}
      {pctAltaOuMais != null && (
        <KpiCard label="Área em prioridade alta ou muito alta" value={`${pctAltaOuMais}%`} accent />
      )}
      {report.dist["muito alta"] != null && (
        <KpiCard label="Hexágonos em prioridade muito alta" value={report.dist["muito alta"]} accent />
      )}
    </section>
  );
}
