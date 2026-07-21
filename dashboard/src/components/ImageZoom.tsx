import { useEffect, useState } from "react";

interface ImageZoomProps {
  src: string;
  alt: string;
  className?: string;
}

// Miniatura clicável → modal com a imagem ampliada + link de download direto
// do PNG original (mesmo arquivo servido em REPORT_DIR, sem reprocessamento).
export default function ImageZoom({ src, alt, className }: ImageZoomProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative block w-full cursor-zoom-in"
        aria-label={`Ampliar: ${alt}`}
      >
        <img src={src} alt={alt} className={className} loading="lazy" />
        <span className="pointer-events-none absolute bottom-2 right-2 rounded-md bg-black/60 px-2 py-1 text-[11px] text-white opacity-0 transition group-hover:opacity-100">
          Ampliar
        </span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 print:hidden"
          onClick={() => setOpen(false)}
        >
          <div
            className="relative flex max-h-full max-w-5xl flex-col items-center"
            onClick={(e) => e.stopPropagation()}
          >
            <img src={src} alt={alt} className="max-h-[80vh] w-auto rounded-lg shadow-2xl" />
            <div className="mt-3 flex gap-3">
              <a href={src} download className="wri-btn wri-btn--primary wri-btn--sm">
                Baixar imagem
              </a>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="wri-btn wri-btn--secondary wri-btn--sm"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
