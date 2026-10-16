"""
Core 'business logic'.

GMSLR projection program used for IPCC WG1 AR5.
Translated from IDL to Python 2.7 by Jonathan Gregory 23.10.19.
Adapted for use in FACTS by Gregory Garner 20 November 2019.

Nothing in this module reads or writes files; see ipccar5.io for that.
"""

from dataclasses import dataclass
import logging

import numpy as np

logger = logging.getLogger(__name__)


class ProjectionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


@dataclass
class ClimateData:
    """Raw surface temperature ensemble from FaIR (or similar) output."""

    samples: np.ndarray  # [years, samples]
    years: np.ndarray


@dataclass
class TemperatureData:
    """Preprocessed temperature anomalies and their time integrals."""

    temp_samples: np.ndarray  # [samples, years]
    temp_mean: np.ndarray
    temp_sd: np.ndarray
    inttemp_samples: np.ndarray  # [samples, years]
    inttemp_mean: np.ndarray
    inttemp_sd: np.ndarray
    data_years: np.ndarray
    startyr: int
    scenario: str


@dataclass
class RegionalFractions:
    """Time-varying fractions used to split a global contribution into regions."""

    region_names: list[str]
    years: np.ndarray
    fractions: np.ndarray  # [regions, years]


@dataclass
class GlacierFit:
    dmz: float
    cvgl: float
    glmass: float
    glparm: list[dict]


@dataclass
class IcesheetFit:
    dant: float
    dgreen: float
    fgreendyn: float
    mSLEoGt: float
    dtgreen: float
    fnlogsd: float
    febound: list[float]
    pcoK: list[float]
    KoKg: list[float]
    smax: float
    gdyn_finalrange: list[float]
    adyn_finalrange: list[float]
    adyn_startratemean: float
    adyn_startratepm: float


@dataclass
class IcesheetProjection:
    """Global ice sheet projections in mm, each [samples, years]."""

    gis: np.ndarray
    ais: np.ndarray
    wais: np.ndarray
    eais: np.ndarray
    years: np.ndarray


# ---------------------------------------------------------------------------
# Preprocess (shared by glaciers and icesheets)
# ---------------------------------------------------------------------------


def check_scenario_match(
    requested: str, found: str | None, source: str = "the climate data"
) -> None:
    """
    Raise ValueError unless the scenario found in the input data matches the
    requested scenario. found is None when the input data has no scenario.
    """
    if found is None:
        raise ValueError(
            f"{source} has no scenario, so it cannot be checked against the "
            f"requested scenario '{requested}'."
        )
    if found != requested:
        raise ValueError(
            f"Scenario mismatch: requested '{requested}' but {source} contains '{found}'."
        )


def preprocess(
    climate: ClimateData,
    scenario: str,
    refyear_start: int,
    refyear_end: int,
    start_year: int,
    end_year: int,
) -> TemperatureData:
    """Reference, filter and integrate the temperature ensemble."""
    samps = climate.samples
    years = climate.years

    # Calculate the reference period values (mean between refyear_start and refyear_end inclusive)
    year_idx = np.flatnonzero(
        np.logical_and(years >= refyear_start, years <= refyear_end)
    )
    ref_vals = np.mean(samps[year_idx, :], axis=0)[None, :]
    samps = samps - ref_vals

    temp_samples, data_years = filter_temperature(
        samps.T, years, filter_years=np.arange(start_year, end_year)
    )

    # Find the mean and sd of the ensemble
    temp_mean = np.nanmean(temp_samples, axis=0)
    temp_sd = np.nanstd(temp_samples, axis=0)

    # Integrate temperature to obtain K yr at ends of calendar years
    # Note - The original code I believe performs a cumulative sum of the standard
    # deviations, which is not correct.  Below I provide a fix to that bug as well as
    # a replication of the bug for diagnostic purposes.
    # Note - JG makes an assumption here so that standard deviations are able to be summed
    # over time.
    inttemp_mean = np.cumsum(temp_mean)
    # inttemp_sd = np.sqrt(np.cumsum(temp_sd**2))  # Fix the bug
    inttemp_sd = np.cumsum(temp_sd)  # Replicate the bug
    inttemp_samples = np.cumsum(temp_samples, axis=1)

    logger.info("Preprocess complete.")
    return TemperatureData(
        temp_samples=temp_samples,
        temp_mean=temp_mean,
        temp_sd=temp_sd,
        inttemp_samples=inttemp_samples,
        inttemp_mean=inttemp_mean,
        inttemp_sd=inttemp_sd,
        data_years=data_years,
        startyr=start_year,
        scenario=scenario,
    )


