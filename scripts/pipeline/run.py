"""
run.py
------
Orquestrador do pipeline: roda os scripts de scripts/pipeline/ na ordem de
manifest.py, chamando main(config) de cada um em vez de disparar um
processo Python separado por passo.

Por que mora em scripts/pipeline/ (e não na raiz do repo): os scripts do
pipeline também moram aqui, e o manifesto (manifest.py) é lido por caminho
relativo a este arquivo — manter os três juntos evita ter que descobrir
"onde fica o pipeline" a partir de dois lugares diferentes no repo. A regra
de "rodar a partir da pasta do projeto" (cd projetos/<cidade>) é a mesma dos
outros scripts, então isso não é uma inconsistência nova.

Como rodar  : a partir da pasta do projeto (onde está o config.py):
              cd projetos/campinas
              python ../../scripts/pipeline/run.py
              python ../../scripts/pipeline/run.py --from h3_dasimetrico
              python ../../scripts/pipeline/run.py --only analises
              python ../../scripts/pipeline/run.py --skip dados_municipais --skip indicadores_municipais

Convenção "SKIP:" — um passo que decide pular uma sub-etapa por falta de
dado manual (ex.: CAMADAS_MUNICIPAIS vazio, geojson/analise_area.md
ausentes) imprime uma linha começando literalmente com "SKIP:". Este
orquestrador captura essas linhas (sem deixar de exibi-las em tempo real) e
as usa só para o resumo final — a decisão de pular já foi tomada pelo
próprio script, o run.py não reimplementa essa lógica.
"""

import argparse
import importlib.util
import io
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
from manifest import PASSOS  # noqa: E402


class _TeeCapturaSkip(io.TextIOBase):
    """Ecoa cada escrita no stdout real e guarda as linhas 'SKIP: ...' que
    passarem por aqui — sem bufferizar a saída inteira (o script continua
    imprimindo progresso em tempo real, só que também sob observação)."""

    def __init__(self, stdout_real):
        self._stdout_real = stdout_real
        self._resto_linha = ""
        self.skips = []

    def write(self, texto):
        self._stdout_real.write(texto)
        buffer = self._resto_linha + texto
        linhas = buffer.split("\n")
        self._resto_linha = linhas.pop()  # sobra sem \n, junta na próxima escrita
        for linha in linhas:
            if linha.startswith("SKIP:"):
                self.skips.append(linha[len("SKIP:"):].strip())
        return len(texto)

    def flush(self):
        self._stdout_real.flush()


def carregar_modulo(passo):
    """Importa o arquivo do passo por caminho (não por `import` normal, que
    exigiria os arquivos no sys.path como pacote). Usa `caminho` (relativo à
    raiz do repo) quando o passo define um — caso dos passos de dashboard/ —
    senão assume scripts/pipeline/<modulo>.py."""
    nome = passo["modulo"]
    if "caminho" in passo:
        caminho = REPO_ROOT / passo["caminho"]
    else:
        caminho = PIPELINE_DIR / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def rodar_passo(passo, cfg):
    """Executa main(cfg, **kwargs) de um passo, capturando linhas 'SKIP:'
    impressas. Retorna (status, motivos) — status em {'ok', 'skip'}; 'skip'
    só quando o próprio passo sinalizou SKIP (não há como saber sem rodar
    main())."""
    modulo = carregar_modulo(passo)
    kwargs = passo.get("kwargs", {})

    stdout_real = sys.stdout
    tee = _TeeCapturaSkip(stdout_real)
    sys.stdout = tee
    try:
        modulo.main(cfg, **kwargs)
    finally:
        sys.stdout = stdout_real

    if tee.skips:
        return "skip", tee.skips
    return "ok", []


def selecionar_passos(passos, so_este, a_partir_de, pular):
    if so_este:
        selecionados = [p for p in passos if p["modulo"] == so_este]
        if not selecionados:
            raise SystemExit(f"--only {so_este}: módulo não encontrado no manifest.py")
        return selecionados

    if a_partir_de:
        nomes = [p["modulo"] for p in passos]
        if a_partir_de not in nomes:
            raise SystemExit(f"--from {a_partir_de}: módulo não encontrado no manifest.py")
        idx = nomes.index(a_partir_de)
        passos = passos[idx:]

    if pular:
        passos = [p for p in passos if p["modulo"] not in pular]

    return passos


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="a_partir_de", metavar="MODULO",
                        help="roda a partir deste passo, inclusive (ex.: h3_dasimetrico)")
    parser.add_argument("--only", dest="so_este", metavar="MODULO",
                        help="roda só este passo")
    parser.add_argument("--skip", dest="pular", metavar="MODULO", action="append", default=[],
                        help="pula este passo (repetível), mesmo que não seja opcional")
    args = parser.parse_args()

    sys.path.insert(0, str(Path.cwd()))
    import config

    passos = selecionar_passos(PASSOS, args.so_este, args.a_partir_de, set(args.pular))
    if not passos:
        raise SystemExit("Nenhum passo selecionado (confira --from/--only/--skip).")

    rodados, pulados_manual = [], []

    for i, passo in enumerate(passos, start=1):
        nome = passo["modulo"]
        print(f"\n{'='*70}\n[{i}/{len(passos)}] {nome}\n{'='*70}")

        try:
            status, motivos = rodar_passo(passo, config)
        except Exception:
            print(f"\n{'!'*70}\nFALHOU: {nome}\n{'!'*70}", file=sys.stderr)
            raise

        if status == "skip":
            pulados_manual.append((nome, motivos))
        else:
            rodados.append(nome)

    print(f"\n{'='*70}\nResumo da execução\n{'='*70}")
    print(f"Rodados com sucesso ({len(rodados)}): {', '.join(rodados) or '—'}")
    if pulados_manual:
        print(f"Pulados pelo próprio passo ({len(pulados_manual)}):")
        for nome, motivos in pulados_manual:
            for motivo in motivos:
                print(f"  - {nome}: {motivo}")
    if args.pular:
        print(f"Pulados via --skip: {', '.join(args.pular)}")


if __name__ == "__main__":
    main()
