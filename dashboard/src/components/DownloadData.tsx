interface DownloadDataProps {
  gpkgArquivo: string | null;
  gpkgTamanhoMb: number | null;
}

// Entregável principal do diagnóstico é o GeoPackage (não o site — ver
// CLAUDE.md) — este bloco só deixa ele acessível a quem só tem o link do site.
export default function DownloadData({ gpkgArquivo, gpkgTamanhoMb }: DownloadDataProps) {
  if (!gpkgArquivo) return null;
  return (
    <section className="py-6 print:hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-wri-line bg-white p-4">
        <div>
          <h3 className="text-base font-semibold text-wri-ink">Baixar dados completos</h3>
          <p className="mt-1 text-sm text-wri-muted">
            GeoPackage com todas as camadas e indicadores deste diagnóstico — abra no QGIS.
            {gpkgTamanhoMb != null && ` (${gpkgTamanhoMb.toFixed(1)} MB)`}
          </p>
        </div>
        <a
          href={`${import.meta.env.BASE_URL}data/${gpkgArquivo}`}
          download
          className="wri-btn wri-btn--primary wri-btn--md shrink-0"
        >
          Baixar GeoPackage (.gpkg)
        </a>
      </div>
    </section>
  );
}
