'''

Manager Script to run operational NEMO storm surge model, this script imports the workers
and checks that they ran correctly.

'''

from argparse import ArgumentParser
from workers import download_weather
from workers import process_forcing
from workers import generate_boundary
from workers import rasteriogeoref
import sys

def main():
    parser = ArgumentParser(description='Manager Script for running operational NEMO Surge')
    parser.add_argument('config_location', help='location of YAML config file')
    args = parser.parse_args()

    # run download latest atmo forcing
    atmo_worker = download_weather(args.config_location)
    if atmo_worker == 0:
        print('latest atmo forcing data downloaded successfully')
    if atmo_worker != 0:
        print('atmo_worker failed, terminating program')
        sys.exit('atmo worker failure')

    # process forcing data
    forcing_worker = process_forcing(args.config_location)
    if forcing_worker == 0:
        print('grib data successfully converted to netcdf')
    if forcing_worker != 0:
        print('process atmo forcing worker failed, terminating program')
        sys.exit('process forcing worker failure')

    # generate_boundary weightings
    boundary_worker = generate_boundary(args.config_location)
    if boundary_worker == 0:
        print('boundary weighting successfully created')
    if boundary_worker != 0:
        print('boundary weighting generation failed, terminating program')
        sys.exit('boundary weighting worker failure')

    # run model

    # watch model

    # use sargassium product to create seeding locations
    raster_gen = rasteriogeoref(args.config_location)
    if raster_gen == 0:
        print('seeding locations for openParcels successfully generated')
    if raster_gen != 0:
        print('seeding worker failed, terminating program')
        sys.exit('seeding worker failure')

    # run open parcels

    # plot open parcels

    # clean up


if __name__ == '__main__':
    main()