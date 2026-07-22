import { useEffect } from "react";
import { useReport } from "./data";
import { useRoute } from "./router";
import TopBar from "./components/TopBar";
import Hero from "./components/Hero";
import StatsBar from "./components/StatsBar";
import MapCard from "./components/MapCard";
import SinteseSection from "./components/SinteseSection";
import AnaliseArea from "./components/AnaliseArea";
import MethodologyNotes from "./components/MethodologyNotes";
import Footer from "./components/Footer";

// Rodapé fixo (ver Footer.tsx) — o espaço reservado aqui evita que o
// conteúdo fique escondido atrás dele. Generoso o bastante para o rodapé
// quebrar em até 2 linhas em telas estreitas.
const FOOTER_SPACER = "pb-28 sm:pb-16";

export default function App() {
  const { report, loading, error } = useReport();
  const [route] = useRoute();

  useEffect(() => {
    if (report) {
      document.title =
        route === "notas"
          ? `Notas metodológicas — ${report.cidade}`
          : `Diagnóstico territorial urbanístico — ${report.cidade}`;
    }
  }, [report, route]);

  if (loading) return <main className="p-8 text-wri-muted">Carregando…</main>;
  if (error || !report) {
    return (
      <main className="p-8 text-wri-muted">
        Não foi possível carregar os dados do diagnóstico ({error ?? "report.json vazio"}).
      </main>
    );
  }

  if (route === "notas") {
    return (
      <>
        <TopBar cidade={report.cidade} />
        <div className={`mx-auto max-w-3xl px-4 ${FOOTER_SPACER}`}>
          <a
            href="#/"
            className="mt-6 inline-block text-sm text-wri-muted underline underline-offset-2 hover:text-wri-ink"
          >
            ← Voltar ao diagnóstico
          </a>
          <MethodologyNotes />
        </div>
        <Footer />
      </>
    );
  }

  const sintese = report.cards.find((c) => c.id === "prioridade");
  const outrosMapas = report.cards.filter((c) => c.id !== "prioridade");

  return (
    <>
      <TopBar cidade={report.cidade} />
      <div className={`mx-auto max-w-5xl px-4 ${FOOTER_SPACER}`}>
        <Hero cidade={report.cidade} data={report.data} />
        <StatsBar report={report} />
        <AnaliseArea analiseMd={report.analise_md} />
        {sintese && <SinteseSection card={sintese} />}
        <section className="py-6">
          <h2 className="border-l-4 border-wri-yellow pl-3 text-xl font-semibold text-wri-ink">
            Mapas temáticos
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {outrosMapas.map((c) => (
              <MapCard key={c.id} {...c} />
            ))}
          </div>
        </section>
      </div>
      <Footer />
    </>
  );
}
