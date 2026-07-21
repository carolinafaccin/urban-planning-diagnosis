import { marked } from "marked";

interface AnaliseAreaProps {
  analiseMd: string;
}

// Texto descritivo específico do projeto (não é código, é dado — ver
// LOCAL_DATA_DIR/analise_area.md em build_web_assets.py). Renderizado em
// runtime porque o conteúdo só existe no data_dir, não no build do Vite.
export default function AnaliseArea({ analiseMd }: AnaliseAreaProps) {
  if (!analiseMd.trim()) return null;
  return (
    <section id="analise" className="py-6">
      <h2 className="text-xl font-semibold text-wri-ink">Análise da área</h2>
      <div
        className="prose prose-sm mt-3 max-w-2xl text-wri-ink"
        dangerouslySetInnerHTML={{ __html: marked.parse(analiseMd, { async: false }) }}
      />
    </section>
  );
}
