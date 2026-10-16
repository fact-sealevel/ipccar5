"""
Logic for application IO.
"""

from datetime import datetime, timezone
from importlib.metadata import version
import os
import re

import numpy as np
import xarray as xr

from ipccar5.core import (
    ClimateData,
    RegionalFractions,
    check_scenario_match,
)

CF_CONVENTIONS = "CF-1.11"

# Name of the sea-level variable in GMSL output files
GMSL_VARIABLE = "sea_level_change"


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def read_climate(
    climate_fname: str | os.PathLike,
    scenario: str,
    variable: str = "surface_temperature",
) -> ClimateData:
    """
    Read the FaIR temperature ensemble, variable(year, sample), from a
    single-scenario netCDF file.

    The variable is read from the root of the file. Older files that store it
    in a group named after the scenario, with dims (years, samples), are still
    supported.

    Raises ValueError if the file's 'Scenario' attribute is missing or does not
    match scenario.
    """
    with xr.open_dataset(climate_fname, engine="netcdf4") as ds:
        if variable in ds:
            return _climate_from_dataset(ds, variable, scenario, climate_fname)

    # Fall back to the older layout with the data in a group named after the scenario
    try:
        with xr.open_dataset(climate_fname, engine="netcdf4", group=scenario) as ds:
            if variable in ds:
                legacy_dims = {"years": "year", "samples": "sample"}
                return _climate_from_dataset(
                    ds.rename({k: v for k, v in legacy_dims.items() if k in ds.dims}),
                    variable,
                    scenario,
                    climate_fname,
                )
    except OSError:
        pass

    raise ValueError(
        f"Cannot find '{variable}' in {climate_fname}, either at the root "
        f"or in a '{scenario}' group."
    )


CLIMATE_DIMS = ("year", "sample")


def _climate_from_dataset(
    ds: xr.Dataset, variable: str, scenario: str, climate_fname: str | os.PathLike
) -> ClimateData:
    check_scenario_match(
        requested=scenario,
        found=ds.attrs.get("Scenario", ds.attrs.get("scenario")),
        source=str(climate_fname),
    )

    dims = ds[variable].dims
    if set(dims) != set(CLIMATE_DIMS):
        raise ValueError(
            f"'{variable}' in {climate_fname} has dimensions {dims}, but FaIR "
            f"output is expected to have dimensions {CLIMATE_DIMS}."
        )
    return ClimateData(
        samples=ds[variable].transpose("year", "sample").values,
        years=ds["year"].values,
    )


def read_regional_fractions(fname: str | os.PathLike) -> RegionalFractions:
    """
    Read a glacier or icesheet fraction file.

    The header line is 'region, <year>, <year>, ...'; each following line is
    '<region name>, <fraction>, <fraction>, ...'.
    """
    fractions = []
    region_names = []
    with open(fname, "r", encoding="utf-8") as fp:
        header_items = re.split(r",\s*", fp.readline())
        years = np.array([int(x) for x in header_items[1:]])

        for line in fp:
            line_parts = re.split(r",\s*", line.rstrip())
            region_names.append(line_parts[0])
            fractions.append([float(x) for x in line_parts[1:]])

    return RegionalFractions(
        region_names=region_names, years=years, fractions=np.array(fractions)
    )


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def make_gmsl_ds(
    samps: np.ndarray,
    nsamps: int,
    data_years: np.ndarray,
    pipeline_id: str,
    baseyear: int,
    scenario: str,
    budget_term: str,
    source_region: str | list[str],
    module_name: str,
    region_names: list[str] | None = None,
) -> xr.Dataset:
    """
    Build a GMSL dataset with dims (sample, year, budget_term, source_region).

    Pass a single source_region with samps shaped [samples, years], or a list
    of source regions with samps shaped [samples, years, regions].
    """
    if isinstance(source_region, str):
        source_region = [source_region]
        samps = samps[:, :, np.newaxis]
    # Add a length-1 budget_term axis: [samples, years, 1, regions]
    samps = samps[:, :, np.newaxis, :]
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ds = xr.Dataset(
        {
            GMSL_VARIABLE: (
                ("sample", "year", "budget_term", "source_region"),
                samps,
                {
                    "long_name": f"global mean sea-level change relative to {baseyear}",
                    "units": "mm",
                },
            )
        },
        coords={
            "sample": (
                ("sample",),
                np.arange(nsamps),
                {"long_name": "sample index"},
            ),
            "year": (
                ("year",),
                data_years,
                {"long_name": "calendar year"},
            ),
            "budget_term": (
                ("budget_term",),
                [budget_term],
                {"long_name": "sea-level budget term"},
            ),
            "source_region": (
                ("source_region",),
                source_region,
                {"long_name": "source region of the sea-level contribution"},
            ),
        },
        attrs={
            "Conventions": CF_CONVENTIONS,
            "title": f"Global mean sea-level contribution from {module_name}",
            "source": f"FACTS2 ipccar5 {version('ipccar5')}",
            "history": f"{created}: created by FACTS2 pipeline {pipeline_id}",
            "baseyear": baseyear,
            "scenario": scenario,
        },
    )
    if region_names is not None:
        # Kept as an attribute rather than a coordinate so files from different
        # modules can still be concatenated along source_region.
        ds["source_region"].attrs["region_names"] = ", ".join(
            f"{key}: {name}" for key, name in zip(source_region, region_names)
        )
    return ds


def write_gmsl_projection(ds: xr.Dataset, gslr_out_name: str) -> None:
    ds.to_netcdf(
        gslr_out_name,
        mode="w",
        format="NETCDF4",
        engine="netcdf4",
        encoding={GMSL_VARIABLE: {"zlib": True, "complevel": 4}},
    )
