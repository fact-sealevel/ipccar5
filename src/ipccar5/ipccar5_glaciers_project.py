# GMSLR projection program used for IPCC WG1 AR5
# Translated from IDL to Python 2.7 by Jonathan Gregory 23.10.19

import numpy as np
import argparse
import time
import re
import xarray as xr


class ProjectionError(Exception):
    pass


def project_glacier1(it, factor, exponent):
    # Return projection of glacier contribution by one glacier method
    scale = 1e-3  # mm to m
    it[it < 0] = 0.0
    return scale * factor * (it**exponent)


def ar5_project_glaciers(
    preprocess_dict,
    fit_dict,
    rng_seed,
    pyear_start,
    pyear_end,
    pyear_step,
    nmsamps,
    ntsamps,
    nsamps,
    pipeline_id,
    glacier_fraction_file,
    global_output_file,
):
    # Define the target years
    # Creates an array from pyear_start to pyear_end in steps of pyear_steps to serve as the projection window
    targyears = np.arange(pyear_start, pyear_end + 1, pyear_step)

    # Load the preprocessed data
    # data_file = "{}_data.pkl".format(pipeline_id)
    # try:
    #    f = open(data_file, "rb")
    # except:
    #    print("Cannot open data file\n")

    # NEEDS TO BE FIXED TO USE SAMPLES RATHER THAN MEAN AND SD
    # Extract the data variables
    # my_data = pickle.load(f)
    # f.close()

    inttemp_mean = preprocess_dict["inttemp_mean"]
    inttemp_sd = preprocess_dict["inttemp_sd"]
    data_years = preprocess_dict["data_years"]
    baseyear = preprocess_dict["startyr"]
    scenario = preprocess_dict["scenario"]
    # temp_samples = preprocess_dict["temp_samples"]  # Added for Fair Correlation  Issue
    inttemp_samples = preprocess_dict[
        "inttemp_samples"
    ]  # Added for Fair Correlation  Issue

    # Load the fit data
    # data_file = "{}_fit.pkl".format(pipeline_id)
    # try:
    #    f = open(data_file, "rb")
    # except:
    #    print("Cannot open fit file\n")

    # Extract the fit variables
    # my_fit = pickle.load(f)
    # f.close()

    dmz = fit_dict["dmz"]
    # cvgl = fit_dict["cvgl"]
    glmass = fit_dict["glmass"]
    glparm = fit_dict["glparm"]

    # Subset the data to the target years
    year_idx = np.isin(data_years, targyears)
    inttemp_sd = inttemp_sd[year_idx]
    data_years = data_years[year_idx]
    inttemp_mean = inttemp_mean[year_idx]

    # Set the seed for the random number generator
    rng = np.random.default_rng(rng_seed)

    # Divide "nsamps" into "nmsamps" and "ntsamps" if necessary
    if nsamps is None:
        nsamps = nmsamps * ntsamps
    else:
        temp = int(np.ceil(np.sqrt(nsamps)))
        nmsamps = int(temp - (temp % len(glparm)))
        ntsamps = int(np.ceil(nsamps / nmsamps))

    # Generate perfectly correlated samples
    # For each quantity, mean + standard deviation * normal random number
    # z = rng.standard_normal(ntsamps)[:, np.newaxis]
    # zit = inttemp_mean + (inttemp_sd * z)

    # z = temp_samples
    # zit = inttemp_samples

    # Number of realizations
    nr = nmsamps

    # Number of years in the data record (default is 296)
    nyr = len(data_years)

    # number of glacier methods (current default is 7)
    ngl = len(glparm)

    # Stop if the number of realizations requested cannot evenly distributed over methods
    if nr % ngl:
        raise ProjectionError(
            "number of realisations "
            + "must be a multiple of number of glacier methods"
        )

    # number of realisations per glacier method
    # nrpergl = nr / ngl

    # Generate samples for methodologies
    # r = rng.standard_normal(nr)

    # Initialize the data structure to hold the glacier samples
    total_glac_samps = np.full((nsamps, nyr), np.nan)

    # Takes the data years and divides by the number of glacier methods to evenly distribute methods across
    # temp_samples and inttemp_samples
    samps_per_model = np.array([nsamps // ngl for x in range(ngl)])
    remainder_samps = nsamps % ngl
    samps_per_model[rng.choice(ngl, size=remainder_samps, replace=False)] += 1

    # Creates a list of integers for the random method selection
    time_series_idx = np.arange(nsamps)

    for method_idx in range(len(samps_per_model)):
        # Applies the method index to the select the appropriate glacier method
        gmethod = glparm[method_idx]

        # Randomly pulls time-series indices from the selection pool corresponding to samps_per_model for this method
        rnd_sample_idx = rng.choice(
            time_series_idx, size=samps_per_model[method_idx], replace=False
        )

        # Removes the selected time-series indices from the selection pool for the next loop
        time_series_idx = np.setdiff1d(time_series_idx, rnd_sample_idx)

        # glacier projection for this method using the mean temperature timeseries
        mgl = project_glacier1(inttemp_mean, gmethod["factor"], gmethod["exponent"])

        for sample_idx in rnd_sample_idx:
            # Project time series of total glacier loss based on integrated temperature time series
            zgl = project_glacier1(
                inttemp_samples[sample_idx][year_idx],
                gmethod["factor"],
                gmethod["exponent"],
            )

            # add normally distributed methodological uncertainty based on ensemble-mean integrated temperature
            zgl = zgl + (mgl * rng.standard_normal(1) * gmethod["cvgl"])

            total_glac_samps[sample_idx, :] = zgl

    total_glac_samps += dmz
    total_glac_samps[total_glac_samps > glmass] = glmass
    total_glac_samps = total_glac_samps * 1000

    ds = xr.Dataset(
        data_vars={
            "sea_level_change": (
                ("samples", "years", "locations"),
                total_glac_samps[:, :, np.newaxis],
                {"units": "mm"},
            ),
            "lat": (
                ("locations",),
                np.array([np.float32(np.inf)], dtype=np.float32),
            ),
            "lon": (
                ("locations",),
                np.array([np.float32(np.inf)], dtype=np.float32),
            ),
        },
        coords={
            "samples": np.arange(nsamps),
            "years": data_years,
            "locations": [-1],
        },
        attrs={
            "description": "Global SLR contribution from glaciers and ice caps according to AR5 workflow",
            "history": "Created " + time.ctime(time.time()),
            "source": "FACTS: {0}".format(pipeline_id),
            "baseyear": baseyear,
            "scenario": scenario,
        },
    )

    ds.to_netcdf(
        global_output_file,
        mode="w",
        format="NETCDF4",
        engine="netcdf4",
        encoding={"sea_level_change": {"zlib": True, "complevel": 4}},
    )

    # Load in the glacier fraction data-------------------------------------------
    # Note: There's were derived from the Kopp14 workflow.  Apparently, glacier region 4
    # is not represented and region 7 is represented twice.  I'm not sure why, but
    # it's consistent with the K14 workflow, so it's been carried over to this.

    # Initialize the data structures
    glac_frac = []
    glac_region_names = []

    # Open the glacier fraction file
    # glac_frac_file = os.path.join(os.path.dirname(__file__), "glacier_fraction.txt")
    with open(glacier_fraction_file, "r") as fp:
        # Get the fraction years from the header line
        header_items = re.split(",\s*", fp.readline())
        glac_frac_years = np.array([int(x) for x in header_items[1:]])

        # Read in the rest of the files
        for line in fp:
            line = line.rstrip()

            # Split the line into the region name and the fractions then append to data structures
            line_parts = re.split(",\s*", line)
            glac_region_names.append(line_parts[0])
            glac_frac.append([float(x) for x in line_parts[1:]])

    # Convert the fraction data structure into a numpy array
    glac_frac = np.array(glac_frac)

    # Subset the fraction data to the years of interest
    year_idx = np.isin(glac_frac_years, data_years)
    glac_frac = glac_frac[:, year_idx]

    # Reshape the samples and fraction data structures for broadcasting
    glac_frac = glac_frac[np.newaxis, :, :]

    # Apply the regional fractions to the global projections

    total_glac_samps = total_glac_samps[:, :, np.newaxis]
    total_glac_samps = np.transpose(total_glac_samps, (0, 2, 1))

    gicsamps = total_glac_samps * glac_frac

    # print(gicsamps.shape)

    # Save the global glacier and ice caps projections to a pickle
    output = {
        "gicsamps": gicsamps,
        "glac_region_names": glac_region_names,
        "data_years": data_years,
    }

    return output


if __name__ == "__main__":
    # Initialize the command-line argument parser
    parser = argparse.ArgumentParser(
        description="Run the glacier projection stage for the AR5 SLR projection workflow",
        epilog="Note: This is meant to be run as part of the Framework for the Assessment of Changes To Sea-level (FACTS)",
    )

    # Define the command line arguments to be expected
    parser.add_argument(
        "--nmsamps",
        help="Number of method samples to generate [default=1000]",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "--ntsamps",
        help="Number of climate samples to generate [default=450]",
        default=450,
        type=int,
    )
    parser.add_argument(
        "--nsamps",
        help="Total number of samples to generate (replaces 'nmsamps' and 'ntsamps' if provided)",
        default=None,
        type=int,
    )
    parser.add_argument(
        "--pyear_start",
        help="Projection year start [default=2020]",
        default=2020,
        type=int,
    )
    parser.add_argument(
        "--pyear_end", help="Projection year end [default=2100]", default=2100, type=int
    )
    parser.add_argument(
        "--pyear_step", help="Projection year step [default=10]", default=10, type=int
    )
    parser.add_argument(
        "--seed",
        help="Seed value for random number generator [default=1234]",
        default=1234,
        type=int,
    )
    parser.add_argument(
        "--pipeline_id", help="Unique identifier for this instance of the module"
    )

    # Parse the arguments
    args = parser.parse_args()

    # Run the projection process on the files specified from the command line argument
    ar5_project_glaciers(
        args.seed,
        args.pyear_start,
        args.pyear_end,
        args.pyear_step,
        args.nmsamps,
        args.ntsamps,
        args.nsamps,
        args.pipeline_id,
    )

    exit()
