import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.event_builders import run_abr_cli


if __name__ == "__main__":
    run_abr_cli()
