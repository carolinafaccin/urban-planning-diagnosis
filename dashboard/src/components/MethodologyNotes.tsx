import { marked } from "marked";
import notesMd from "../content/methodological_notes.md?raw";

export default function MethodologyNotes() {
  return (
    <section id="metodologia" className="py-6">
      <h2 className="border-l-4 border-wri-yellow pl-3 text-xl font-semibold text-wri-ink">
        Notas metodológicas
      </h2>
      <div
        className="prose-notes mt-3 max-w-2xl pl-3"
        dangerouslySetInnerHTML={{ __html: marked.parse(notesMd, { async: false }) }}
      />
    </section>
  );
}
