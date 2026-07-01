"""Pipeline profiles and configurable defaults for Stock Characters builds.

Profiles are presets; CLI flags and environment variables override them.
Datashare-like behavior is never hard-coded into character formulas.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

# Green SAS recipe: broad link types, no linkprim filter (ALL = no filter).
GREEN_CCM_LINKTYPES = "LU,LC,LD,LF,LN,LO,LS,LX"
GREEN_CCM_LINKPRIM = "ALL"

# HXZ / Fama-French recipe: narrow link types, primary links only.
HXZ_CCM_LINKTYPES = "LU,LC"
HXZ_CCM_LINKPRIM = "P,C"

# CRSP universe recipe (common stock on NYSE/AMEX/NASDAQ) — shared by all profiles.
DEFAULT_CRSP_SHRCD = "10,11"
DEFAULT_CRSP_EXCHCD = "1,2,3"

VALID_PROFILES = frozenset({"green", "datashare", "research"})


@dataclass(frozen=True)
class PipelineConfig:
    profile: str
    sample_start: str | None = None
    sample_end: str | None = None
    green_universe: bool = False
    green_winsor: bool = False
    skip_ibes: bool = True
    build_hxz: bool = True
    build_research_panel: bool = True
    skip_special: bool = False
    skip_daily: bool = False
    # The five required global flags default to None so a bare run with no
    # profile and no explicit flags fails validate_required(). Profiles fill them.
    ccm_linktypes: str | None = None
    ccm_linkprim: str | None = None
    crsp_shrcd: str | None = None
    crsp_exchcd: str | None = None
    datashare_columns: tuple[str, ...] = field(default_factory=tuple)

    def apply_env(self) -> None:
        """Push sample bounds + CCM/CRSP filters into the environment for WRDS SQL."""
        for key, value in (
            ("STOCK_CHARACTERS_SAMPLE_START", self.sample_start),
            ("STOCK_CHARACTERS_SAMPLE_END", self.sample_end),
            ("STOCK_CHARACTERS_CCM_LINKTYPES", self.ccm_linktypes),
            ("STOCK_CHARACTERS_CCM_LINKPRIM", self.ccm_linkprim),
            ("STOCK_CHARACTERS_CRSP_SHRCD", self.crsp_shrcd),
            ("STOCK_CHARACTERS_CRSP_EXCHCD", self.crsp_exchcd),
        ):
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)

    def validate_required(self) -> None:
        """Ensure the five required global flags are set (directly or via a profile)."""
        required = {
            "--ccm-linktypes": self.ccm_linktypes,
            "--ccm-linkprim": self.ccm_linkprim,
            "--crsp-shrcd": self.crsp_shrcd,
            "--crsp-exchcd": self.crsp_exchcd,
            "--sample-start": self.sample_start,
        }
        missing = [flag for flag, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required pipeline flag(s): "
                + ", ".join(missing)
                + ". Pass them explicitly or use --profile green|datashare|research. "
                "See the 'Required flags & recipes' section in README.md / docs/CONFIGURATION.md."
            )


def _profile_defaults(profile: str) -> PipelineConfig:
    if profile == "green":
        return PipelineConfig(
            profile="green",
            sample_start="1975-01-01",
            green_universe=False,
            green_winsor=True,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=True,
            ccm_linktypes=GREEN_CCM_LINKTYPES,
            ccm_linkprim=GREEN_CCM_LINKPRIM,
            crsp_shrcd=DEFAULT_CRSP_SHRCD,
            crsp_exchcd=DEFAULT_CRSP_EXCHCD,
        )
    if profile == "datashare":
        return PipelineConfig(
            profile="datashare",
            sample_start="1957-01-01",
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=False,
            skip_special=False,
            skip_daily=False,
            ccm_linktypes=HXZ_CCM_LINKTYPES,
            ccm_linkprim=HXZ_CCM_LINKPRIM,
            crsp_shrcd=DEFAULT_CRSP_SHRCD,
            crsp_exchcd=DEFAULT_CRSP_EXCHCD,
            datashare_columns=("bm", "operprof", "cfp"),
        )
    if profile == "research":
        return PipelineConfig(
            profile="research",
            sample_start="1975-01-01",
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=True,
            ccm_linktypes=GREEN_CCM_LINKTYPES,
            ccm_linkprim=GREEN_CCM_LINKPRIM,
            crsp_shrcd=DEFAULT_CRSP_SHRCD,
            crsp_exchcd=DEFAULT_CRSP_EXCHCD,
        )
    raise ValueError(f"Unknown profile: {profile!r}. Choose from {sorted(VALID_PROFILES)}")


def resolve_config(
    profile: str | None = None,
    *,
    sample_start: str | None = None,
    sample_end: str | None = None,
    green_universe: bool | None = None,
    green_winsor: bool | None = None,
    skip_ibes: bool | None = None,
    build_hxz: bool | None = None,
    build_research_panel: bool | None = None,
    skip_special: bool | None = None,
    skip_daily: bool | None = None,
    ccm_linktypes: str | None = None,
    ccm_linkprim: str | None = None,
    crsp_shrcd: str | None = None,
    crsp_exchcd: str | None = None,
) -> PipelineConfig:
    """Merge profile defaults with explicit CLI overrides."""
    prof = (profile or os.environ.get("STOCK_CHARACTERS_PROFILE") or "").strip().lower()
    if prof and prof not in VALID_PROFILES:
        raise ValueError(f"Unknown profile {prof!r}. Choose from {sorted(VALID_PROFILES)}")

    # No profile (and no env profile) → bare base with required flags unset; the
    # caller must supply all five flags explicitly or validate_required() errors.
    base = _profile_defaults(prof) if prof else PipelineConfig(profile="")
    overrides: dict = {}

    if sample_start is not None:
        overrides["sample_start"] = sample_start or None
    if sample_end is not None:
        overrides["sample_end"] = sample_end or None
    if green_universe is not None:
        overrides["green_universe"] = green_universe
    if green_winsor is not None:
        overrides["green_winsor"] = green_winsor
    if skip_ibes is not None:
        overrides["skip_ibes"] = skip_ibes
    if build_hxz is not None:
        overrides["build_hxz"] = build_hxz
    if build_research_panel is not None:
        overrides["build_research_panel"] = build_research_panel
    if skip_special is not None:
        overrides["skip_special"] = skip_special
    if skip_daily is not None:
        overrides["skip_daily"] = skip_daily
    if ccm_linktypes is not None:
        overrides["ccm_linktypes"] = ccm_linktypes
    if ccm_linkprim is not None:
        overrides["ccm_linkprim"] = ccm_linkprim
    if crsp_shrcd is not None:
        overrides["crsp_shrcd"] = crsp_shrcd
    if crsp_exchcd is not None:
        overrides["crsp_exchcd"] = crsp_exchcd

    if overrides:
        return PipelineConfig(**{**base.__dict__, **overrides})
    return base


def profile_help() -> str:
    return """
Profiles (each is a complete recipe of the required flags; see README 'Required flags & recipes'):
  green      Replicate Green SAS: broad CCM linktypes, no linkprim (ALL), shrcd 10,11, exchcd 1,2,3, 1975+ start.
  datashare  Match datashare.csv: LU,LC + linkprim P,C, shrcd 10,11, exchcd 1,2,3, 1957+ start, sparse panel.
  research   Full ranked 1957+ panel: Green recipe link rules, 1975+ build start.

Required flags (or a profile that sets them): --ccm-linktypes, --ccm-linkprim, --crsp-shrcd, --crsp-exchcd, --sample-start.
""".strip()
