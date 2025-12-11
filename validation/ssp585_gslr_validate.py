"""
ssp585_gslr_validate.py 

Read outputs from corresponding FACTS v1, v2 runs of ipccar5-glaciers module and ensure that outputs match.

v2 results were generated with:
uv run ipccar5 glaciers \
--climate-fname /Users/emmamarshall/Desktop/facts_work/facts_v1/facts/experiments/ar5.ssp585/output/ar5.ssp585.temperature.fair.temperature_climate.nc \
--glacier-fraction-file /Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/input/glacier_fraction.txt \
--scenario 'ssp585' \
--nsamps 500 \
--tlm-flag 1 \
--use-gmip 2 \
--refyear-start 1986 \
--refyear-end 2005 \
--start-year 2005 \
--pyear-start 2020 \
--pyear-end 2150 \
--pyear-step 10 \
--global-output-file /Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/output_1210/glaciers_gslr.nc \
--location-file /Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/input/location.lst \
--fingerprint-dir /Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/input/FPRINT \
--local-output-file /Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/output_1210/glaciers_lslr.nc

v1 results are generated from facts/experiments/ar5.ssp585/ 
"""
import xarray as xr

#hardcoded paths
f2_gslr_file = "/Users/emmamarshall/Desktop/facts_work/facts_v2/ipccar5/data/output_1210/glaciers_gslr.nc"
f1_gslr_file = "/Users/emmamarshall/Desktop/facts_work/facts_v1/facts/experiments/ar5.ssp585/output/ar5.ssp585.ar5glaciers.ipccar5.glaciers_globalsl.nc"

#validation params
RTOL = 1e-5 
ATOL = 1e-8

def load_dataset(path):
    return xr.open_dataset(path)

def validate_gslr(v1_ds, v2_ds, rtol=RTOL, atol=ATOL):
    xr.testing.assert_allclose(
        v2_ds['sea_level_change'],
        v1_ds['sea_level_change'],
        rtol=rtol,
        atol=atol
    )

def main():
    f2_gslr_ds = load_dataset(f2_gslr_file)
    f1_gslr_ds = load_dataset(f1_gslr_file)
    print('data loaded. Validating...')
    try:
        validate_gslr(f1_gslr_ds, f2_gslr_ds)
        print('Validation successful: datasets match within tolerances.')
    except AssertionError as e:
        print('Validation failed: datasets do not match within tolerances.')
        print(e)

if __name__ == "__main__":
    main()

