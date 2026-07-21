"""
deploy.py
---------
O que faz   : Publica o dashboard/ no Cloudflare Pages com um comando. Builda
              o site (npm run build) e publica dist/ via wrangler, no branch
              do projeto atual (um Pages project guarda-chuva, um branch por
              projeto/bbox — vira <PAGES_BRANCH>.<PAGES_PROJECT>.pages.dev).
Uso         : a partir da pasta do projeto (onde está o config.py):
                cd projetos/campinas
                python ../../dashboard/deploy.py             # builda e publica
                python ../../dashboard/deploy.py --skip-data  # não regenera
                                                               # report.json/imgs antes
                python ../../dashboard/deploy.py --branch teste  # sobrescreve o branch
                                                                   # (ex.: deploy de teste
                                                                   # antes de publicar
                                                                   # no branch definitivo)
Requer      : Node.js + wrangler autenticado (`wrangler login`); GeoPackage do
              projeto já construído (10_build_geopackage.py + 11_analises.py).
Config      : lê PAGES_PROJECT/PAGES_BRANCH do config.py do projeto. Genérico —
              para publicar outro projeto, rode a partir da pasta dele.
Privacidade : quem restringe o acesso (allowlist de e-mails) é o Cloudflare
              Access, configurado uma vez no painel Zero Trust — este script
              não mexe nisso; redeploys reusam a mesma URL e o mesmo Access.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PREP = SCRIPT_DIR / "data_prep" / "build_web_assets.py"


def main():
    if not Path("config.py").exists():
        sys.exit(
            "erro: rode a partir da pasta do projeto (onde está o config.py).\n"
            "  ex.: cd projetos/campinas && python ../../dashboard/deploy.py"
        )

    sys.path.insert(0, str(Path.cwd()))
    from config import PAGES_BRANCH, PAGES_PROJECT  # noqa: E402

    ap = argparse.ArgumentParser(description="Deploy do dashboard/ no Cloudflare Pages.")
    ap.add_argument("--skip-data", action="store_true",
                     help="Não regenera report.json/imgs antes do deploy.")
    ap.add_argument("--branch", default=PAGES_BRANCH,
                     help=f"Sobrescreve o branch de deploy (padrão: {PAGES_BRANCH}).")
    args = ap.parse_args()

    if not args.skip_data:
        print("==> gerando report.json + imagens...")
        subprocess.run([sys.executable, str(DATA_PREP)], check=True)

    print("==> npm run build (dashboard/)...")
    subprocess.run(["npm", "run", "build"], cwd=SCRIPT_DIR, check=True)

    dist_dir = SCRIPT_DIR / "dist"
    if not (dist_dir / "index.html").exists():
        sys.exit(f"erro: build não produziu {dist_dir / 'index.html'}")

    print(f"==> publicando {dist_dir}")
    print(f"    projeto Pages: {PAGES_PROJECT}  (branch: {args.branch})")
    print(f"    URL: https://{args.branch}.{PAGES_PROJECT}.pages.dev")
    subprocess.run(
        ["wrangler", "pages", "deploy", str(dist_dir),
         "--project-name", PAGES_PROJECT, "--branch", args.branch],
        check=True,
    )


if __name__ == "__main__":
    main()
    print("\nConcluído.")
