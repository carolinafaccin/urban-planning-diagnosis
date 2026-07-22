"""
_projeto.py
-----------
Resolve o config.py de um projeto sem depender do cwd — permite rodar
qualquer script deste repositório (individual ou via run.py) a partir da
raiz do repo, além do padrão antigo (cd projetos/<cidade> && python ...).

Prefixo "_" no nome: não é um passo do pipeline (não entra em manifest.py),
é infraestrutura compartilhada.

Prioridade de resolução:
1. `projeto` explícito (slug em projetos/<slug>/), passado por quem chama
   carregar_config() — normalmente vindo de --projeto na CLI de run.py ou
   de um script individual.
2. Variável de ambiente DIAGNOSTICO_PROJETO=<slug>.
3. cwd contém config.py (convenção antiga: cd projetos/<cidade> antes de
   rodar) — mantida por compatibilidade, nenhum script quebra.

Uso a partir da raiz do repo, sem precisar de --projeto em cada comando:
    export DIAGNOSTICO_PROJETO=campinas
    python scripts/pipeline/download_osm.py
    python scripts/run.py
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def carregar_config(projeto=None):
    if projeto is None:
        projeto = os.environ.get("DIAGNOSTICO_PROJETO")

    if projeto:
        projeto_dir = (REPO_ROOT / "projetos" / projeto).resolve()
        if not (projeto_dir / "config.py").exists():
            raise SystemExit(
                f"erro: projetos/{projeto}/config.py não existe "
                f"(--projeto/DIAGNOSTICO_PROJETO='{projeto}')."
            )
    else:
        projeto_dir = Path.cwd()
        if not (projeto_dir / "config.py").exists():
            raise SystemExit(
                "erro: rode a partir da pasta do projeto (onde está o config.py), "
                "ou passe --projeto <slug> / defina DIAGNOSTICO_PROJETO=<slug>.\n"
                "  ex.: cd projetos/campinas && python ../../scripts/pipeline/download_osm.py\n"
                "  ex.: DIAGNOSTICO_PROJETO=campinas python scripts/pipeline/download_osm.py"
            )

    sys.path.insert(0, str(projeto_dir))
    import config
    return config
