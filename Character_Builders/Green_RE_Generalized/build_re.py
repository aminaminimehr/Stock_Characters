import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.ibes_builders import run_re_cli


if __name__ == "__main__":
    run_re_cli()
