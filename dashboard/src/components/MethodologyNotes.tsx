import { marked } from "marked";
import notesMd from "../content/methodological_notes.md?raw";

export default function MethodologyNotes() {
  return (
    <section id="metodologia" className="py-6">
      <h2 className="text-xl font-semibold text-wri-ink">Notas metodológicas</h2>
      <div
        className="prose prose-sm mt-3 max-w-2xl text-wri-ink"
        dangerouslySetInnerHTML={{ __html: marked.parse(notesMd, { async: false }) }}
      />
    </section>
  );
}
