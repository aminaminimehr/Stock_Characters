"""Pipeline profiles and configurable defaults for Stock Characters builds.

Profiles are presets; CLI flags and environment variables override them.
Datashare-like behavior is never hard-coded into character formulas.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

# Green SAS uses broad link types without linkprim filter.
GREEN_CCM_LINKTYPES = "LU,LC,LD,LF,LN,LO,LS,LX"
GREEN_CCM_LINKPRIM = ""

# HXZ / Fama-French default (also used for datashare bm/operprof via HXZ builders).
HXZ_CCM_LINKTYPES = "LU,LC"
HXZ_CCM_LINKPRIM = "P,C"

VALID_PROFILES = frozenset({"green", "datashare", "research"})


@dataclass(frozen=True)
class PipelineConfig:
    profile: str
    sample_start: str | None = None
    sample_end: str | None = None
    green_universe: bool = False
    skip_ibes: bool = True
    build_hxz: bool = True
    build_research_panel: bool = True
    green_ccm_linktypes: str = GREEN_CCM_LINKTYPES
    green_ccm_linkprim: str = GREEN_CCM_LINKPRIM
    hxz_ccm_linktypes: str = HXZ_CCM_LINKTYPES
    hxz_ccm_linkprim: str = HXZ_CCM_LINKPRIM
    datashare_columns: tuple[str, ...] = field(default_factory=tuple)

    def apply_env(self) -> None:
        """Push sample bounds into environment for WRDS SQL filters."""
        if self.sample_start:
            os.environ["STOCK_CHARACTERS_SAMPLE_START"] = self.sample_start
        else:
            os.environ.pop("STOCK_CHARACTERS_SAMPLE_START", None)
        if self.sample_end:
            os.environ["STOCK_CHARACTERS_SAMPLE_END"] = self.sample_end
        else:
            os.environ.pop("STOCK_CHARACTERS_SAMPLE_END", None)


def _profile_defaults(profile: str) -> PipelineConfig:
    if profile == "green":
        return PipelineConfig(
            profile="green",
            sample_start=None,  # green_builders default floor 1975-01-01
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=True,
            green_ccm_linktypes=GREEN_CCM_LINKTYPES,
            green_ccm_linkprim=GREEN_CCM_LINKPRIM,
        )
    if profile == "datashare":
        return PipelineConfig(
            profile="datashare",
            sample_start="1957-01-01",
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=False,
            green_ccm_linktypes=GREEN_CCM_LINKTYPES,
            green_ccm_linkprim=GREEN_CCM_LINKPRIM,
            datashare_columns=("bm", "operprof", "cfp"),
        )
    if profile == "research":
        return PipelineConfig(
            profile="research",
            sample_start=None,
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=True,
            green_ccm_linktypes=GREEN_CCM_LINKTYPES,
            green_ccm_linkprim=GREEN_CCM_LINKPRIM,
        )
    raise ValueError(f"Unknown profile: {profile!r}. Choose from {sorted(VALID_PROFILES)}")


def resolve_config(
    profile: str | None = None,
    *,
    sample_start: str | None = None,
    sample_end: str | None = None,
    green_universe: bool | None = None,
    skip_ibes: bool | None = None,
    build_hxz: bool | None = None,
    build_research_panel: bool | None = None,
    ccm_linktypes: str | None = None,
    ccm_linkprim: str | None = None,
) -> PipelineConfig:
    """Merge profile defaults with explicit CLI overrides."""
    prof = (profile or os.environ.get("STOCK_CHARACTERS_PROFILE") or "green").strip().lower()
    if prof not in VALID_PROFILES:
        raise ValueError(f"Unknown profile {prof!r}. Choose from {sorted(VALID_PROFILES)}")

    base = _profile_defaults(prof)
    overrides: dict = {}

    if sample_start is not None:
        overrides["sample_start"] = sample_start or None
    if sample_end is not None:
        overrides["sample_end"] = sample_end or None
    if green_universe is not None:
        overrides["green_universe"] = green_universe
    if skip_ibes is not None:
        overrides["skip_ibes"] = skip_ibes
    if build_hxz is not None:
        overrides["build_hxz"] = build_hxz
    if build_research_panel is not None:
        overrides["build_research_panel"] = build_research_panel
    if ccm_linktypes is not None:
        overrides["green_ccm_linktypes"] = ccm_linktypes
        overrides["hxz_ccm_linktypes"] = ccm_linktypes
    if ccm_linkprim is not None:
        overrides["green_ccm_linkprim"] = ccm_linkprim
        overrides["hxz_ccm_linkprim"] = ccm_linkprim

    if overrides:
        return PipelineConfig(**{**base.__dict__, **overrides})
    return base


def profile_help() -> str:
    return """
Profiles:
  green      Replicate Green SAS library (default annual start 1975; optional --green-universe).
  datashare  Match datashare.csv for bm/operprof/cfp: 1957+ sample, sparse panel, no joint screen.
  research   Full pipeline through ranked 1957+ research panel.
""".strip()
