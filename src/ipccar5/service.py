"""
Services the UI provides to our lovely users.
"""

import logging

import numpy as np

from ipccar5.core import (
    fit_glaciers,
    fit_icesheets,
    preprocess,
    project_glaciers,
    project_icesheets,
    split_glacier_regions,
    GLACIER_REGIONS,
)
from ipccar5.io import (
    read_climate,
    read_regional_fractions,
    make_gmsl_ds,
    write_gmsl_projection,
)

logger = logging.getLogger(__name__)

GLACIERS_BUDGET_TERM = "glaciers"
GLACIERS_SOURCE_REGION = "global"
ICESHEETS_BUDGET_TERM = "icesheets"

# Icesheets always runs over the full temperature record
ICESHEETS_END_YEAR = 2301


def run_glaciers(
    *,
    scenario,
    climate_data_file,
    refyear_start,
    refyear_end,
    start_year,
    end_year,
    use_gmip,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    pipeline_id,
    global_output_file,
    glacier_fraction_file=None,
    global_regions_output_file=None,
) -> None:
    """
    Project the glacier contribution to global sea level, optionally also split
    by glacier region.
    """
    climate = read_climate(climate_data_file, scenario)

    temperature = preprocess(
        climate,
        scenario=scenario,
        refyear_start=refyear_start,
        refyear_end=refyear_end,
        start_year=start_year,
        end_year=end_year,
    )
    fit = fit_glaciers(start_year=start_year, use_gmip=use_gmip)

    targyears = np.arange(pyear_start, pyear_end + 1, pyear_step)
    gslr, years = project_glaciers(
        temperature,
        fit,
        rng_seed=rng_seed,
        targyears=targyears,
        nmsamps=nmsamps,
        ntsamps=ntsamps,
        nsamps=nsamps,
    )

    if global_output_file is not None:
        ds = make_gmsl_ds(
            samps=gslr,
            nsamps=gslr.shape[0],
            data_years=years,
            pipeline_id=pipeline_id,
            baseyear=start_year,
            scenario=scenario,
            budget_term=GLACIERS_BUDGET_TERM,
            source_region=GLACIERS_SOURCE_REGION,
            module_name="glaciers and ice caps according to the IPCC AR5 workflow",
        )
        write_gmsl_projection(ds, global_output_file)

    if global_regions_output_file is not None:
        if glacier_fraction_file is None:
            raise ValueError(
                "A glacier fraction file is required to write regional glacier output."
            )
        gicsamps = split_glacier_regions(
            gslr, read_regional_fractions(glacier_fraction_file), years
        )
        # Reorder from fraction-file order to RGI order
        order = np.argsort([rgi_id for rgi_id, _, _ in GLACIER_REGIONS])
        regions = [GLACIER_REGIONS[i] for i in order]
        ds = make_gmsl_ds(
            samps=np.moveaxis(gicsamps[:, order, :], 1, 2),  # [samples, years, regions]
            nsamps=gicsamps.shape[0],
            data_years=years,
            pipeline_id=pipeline_id,
            baseyear=start_year,
            scenario=scenario,
            budget_term=GLACIERS_BUDGET_TERM,
            source_region=[f"rgi{rgi_id:02d}" for rgi_id, _, _ in regions],
            module_name="glaciers and ice caps by RGI region according to the IPCC AR5 workflow",
            region_names=[name for _, name, _ in regions],
        )
        write_gmsl_projection(ds, global_regions_output_file)


def run_icesheets(
    *,
    scenario,
    climate_data_file,
    icesheet_fraction_file,
    refyear_start,
    refyear_end,
    start_year,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    pipeline_id,
    global_gis_output_file,
    global_ais_output_file,
    global_wais_output_file,
    global_eais_output_file,
) -> None:
    """Project the GIS and AIS contributions to global sea level."""
    climate = read_climate(climate_data_file, scenario)
    antarctic_fractions = read_regional_fractions(icesheet_fraction_file)

    temperature = preprocess(
        climate,
        scenario=scenario,
        refyear_start=refyear_start,
        refyear_end=refyear_end,
        start_year=start_year,
        end_year=ICESHEETS_END_YEAR,
    )
    fit = fit_icesheets(scenario)

    targyears = np.arange(pyear_start, pyear_end + 1, pyear_step)
    projection = project_icesheets(
        temperature,
        fit,
        antarctic_fractions,
        rng_seed=rng_seed,
        targyears=targyears,
        cyear_start=pyear_start,
        cyear_end=pyear_end,
        nmsamps=nmsamps,
        ntsamps=ntsamps,
        nsamps=nsamps,
    )

    # Write the global projections, one file per source region
    global_outputs = {
        "gis": (projection.gis, global_gis_output_file),
        "ais": (projection.ais, global_ais_output_file),
        "wais": (projection.wais, global_wais_output_file),
        "eais": (projection.eais, global_eais_output_file),
    }
    for source_region, (samps, output_file) in global_outputs.items():
        if output_file is None:
            continue
        ds = make_gmsl_ds(
            samps=samps,
            nsamps=samps.shape[0],
            data_years=projection.years,
            pipeline_id=pipeline_id,
            baseyear=start_year,
            scenario=scenario,
            budget_term=ICESHEETS_BUDGET_TERM,
            source_region=source_region,
            module_name=f"{source_region.upper()} using the ice sheet projection approach adopted by IPCC AR5 WG1",
        )
        write_gmsl_projection(ds, output_file)
