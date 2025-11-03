import click

from ipccar5.ipccar5_glaciers_preprocess import ar5_preprocess_glaciers
from ipccar5.ipccar5_glaciers_fit import ar5_fit_glaciers
from ipccar5.ipccar5_glaciers_project import ar5_project_glaciers
from ipccar5.ipccar5_glaciers_postprocess import ar5_postprocess_glaciers


@click.command()
@click.option(
    "--scenario",
    type=str,
    # default="ssp585",
    # show_default=True,
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
    "--end-year",
    default=2151,  # 2301,
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
    "--climate-fname",
    type=str,
    help="NetCDF4/HDF5 file containing surface temperature data (this should be a fair output)",
    # required=True,
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
    help="Path to glacier fraction file",
)
@click.option(
    "--global-output-sl-file",
    type=str,
    help="Path to global output sea-level file",
)
@click.option(
    "--climate-means-fname",
    type=str,
    help="Path to climate data means file (if tlm_data=0)",
)
@click.option(
    "--climate-sds-fname",
    type=str,
    help="Path to climate data standard deviations file (if tlm_data=0)",
)
@click.option(
    "--location-file",
    help="File that contains name, id, lat, and lon of points for localization",
)
@click.option(
    "--chunksize",
    help="Number of locations to process at a time",
    type=int,
    default=20,
)
@click.option(
    "--fingerprint-dir", type=str, help="Path to fingerprint directory", required=True
)
@click.option(
    "--local-output-sl-file",
    type=str,
    help="Path to local output sea-level file",
)
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass


def glaciers(
    scenario,
    refyear_start,
    refyear_end,
    start_year,
    end_year,
    tlm_flag,
    pipeline_id,
    climate_fname,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    use_gmip,
    glacier_fraction_file,
    climate_means_fname,
    climate_sds_fname,
    global_output_sl_file,
    location_file,
    chunksize,
    fingerprint_dir,
    local_output_sl_file,
):
    click.echo("Hello from ipccar5!")

    if climate_fname:
        click.echo(f"Using climate data file: {climate_fname}")
        preprocess_dict = ar5_preprocess_glaciers(
            scenario,
            refyear_start,
            refyear_end,
            start_year,
            end_year,
            tlm_flag,
            pipeline_id,
            climate_fname=climate_fname,
        )
    elif climate_means_fname and climate_sds_fname:
        click.echo("This program only supports FAIR climate data files.")
        raise ValueError(
            "Please provide a FAIR climate data file using --climate-fname."
        )

    fit_dict = ar5_fit_glaciers(
        start_year=start_year, use_gmip=use_gmip, pipeline_id=pipeline_id
    )

    project_dict = ar5_project_glaciers(
        preprocess_dict=preprocess_dict,
        fit_dict=fit_dict,
        rng_seed=rng_seed,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nmsamps=nmsamps,
        ntsamps=ntsamps,
        nsamps=nsamps,
        pipeline_id=pipeline_id,
        glacier_fraction_file=glacier_fraction_file,
        global_output_sl_file=global_output_sl_file,
    )

    ar5_postprocess_glaciers(
        locationfile=location_file,
        chunksize=chunksize,
        pipeline_id=pipeline_id,
        project_dict=project_dict,
        preprocess_dict=preprocess_dict,
        fingerprint_dir=fingerprint_dir,
        local_output_sl_file=local_output_sl_file,
    )
