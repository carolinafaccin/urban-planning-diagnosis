interface TopBarProps {
  cidade: string;
}

// Mesma identidade visual do dashboard do climate-injustice-index (logo +
// borda inferior). Sem navegação — este site é de um projeto só, não um
// explorador multi-página.
export default function TopBar({ cidade }: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-wri-line bg-white px-3 sm:px-5 print:hidden">
      <a
        href="https://www.wribrasil.org.br"
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-w-0 items-center gap-3"
      >
        <img
          src={`${import.meta.env.BASE_URL}wri-brasil-logo.png`}
          alt="WRI Brasil"
          className="h-7 w-auto sm:h-8"
        />
        <span className="hidden truncate border-l border-wri-line pl-3 text-sm font-semibold tracking-tight text-wri-ink md:inline">
          Diagnóstico territorial urbanístico — {cidade}
        </span>
      </a>
      <button
        onClick={() => window.print()}
        className="wri-btn wri-btn--secondary wri-btn--sm shrink-0"
      >
        Salvar como PDF
      </button>
    </header>
  );
}
