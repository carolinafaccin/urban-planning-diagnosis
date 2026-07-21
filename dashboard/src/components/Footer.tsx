export default function Footer() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-wri-line bg-slate-50 px-5 py-3 print:hidden">
      <img
        src={`${import.meta.env.BASE_URL}wri-brasil-logo-k.png`}
        alt="WRI Brasil"
        className="h-6 w-auto opacity-80"
      />
      <nav className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-wri-muted">
        <a
          href="https://www.wribrasil.org.br/sobre"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2 hover:text-wri-ink"
        >
          Sobre o WRI Brasil
        </a>
        <a
          href="https://www.wribrasil.org.br/contato"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2 hover:text-wri-ink"
        >
          Contato
        </a>
        <a
          href="https://www.wribrasil.org.br/politica-de-privacidade-e-protecao-de-dados"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2 hover:text-wri-ink"
        >
          Política de Privacidade e Proteção de Dados
        </a>
        <a href="#metodologia" className="underline underline-offset-2 hover:text-wri-ink">
          Notas Metodológicas
        </a>
        <span className="text-wri-muted/70">© WRI Brasil {new Date().getFullYear()}</span>
      </nav>
    </footer>
  );
}