def filter_temperature(
    samps: np.ndarray,
    years: np.ndarray,
    filter_years=None,
    tmin=-np.inf,
    tmax=np.inf,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Filter temperature trajectories [samples, years] for samples whose maximum
    temperature falls between tmin and tmax, optionally subsetting years.
    """
    if filter_years is not None:
        year_idx = np.isin(years, filter_years)
        samps = samps[:, year_idx]
        years = years[year_idx]

    samps_max = np.nanmax(samps, axis=1)
    match_idx = np.logical_and(samps_max >= tmin, samps_max <= tmax)

    if not np.any(match_idx):
        raise ValueError(
            "Cannot find samples that match the target window. min = {}, max = {}".format(
                tmin, tmax
            )
        )

    return samps[match_idx, :], years


# ---------------------------------------------------------------------------
# Glaciers
# ---------------------------------------------------------------------------


def fit_glaciers(start_year: int, use_gmip: int) -> GlacierFit:
    # mm yr-1 in Marzeion's CMIP5 ensemble mean for AR5 ref period
    dmzdtref = 0.95

    # m from glacier at start wrt AR5 ref period
    dmz = dmzdtref * (start_year - 1996) * 1e-3

    # random methodological error
    cvgl = 0.20

    # initial glacier mass, used to set a limit, from Tab 4.2
    glmass = 412.0 - 96.3
    glmass = 1e-3 * glmass  # m SLE

    # Calibrated parameters for glacier methods
    # 0 = Original AR5 calibration, 1 = GMIP calibration, 2 = GMIP2 calibration
    if use_gmip == 2:
        glparm = [
            dict(name="GLIMB", factor=2.30, exponent=0.753, cvgl=0.209),
            dict(name="GloGEM", factor=2.77, exponent=0.793, cvgl=0.171),
            dict(name="JULES", factor=3.57, exponent=0.646, cvgl=0.197),
            dict(name="Mar-12", factor=3.31, exponent=0.727, cvgl=0.152),
            dict(name="OGGM", factor=2.90, exponent=0.791, cvgl=0.177),
            dict(name="RAD2014", factor=3.13, exponent=0.788, cvgl=0.147),
            dict(name="WAL2001", factor=1.44, exponent=0.852, cvgl=0.208),
        ]
    elif use_gmip == 1:
        glparm = [
            dict(name="SLA2012", factor=3.39, exponent=0.722, cvgl=0.15),
            dict(name="MAR2012", factor=4.35, exponent=0.658, cvgl=0.13),
            dict(name="GIE2013", factor=3.57, exponent=0.665, cvgl=0.13),
            dict(name="RAD2014", factor=6.21, exponent=0.648, cvgl=0.17),
            dict(name="GloGEM", factor=2.88, exponent=0.753, cvgl=0.13),
        ]
    else:
        glparm = [
            dict(name="Marzeion", factor=4.96, exponent=0.685, cvgl=0.20),
            dict(name="Radic", factor=5.45, exponent=0.676, cvgl=0.20),
            dict(name="Slangen", factor=3.44, exponent=0.742, cvgl=0.20),
            dict(name="Giesen", factor=3.02, exponent=0.733, cvgl=0.20),
        ]

    return GlacierFit(dmz=dmz, cvgl=cvgl, glmass=glmass, glparm=glparm)


def project_glacier1(it, factor, exponent):
    # Return projection of glacier contribution by one glacier method
    scale = 1e-3  # mm to m
    it[it < 0] = 0.0
    return scale * factor * (it**exponent)


def project_glaciers(
    temperature: TemperatureData,
    fit: GlacierFit,
    rng_seed: int,
    targyears: np.ndarray,
    nmsamps: int,
    ntsamps: int,
    nsamps: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Project the global glacier contribution.

    Returns (samples [samples, years] in mm, years).
    """
    glmass = fit.glmass
    glparm = fit.glparm

    # Subset the data to the target years
    data_years = temperature.data_years
    year_idx = np.isin(data_years, targyears)
    inttemp_mean = temperature.inttemp_mean[year_idx]
    data_years = data_years[year_idx]
    inttemp_samples = temperature.inttemp_samples

    rng = np.random.default_rng(rng_seed)

    # Divide "nsamps" into "nmsamps" and "ntsamps" if necessary
    if nsamps is None:
        nsamps = nmsamps * ntsamps
    else:
        temp = int(np.ceil(np.sqrt(nsamps)))
        nmsamps = int(temp - (temp % len(glparm)))
        ntsamps = int(np.ceil(nsamps / nmsamps))

    # These draws are unused but advance the RNG state, so they are kept to
    # reproduce FACTS v1 results.
    rng.standard_normal(ntsamps)

    # Number of realizations
    nr = nmsamps

    # Number of years in the data record
    nyr = len(data_years)

    # number of glacier methods
    ngl = len(glparm)

    # Stop if the number of realizations requested cannot evenly distributed over methods
    if nr % ngl:
        raise ProjectionError(
            "number of realisations must be a multiple of number of glacier methods"
        )

    rng.standard_normal(nr)

    total_glac_samps = np.full((nsamps, nyr), np.nan)

    # Evenly distribute glacier methods across the temperature samples
    samps_per_model = np.array([nsamps // ngl for _ in range(ngl)])
    remainder_samps = nsamps % ngl
    samps_per_model[rng.choice(ngl, size=remainder_samps, replace=False)] += 1

    # Selection pool for the random method assignment
    time_series_idx = np.arange(nsamps)

    for method_idx in range(len(samps_per_model)):
        gmethod = glparm[method_idx]

        # Randomly pull time-series indices for this method, then remove them from the pool
        rnd_sample_idx = rng.choice(
            time_series_idx, size=samps_per_model[method_idx], replace=False
        )
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

    total_glac_samps += fit.dmz
    total_glac_samps[total_glac_samps > glmass] = glmass
    total_glac_samps = total_glac_samps * 1000

    return total_glac_samps, data_years


# Glacier regions are the RGI first-order regions used by Kopp14 (Marzeion et al.
# 2012), listed in the row order of glacier_fraction.txt as
# (RGI id, region name, fingerprint id). Rows are sorted by fingerprint id, not by
# region. RGI 14 and 15 share fingerprint glac7; we assume they appear in RGI order
# (i.e. the file was produced by a stable sort). RGI 19 (Antarctic periphery) is
# excluded, as in Kopp14.
#
# RGI ids and region names come from the IceID and IceName columns of Kopp14's
# fingerprint_region_map.csv, matched to the fraction file rows on its FPID column.
# The CSV is in kopp14_glaciers_preprocess_data.tgz at
# https://zenodo.org/records/7478192.
GLACIER_REGIONS = (
    (5, "GreenlandGIC", "gis"),
    (6, "Iceland", "glac1"),
    (7, "Svalbard", "glac2"),
    (9, "RussianArctic", "glac3"),
    (10, "NorthAsia", "glac5"),
    (13, "CentralAsia", "glac6"),
    (14, "SouthAsiaWest", "glac7"),
    (15, "SouthAsiaEast", "glac7"),
    (12, "Caucasus", "glac8"),
    (11, "CentralEurope", "glac9"),
    (8, "Scandinavia", "glac10"),
    (1, "Alaska", "glac11"),
    (2, "WesternCanUS", "glac12"),
    (4, "ArcticCanadaSouth", "glac13"),
    (3, "ArcticCanadaNorth", "glac14"),
    (16, "LowLatitudes", "glac15"),
    (17, "SouthernAndes", "glac16"),
    (18, "NewZealand", "glac17"),
)


def split_glacier_regions(
    samps: np.ndarray, fractions: RegionalFractions, years: np.ndarray
) -> np.ndarray:
    """
    Split [samples, years] global glacier samples into [samples, regions, years],
    with regions in GLACIER_REGIONS order.
    """
    expected = [fpid for _, _, fpid in GLACIER_REGIONS]
    if fractions.region_names != expected:
        raise ValueError(
            "Glacier fraction file regions do not match the expected fingerprint ids. "
            f"Expected {expected}, got {fractions.region_names}."
        )
    missing_years = np.setdiff1d(years, fractions.years)
    if missing_years.size:
        raise ValueError(
            f"Glacier fraction file is missing projection years: {missing_years}"
        )
    return apply_regional_fractions(samps, fractions, years)


# ---------------------------------------------------------------------------
# Icesheets
# ---------------------------------------------------------------------------


def fit_icesheets(scenario: str) -> IcesheetFit:
    # Greenland Dynamic
    if scenario in ["rcp85", "ssp585"]:
        gdyn_finalrange = [0.020, 0.085]
    else:
        gdyn_finalrange = [0.014, 0.063]

    return IcesheetFit(
        # m SLE from Antarctica during 1996 to 2005 according to AR5 chapter 4
        dant=(2.37 + 0.13) * 1e-3,
        # m SLE from Greenland during 1996 to 2005 according to AR5 chapter 4
        dgreen=(3.21 - 0.30) * 1e-3,
        # Fraction of SLE from Greenland during 1996 to 2005 assumed to result from
        # rapid dynamical change, with the remainder assumed to result from SMB change
        fgreendyn=0.5,
        # Conversion factor for Gt to m SLE
        mSLEoGt=1e12 / 3.61e14 * 1e-3,
        # Greenland SMB
        dtgreen=-0.146,  # Delta_T of Greenland ref period wrt AR5 ref period
        fnlogsd=0.4,  # random methodological error of the log factor
        febound=[1, 1.15],  # bounds of uniform pdf of SMB elevation feedback factor
        # Antarctic SMB, [mean, SD]
        pcoK=[5.1, 1.5],  # % change in Ant SMB per K of warming from G&H06
        KoKg=[1.1, 0.2],  # ratio of Antarctic warming to global warming from G&H06
        smax=0.35,  # max value of S in 13.SM.1.5
        gdyn_finalrange=gdyn_finalrange,
        # Antarctic Dynamic
        # For SMB+dyn during 2005-2010 Table 4.6 gives 0.41+-0.24 mm yr-1 (5-95% range)
        # For dyn at 2100 Chapter 13 gives [-20,185] mm for all scenarios
        adyn_finalrange=[-0.020, 0.185],
        adyn_startratemean=0.41,
        adyn_startratepm=0.20,
    )


def fettweis(ztgreen, mSLEoGt):
    # Greenland SMB in m yr-1 SLE from global mean temperature anomaly
    # using Eq 2 of Fettweis et al. (2013)
    return (71.5 * ztgreen + 20.4 * (ztgreen**2) + 2.8 * (ztgreen**3)) * mSLEoGt


def project_greensmb(zt, fit: IcesheetFit, nt, rng):
    # random log-normal factor
    fn = np.exp(rng.standard_normal(nt) * fit.fnlogsd)

    # elevation feedback factor
    fe = rng.choice(nt) * (fit.febound[1] - fit.febound[0]) + fit.febound[0]
    ff = fn * fe

    ztgreen = zt - fit.dtgreen
    greensmbrate = fettweis(ztgreen, fit.mSLEoGt)[:, :] * ff[:, np.newaxis]

    greensmb = np.cumsum(greensmbrate, axis=1)[:]
    greensmb += (1 - fit.fgreendyn) * fit.dgreen
    return greensmb


def project_antsmb(zit, fit: IcesheetFit, nr, nt, rng, fraction=None):
    # Return projection of Antarctic SMB contribution
    # zit -- ensemble of time-integral temperature anomaly timeseries
    # fraction -- array-like, random numbers for the SMB-dynamic feedback

    # Generate a distribution of products of the above two factors
    pcoKg = (fit.pcoK[0] + rng.standard_normal([nr, nt, 1]) * fit.pcoK[1]) * (
        fit.KoKg[0] + rng.standard_normal([nr, nt, 1]) * fit.KoKg[1]
    )
    meansmb = 1923  # model-mean time-mean 1979-2010 Gt yr-1 from 13.3.3.2
    moaoKg = (
        -pcoKg * 1e-2 * meansmb * fit.mSLEoGt
    )  # m yr-1 of SLE per K of global warming

    if fraction is None:
        fraction = rng.random([nr, nt, 1])
    elif fraction.size != nr * nt:
        raise ProjectionError("Project antsmb: fraction is the wrong size")
    else:
        fraction.shape = (nr, nt, 1)

    ainterfactor = 1 - fraction * fit.smax

    return moaoKg * ainterfactor * zit.reshape(1, nt, -1)


def project_greendyn(fit: IcesheetFit, nm, nt, rng, data_years):
    gdyn_startratemean = 0.63 * fit.fgreendyn
    gdyn_startratepm = 0.17 * fit.fgreendyn

    gdyn_timeprojection = time_projection(
        gdyn_startratemean,
        gdyn_startratepm,
        fit.gdyn_finalrange,
        nm,
        nt,
        data_years,
        rng,
    )

    return gdyn_timeprojection + fit.fgreendyn * fit.dgreen


def project_antdyn(fit: IcesheetFit, nm, nt, data_years, rng, fraction=None):
    adyn_timeprojection = time_projection(
        fit.adyn_startratemean,
        fit.adyn_startratepm,
        fit.adyn_finalrange,
        nm,
        nt,
        data_years,
        rng,
        fraction=fraction,
    )

    return adyn_timeprojection + fit.dant


def time_projection(
    startratemean,
    startratepm,
    finalrange,
    nr,
    nt,
    data_years,
    rng,
    nfinal=1,
    fraction=None,
):
    # Return projection of a quantity which is a quadratic function of time
    # startratemean, startratepm -- rate of GMSLR at the start in mm yr-1, whose
    # likely range is startratemean +- startratepm
    # finalrange -- two-element list giving likely range in m for GMSLR at the end
    # nfinal -- int, optional, number of years at the end over which finalrange is
    # a time-mean; by default 1 => finalrange is the value for the last year
    # fraction -- array-like, optional, random numbers in the range 0 to 1,
    # by default uniformly distributed

    if fraction is None:
        fraction = rng.random([nr, nt, 1])
    elif fraction.size != nr * nt:
        raise ProjectionError("Time Projection: fraction is the wrong size")
    fraction = fraction.reshape(nr, nt, 1)

    # Number of years
    nyr = np.flatnonzero(data_years == 2100)

    # For terms where the rate increases linearly in time t, we can write GMSLR as
    # S(t) = a*t**2 + b*t
    # where a is 0.5*acceleration and b is start rate. Hence
    # a = S/t**2-b/t
    momm = 1e-3  # convert mm yr-1 to m yr-1
    startrate = (startratemean + startratepm * np.array([-1, 1], dtype=float)) * momm
    finalyr = np.arange(nfinal) - nfinal + nyr + 1  # last element ==nyr
    acceleration = (np.array(finalrange, dtype=float) - startrate * finalyr.mean()) / (
        finalyr**2
    ).mean()

    # Elapsed time in years since start
    time = data_years - data_years[0] + 1

    # Calculate two-element list containing fields of the minimum and maximum
    # timeseries of projections, then calculate random ensemble within envelope
    bounds = [
        float(acceleration[i]) * (time**2) + float(startrate[i]) * time for i in [0, 1]
    ]

    return bounds[0] * (1 - fraction) + bounds[1] * fraction


def extrapolate_rate(sample, targyears, cyear_start, cyear_end):
    # If only one of the constant rate years is provided, imply the other
    if cyear_start and not cyear_end:
        cyear_end = cyear_start + 20
    if cyear_end and not cyear_start:
        cyear_start = cyear_end - 20

    # Find the start and end projection values for the rate calculation
    proj_start = np.interp(cyear_start, targyears, sample)
    proj_end = np.interp(cyear_end, targyears, sample)

    rate = (proj_end - proj_start) / (cyear_end - cyear_start)

    ext_sample = sample
    ext_sample[targyears >= cyear_end] = proj_end + (
        rate * (targyears[targyears >= cyear_end] - cyear_end)
    )
    return ext_sample


def project_icesheets(
    temperature: TemperatureData,
    fit: IcesheetFit,
    antarctic_fractions: RegionalFractions,
    rng_seed: int,
    targyears: np.ndarray,
    cyear_start: int | None,
    cyear_end: int | None,
    nmsamps: int,
    ntsamps: int,
    nsamps: int | None,
) -> IcesheetProjection:
    """Project global GIS and AIS contributions, splitting AIS into WAIS and EAIS."""
    temp_samples = temperature.temp_samples
    inttemp_samples = temperature.inttemp_samples
    data_years = temperature.data_years
    startyr = temperature.startyr

    rng = np.random.default_rng(rng_seed)

    # Divide "nsamps" into "nmsamps" and "ntsamps" if necessary
    if nsamps is None:
        nsamps = nmsamps * ntsamps
    else:
        nmsamps = int(np.ceil(np.sqrt(nsamps)))
        ntsamps = nmsamps

    # This draw is unused but advances the RNG state, so it is kept to
    # reproduce FACTS v1 results.
    rng.standard_normal(ntsamps)

    # correlation between antsmb and antdyn
    fraction = rng.random(nsamps)

    # Project the SMB and Dynamics portions of each ice sheet
    greensmb = project_greensmb(temp_samples, fit, nsamps, rng)
    greendyn = project_greendyn(fit, 1, nsamps, rng, data_years)
    antsmb = project_antsmb(inttemp_samples, fit, 1, nsamps, rng, fraction=fraction)
    antdyn = project_antdyn(fit, 1, nsamps, data_years, rng, fraction=fraction)

    # Center the projections to the baseyear
    baseyear_idx = np.flatnonzero(data_years == startyr)
    if len(baseyear_idx) > 0:
        greensmb = greensmb - greensmb[:, baseyear_idx]
        greendyn = greendyn - greendyn[:, :, baseyear_idx]
        antsmb = antsmb - antsmb[:, :, baseyear_idx]
        antdyn = antdyn - antdyn[:, :, baseyear_idx]

    # Reduce the years to just the target years
    year_idx = np.isin(data_years, targyears)
    data_years = data_years[year_idx]
    greensmb = greensmb[:, year_idx]
    greendyn = greendyn[:, :, year_idx]
    antsmb = antsmb[:, :, year_idx]
    antdyn = antdyn[:, :, year_idx]

    # Flatten the ice sheet samples and convert to mm
    greensmb = greensmb.reshape(-1, greensmb.shape[-1])[:nsamps, :] * 1000.0
    greendyn = greendyn.reshape(-1, greendyn.shape[-1])[:nsamps, :] * 1000.0
    antsmb = antsmb.reshape(-1, antsmb.shape[-1])[:nsamps, :] * 1000.0
    antdyn = antdyn.reshape(-1, antdyn.shape[-1])[:nsamps, :] * 1000.0

    # If the user wants to extrapolate projections based on rates, do so here
    if cyear_start or cyear_end:
        for i in np.arange(nsamps):
            greendyn[i, :] = extrapolate_rate(
                greendyn[i, :], targyears, cyear_start, cyear_end
            )
            antdyn[i, :] = extrapolate_rate(
                antdyn[i, :], targyears, cyear_start, cyear_end
            )

    # Sum up the components
    greennet = greendyn + greensmb
    antnet = antdyn + antsmb

    # Split Antarctica into west and east using the regional fractions
    aissamps = apply_regional_fractions(antnet, antarctic_fractions, data_years)

    return IcesheetProjection(
        gis=greennet,
        ais=antnet,
        wais=aissamps[:, 0, :],
        eais=aissamps[:, 1, :],
        years=data_years,
    )


# ---------------------------------------------------------------------------
# Regionalization (shared)
# ---------------------------------------------------------------------------


def apply_regional_fractions(
    samps: np.ndarray, fractions: RegionalFractions, years: np.ndarray
) -> np.ndarray:
    """Split [samples, years] global samples into [samples, regions, years]."""
    year_idx = np.isin(fractions.years, years)
    frac = fractions.fractions[:, year_idx]
    return samps[:, np.newaxis, :] * frac[np.newaxis, :, :]
