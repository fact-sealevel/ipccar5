# ipccar5

This is an application that repicates the `ipccar5` sub-module of FACTS 1; it implements the glacier projection approach adopted by IPCC AR5 WG1. It was translated from IDL to Python 2.7 by Jonathan Gregory 23.10.19 and adapted for use in FACTS by Gregory Garner 20 November 2019.

See IPCC AR5 WG1 13.SM.1.4 - 13.SM.1.6 for the original implementation. This implementation also includes as options calibration parameters derived from the GlacierMIP and GlacierMIP2 studies as described in AR6 WG1 9.SM.4.5. As described therein:
                          
The glacier contribution is the integral of $fI(t)^ρ$, where $I(t)$ is the time integral of GSAT from 2006 to time t in degrees Celsius year, and the constants f and ρ are calibrated for each glacier model. The spread of the results around this median projection has a coefficient of variation (standard deviation divided by the mean) σ which is determined on a per-model basis. This variation is incorporated by taking for each Monte Carlo sample a normally distributed random number. This number is multiplied by the time-dependent standard deviation and added to the sample. All models are equally weighted.

>[!CAUTION]
> This is a prototype. It is likely to change in breaking ways. It might delete all your data. Don't use it in production.

## Example

### Setup

Clone the repository and create directories to hold input and output data. 
```shell
#git clone git@github.com:fact-sealevel/ipccar5.git
# ^eventually, for now:
git clone --single-branch --branch package git@github.com:e-marshall/ipccar5.git
```

Download input data and setup sub-directories to hold data related to this module:
```shell
mkdir -p ./data/input
#Download input data for glaciers submodule
curl -sL https://zenodo.org/record/7478192/files/ipccar5_glaciers_project_data.tgz | tar -zx -C ./data/input
#Download input data for icesheets submodule
curl -sL https://zenodo.org/record/7478192/files/ipccar5_icesheets_project_data.tgz | tar -zx -C ./data/input
#curl -sL https://zenodo.org/records/6419954/files/modules_data.zip -o modules_data.zip
#unzip modules_data.zip -d ./data/input

# Fingerprint input data for postprocessing step
curl -sL https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz | tar -zx -C ./data/input

echo "New_York	12	40.70	-74.01" > ./data/input/location.lst

# Output projections will appear here
mkdir -p ./data/output
```

Next, create a docker image that will be used to run the application. 
```shell
docker build -t ipccar5 .
```

Create a container based on the image (`docker run --rm`), mount volumes for both the input and output data sub-directories and set the working directory to the location of the app in the container (`-w`). Then, call the application, passing the desired input arguments and making sure that the paths for each input argument are relative to the mounted volumes. Replace the paths for each mounted volume with the location of `data/input/` and `data/output/` on your machine.

>[!IMPORTANT]
> This module **requires** a `climate.nc` file that is the output of the FACTS FAIR module, which is created outside of this prototype. Before running the example, manually move the file into `./data/input` and ensure that the filename matches that passed to `climate-file`. The number of samples (`--nsamps`) drawn in the FAIR run must pass the number of samples specified in this run. 

To run the glaciers sub-module:
```shell
docker run --rm \
-v /path/to/data/input:/mnt/ipccar5_data_in:ro \
-v /path/to/data/input:/mnt/ipccar5_data_out \
ipccar5 glaciers \
--scenario 'ssp585' --nsamps 500 \
--climate-fname /mnt/ipccar5_data_in/temperature_climate.nc \
--glacier-fraction-file /mnt/ipccar5_data_in/glacier_fraction.txt \
--location-file /mnt/ipccar5_data_in/location.lst \
--fingerprint-dir /mnt/ipccar5_data_in/FPRINT \
--global-output-sl-file /mnt/ipccar5_data_out/glaciers_gslr.nc \
--local-output-sl-file /mnt/ipccar5_data_out/glaciers_lslr.nc
```

