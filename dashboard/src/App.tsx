import { useEffect } from "react";
import { useReport } from "./data";
import TopBar from "./components/TopBar";
import Hero from "./components/Hero";
import StatsBar from "./components/StatsBar";
import MapCard from "./components/MapCard";
import SinteseSection from "./components/SinteseSection";
import AnaliseArea from "./components/AnaliseArea";
import DownloadData from "./components/DownloadData";
import MethodologyNotes from "./components/MethodologyNotes";
import Footer from "./components/Footer";

export default function App() {
  const { report, loading, error } = useReport();

  useEffect(() => {
    if (report) document.title = `Diagnóstico territorial urbanístico — ${report.cidade}`;
  }, [report]);

  if (loading) return <main className="p-8 text-wri-muted">Carregando…</main>;
  if (error || !report) {
    return (
      <main className="p-8 text-wri-muted">
        Não foi possível carregar os dados do diagnóstico ({error ?? "report.json vazio"}).
      </main>
    );
  }

  const sintese = report.cards.find((c) => c.id === "prioridade");
  const outrosMapas = report.cards.filter((c) => c.id !== "prioridade");

  return (
    <>
      <TopBar cidade={report.cidade} />
      <div className="mx-auto max-w-5xl px-4">
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
        <DownloadData gpkgArquivo={report.gpkg_arquivo} gpkgTamanhoMb={report.gpkg_tamanho_mb} />
        <MethodologyNotes />
      </div>
      <Footer />
    </>
  );
}
