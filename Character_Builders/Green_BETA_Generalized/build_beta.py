import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.green_builders import run_character_cli


if __name__ == "__main__":
    run_character_cli("beta", "Beta rolling 3m")