To run the icesheets sub-module:
```shell
docker run --rm \
-v /path/to/data/input:/mnt/ipccar5_data_in:ro \
-v /path/to/data/input:/mnt/ipccar5_data_out \
ipccar5 icesheets \
--scenario 'ssp585' --nsamps 500 \
--climate-fname /mnt/ipccar5_data_in/temperature_climate.nc \
--icesheet-fraction-file /mnt/ipccar5_data_in/icesheet_fraction.txt \
--global-gis-output-file /mnt/ipccar5_data_out/gis_gslr.nc \
--global-ais-output-file  /mnt/ipccar5_data_out/ais_gslr.nc \
--global-wais-output-file /mnt/ipccar5_data_out/wais_gslr.nc \
--global-eais-output-file /mnt/ipccar5_data_out/eais_gslr.nc \
--location-file /mnt/ipccar5_data_in/location.lst \
--fingerprint-dir /mnt/ipccar5_data_in/FPRINT \
--local-gis-output-file /mnt/ipccar5_data_out/gis_lslr.nc \
--local-ais-output-file  /mnt/ipccar5_data_out/ais_lslr.nc \
--local-wais-output-file /mnt/ipccar5_data_out/wais_lslr.nc \
--local-eais-output-file /mnt/ipccar5_data_out/eais_lslr.nc 
```

## Features
Several options and configurations are available when running the container. The following example shows the options for the `glaciers` command. 

```shell
Usage: ipccar5 glaciers [OPTIONS]

Options:
  --scenario TEXT               Scenario
  --refyear-start INTEGER       Start year for reference period  [default:
                                1986]
  --refyear-end INTEGER         End year for reference period  [default: 2005]
  --start-year INTEGER          Year from which to start integrating
                                temperature  [default: 2005]
  --end-year INTEGER            Year to end the projection (Used in
                                preprocess).  [default: 2151]
  --tlm-flag INTEGER            Use the two-layer model data, 1=yes  [default:
                                1]
  --pipeline-id TEXT            Unique identifier for this instance of the
                                module
  --climate-fname TEXT          NetCDF4/HDF5 file containing surface
                                temperature data (this should be a fair
                                output)  [required]
  --rng-seed INTEGER            Seed value for random number generator
                                [default: 1234]
  --pyear-start INTEGER         Projection start year  [default: 2020]
  --pyear-end INTEGER           Projection end year  [default: 2150]
  --pyear-step INTEGER          Projection year step  [default: 10]
  --nmsamps INTEGER             Number of method samples to generate
                                [default: 1000]
  --ntsamps INTEGER             Number of climate samples to generate
                                [default: 450]
  --nsamps INTEGER              Total number of samples to generate (replaces
                                'nmsamps' and 'ntsamps' if provided)
  --use-gmip [0|1|2]            Use the GMIP calibration  [default: 2]
  --glacier-fraction-file TEXT  Path to glacier fraction file
  --global-output-sl-file TEXT  Path to global output sea-level file
  --climate-means-fname TEXT    Path to climate data means file (if
                                tlm_data=0)
  --climate-sds-fname TEXT      Path to climate data standard deviations file
                                (if tlm_data=0)
  --location-file TEXT          File that contains name, id, lat, and lon of
                                points for localization
  --chunksize INTEGER           Number of locations to process at a time
  --fingerprint-dir TEXT        Path to fingerprint directory  [required]
  --local-output-sl-file TEXT   Path to local output sea-level file
  -h, --help                    Show this message and exit.
```

See this help documentation by passing the `--help` flag when running the application, for example:

```shell
docker run --rm ipccar5 glaciers --help
```
or 
```shell
docker run --rm ipccar5 icesheets --help
```
## Results
If this module runs successfuly, NetCDF files containing sea level projections will be written to `./data/output`. The glaciers command writes two files, local and global sea level change due to contributions from glaciers. The `icesheets` command writes local and global projections files for the Greenland Ice Sheet (GIS), Antarctic Ice Sheet (AIS), Eastern Antarctic Ice Sheet (EAIS), and Western Antarctic Icesheet (WAIS).

## Build the container locally
You can build the container with Docker by cloning the repository locally and then running the following command from the repository root:

```shell
docker build -t ipccar5 .

```

## Support

Source code is available online at https://github.com/facts-org/ipccar5. This software is open source, available under the MIT license.

Please file issues in the issue tracker at https://github.com/facts-org/ipccar5/issues.