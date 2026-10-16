"""
Logic for the CLI.
"""

import click
import logging

from ipccar5.service import run_glaciers, run_icesheets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass


@main.command()
@click.option(
    "--scenario",
    type=str,
    help="Scenario",
)
@click.option(
    "--refyear-start",
    default=1986,
    show_default=True,
    type=int,
    help="Start year for reference period",
)
@click.option(
    "--refyear-end",
    default=2005,
    show_default=True,
    type=int,
    help="End year for reference period",
)
@click.option(
    "--start-year",  # this is same as baseyear
    default=2005,
    show_default=True,
    type=int,
    help="Year from which to start integrating temperature",
)
@click.option(
    "--end-year",
    default=2301,
    show_default=True,
    type=int,
    help="Year to end the projection (Used in preprocess).",
)
@click.option(
    "--tlm-flag",
    default=1,
    show_default=True,
    type=int,
    help="Use the two-layer model data, 1=yes",
)
@click.option(
    "--pipeline-id", type=str, help="Unique identifier for this instance of the module"
)
@click.option(
    "--climate-data-file",
    type=str,
    help="NetCDF4/HDF5 file containing surface temperature data (this should be a fair output)",
    required=True,
)
@click.option(
    "--rng-seed",
    default=1234,
    show_default=True,
    type=int,
    help="Seed value for random number generator",
)
@click.option(
    "--pyear-start",
    default=2020,
    show_default=True,
    type=int,
    help="Projection start year",
)
@click.option(
    "--pyear-end",
    default=2150,
    show_default=True,
    type=int,
    help="Projection end year",
)
@click.option(
    "--pyear-step",
    default=10,
    show_default=True,
    type=int,
    help="Projection year step",
)
@click.option(
    "--nmsamps",
    default=1000,
    show_default=True,
    required=False,
    type=int,
    help="Number of method samples to generate",
)
@click.option(
    "--ntsamps",
    default=450,
    show_default=True,
    required=False,
    type=int,
    help="Number of climate samples to generate",
)
@click.option(
    "--nsamps",
    required=False,
    type=int,
    help="Total number of samples to generate (replaces 'nmsamps' and 'ntsamps' if provided)",
)
@click.option(
    "--use-gmip",
    help="Use the GMIP calibration",
    default=2,
    show_default=True,
    type=click.Choice([0, 1, 2]),
)
@click.option(
    "--glacier-fraction-file",
    type=str,
    help="Path to glacier fraction file (required for --global-regions-output-file)",
)
@click.option(
    "--global-output-file",
    type=str,
    help="Path to global output sea-level file",
)
@click.option(
    "--global-regions-output-file",
    type=str,
    help="Path to global output sea-level file split by glacier (RGI) region",
)
def glaciers(
    scenario,
    refyear_start,
    refyear_end,
    start_year,
    end_year,
    tlm_flag,
    pipeline_id,
    climate_data_file,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    use_gmip,
    glacier_fraction_file,
    global_output_file,
    global_regions_output_file,
):
    """Project the glacier contribution using the IPCC AR5 approach."""
    click.echo("Hello from ipccar5-glaciers!")
    run_glaciers(
        scenario=scenario,
        climate_data_file=climate_data_file,
        refyear_start=refyear_start,
        refyear_end=refyear_end,
        start_year=start_year,
        end_year=end_year,
        use_gmip=use_gmip,
        rng_seed=rng_seed,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nmsamps=nmsamps,
        ntsamps=ntsamps,
        nsamps=nsamps,
        pipeline_id=pipeline_id,
        global_output_file=global_output_file,
        glacier_fraction_file=glacier_fraction_file,
        global_regions_output_file=global_regions_output_file,
    )


@main.command()
@click.option(
    "--scenario",
    type=str,
    help="Scenario",
)
@click.option(
    "--refyear-start",
    default=1986,
    show_default=True,
    type=int,
    help="Start year for reference period",
)
@click.option(
    "--refyear-end",
    default=2005,
    show_default=True,
    type=int,
    help="End year for reference period",
)
@click.option(
    "--start-year",  # this is same as baseyear
    default=2005,  # may want this to be 2006?
    show_default=True,
    type=int,
    help="Year from which to start integrating temperature",
)
@click.option(
    "--tlm-flag",
    default=1,
    show_default=True,
    type=int,
    help="Use the two-layer model data, 1=yes",
)
@click.option(
    "--pipeline-id", type=str, help="Unique identifier for this instance of the module"
)
@click.option(
    "--climate-data-file",
    type=str,
    help="NetCDF4/HDF5 file containing surface temperature data (this should be a fair output)",
    required=True,
)
@click.option(
    "--rng-seed",
    default=1234,
    show_default=True,
    type=int,
    help="Seed value for random number generator",
)
@click.option(
    "--pyear-start",
    default=2020,
    show_default=True,
    type=int,
    help="Projection start year",
)
@click.option(
    "--pyear-end",
    default=2150,
    show_default=True,
    type=int,
    help="Projection end year",
)
@click.option(
    "--pyear-step",
    default=10,
    show_default=True,
    type=int,
    help="Projection year step",
)
@click.option(
    "--nmsamps",
    default=1000,
    show_default=True,
    required=False,
    type=int,
    help="Number of method samples to generate",
)
@click.option(
    "--ntsamps",
    default=450,
    show_default=True,
    required=False,
    type=int,
    help="Number of climate samples to generate",
)
@click.option(
    "--nsamps",
    required=False,
    type=int,
    help="Total number of samples to generate (replaces 'nmsamps' and 'ntsamps' if provided)",
)
@click.option(
    "--icesheet-fraction-file",
    type=str,
    help="Path to icesheet fraction file",
)
@click.option(
    "--global-gis-output-file",
    type=str,
    help="Path to global GIS output sea-level file",
)
@click.option(
    "--global-ais-output-file",
    type=str,
    help="Path to global AIS output sea-level file",
)
@click.option(
    "--global-wais-output-file",
    type=str,
    help="Path to global WAIS output sea-level file",
)
@click.option(
    "--global-eais-output-file",
    type=str,
    help="Path to global EAIS output sea-level file",
)
def icesheets(
    scenario,
    start_year,
    tlm_flag,
    pipeline_id,
    climate_data_file,
    refyear_start,
    refyear_end,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    icesheet_fraction_file,
    global_gis_output_file,
    global_ais_output_file,
    global_wais_output_file,
    global_eais_output_file,
):
    """Project the GIS and AIS contributions using the IPCC AR5 approach."""
    click.echo("Hello from the ipccar5-icesheets!")
    run_icesheets(
        scenario=scenario,
        climate_data_file=climate_data_file,
        icesheet_fraction_file=icesheet_fraction_file,
        refyear_start=refyear_start,
        refyear_end=refyear_end,
        start_year=start_year,
        rng_seed=rng_seed,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nmsamps=nmsamps,
        ntsamps=ntsamps,
        nsamps=nsamps,
        pipeline_id=pipeline_id,
        global_gis_output_file=global_gis_output_file,
        global_ais_output_file=global_ais_output_file,
        global_wais_output_file=global_wais_output_file,
        global_eais_output_file=global_eais_output_file,
    )
