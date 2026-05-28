import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.rvar_factor_builders import run_factor_rvar_cli


if __name__ == "__main__":
    run_factor_rvar_cli(
        "rvar_ff3",
        "Residual variance from daily Fama-French 3-factor regressions over the previous 3 months.",
        ["mktrf", "smb", "hml"],
    )
