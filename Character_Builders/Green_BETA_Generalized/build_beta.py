import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.beta_builder import run_beta_cli


if __name__ == "__main__":
    run_beta_cli()
