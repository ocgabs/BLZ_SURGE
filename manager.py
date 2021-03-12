'''

Manager Script to run operational NEMO storm surge model, this script imports the workers
and checks that they ran correctly.

'''

from argparse import ArgumentParser
from workers import download_weather
from workers import process_forcing
from workers import generate_boundary
from workers import rasteriogeoref
from workers import run_nemo
from workers import watch_nemo
from workers import stop_container
#from workers import v4Belize_Parcels
#from workers import clean_up
import time
import sys
from datetime import datetime
import os
import yaml

def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='RUN NEMO worker')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    FMT = '%Y-%m-%d %H:%M:%S'
    time0 = datetime.now()
    t0_midnight = str(time0.year) + '-' + str(time0.month) + '-' + str(time0.day) + ' 00:00:00'
    timeorigin = datetime.strptime(t0_midnight, FMT)
    RUN_NEMO = False
    RUN_SARGASSIUM = False
    exit = False
    generate_weights = config['generate_weights']
    first_start = True

    status = {'DOWNLOAD_WEATHER': 'not yet started',
              'PROCESS_FORCING': 'not yet started',
              'GENERATE_WEIGHTINGS': 'not yet started',
              'RUN_NEMO': 'not yet started',
              'WATCH_NEMO': 'not yet started',
              'STOP_CONTAINER': 'not yet started',
              'CLEAN_UP': 'not yet started',
              'SEED_LOC_GEN': 'not yet started',
              'OCEAN_PARCELS': 'not yet started',
              'PLOT_PARCELS': 'not yet started',
              'SLEEP': 'not been to sleep yet',
              'NEMO_runs': 0,
              'SARGASSIUM_runs': 0
    }

    print(status)
    while exit == False:
        if first_start == False:
            timenow = datetime.now()
            start_t = datetime.strftime(timenow, FMT)
            status['sleep'] = f'waking up at {start_t}, checking to see if anything needs to be run'
            print(status)
            tdelta = timenow - timeorigin
            tdelta_hours = int(tdelta.seconds/3600)

        if first_start == True:
            req_time = datetime.now().strftime(FMT)
            print(f'first start of manager at {req_time} so running all processes...')
            RUN_NEMO = True
            RUN_SARGASSIUM = True
            first_start = False
            tdelta_hours = 0

        if tdelta_hours >= config['NEMO_running']*(status['NEMO_runs']+1):
            RUN_NEMO = True
            status['NEMO_runs'] = status['NEMO_runs'] + 1
        if tdelta_hours >= config['SARGASSIUM_running']*(status['SARGASSIUM_runs']+1):
            RUN_SARGASSIUM = True

        if RUN_NEMO == True:
            print('Running operational NEMO model now...')
            # # run download latest atmo forcing
            # req_time = datetime.now().strftime(FMT)
            # status['DOWNLOAD_WEATHER'] = f'download weather worker started at {req_time}'
            # print(status)
            # atmo_worker = download_weather.main(args.config_location)
            # req_time = datetime.now().strftime(FMT)
            # if atmo_worker == 0:
            #     print('latest atmo forcing data downloaded successfully')
            #     status['DOWNLOAD_WEATHER'] = f'download weather worker successful at {req_time}'
            #     print(status)
            # if atmo_worker != 0:
            #     print(atmo_worker)
            #     print('atmo_worker failed, terminating program')
            #     status['DOWNLOAD_WEATHER'] = f'download weather worker failed at {req_time}'
            #     status['NEMO_runs'] = status['NEMO_runs'] - 1
            #     print(status)
            #     sys.exit('download worker failed')

            # process forcing data
            req_time = datetime.now().strftime(FMT)
            status['PROCESS_FORCING'] = f'processing weather worker started at {req_time}'
            print(status)
            forcing_worker = process_forcing.main(args.config_location)
            req_time = datetime.now().strftime(FMT)
            if forcing_worker == 0:
                print('grib data successfully converted to netcdf')
                status['PROCESS_FORCING'] = f'process weather worker successful at {req_time}'
                print(status)
            if forcing_worker != 0:
                print(forcing_worker)
                print('process atmo forcing worker failed, terminating program')
                status['PROCESS_FORCING'] = f'processing weather worker failed at {req_time}'
                status['NEMO_runs'] = status['NEMO_runs'] - 1
                print(status)
                sys.exit('process forcing worker failed')

            if generate_weights == True:
                # generate_boundary weightings
                req_time = datetime.now().strftime(FMT)
                status['GENERATE_WEIGHTINGS'] = f'generate weightings worker started at {req_time}'
                print(status)
                boundary_worker = generate_boundary.main(args.config_location)
                req_time = datetime.now().strftime(FMT)
                if boundary_worker == 0:
                    print('boundary weighting successfully created')
                    status['GENERATE_WEIGHTINGS'] = f'generate weightings worker successful at {req_time}'
                    print(status)
                if boundary_worker != 0:
                    print(boundary_worker)
                    print('boundary weighting generation failed, terminating program')
                    status['GENERATE_WEIGHTINGS'] = f'generate weightings worker failed at {req_time}'
                    print(status)
                    status['NEMO_runs'] = status['NEMO_runs'] - 1
                    sys.exit('weighting worker failed')

            # run model
            req_time = datetime.now().strftime(FMT)
            status['RUN_NEMO'] = f'run nemo worker started at {req_time}'
            print(status)
            run_nemo_worker = run_nemo.main(args.config_location)
            req_time = datetime.now().strftime(FMT)
            if run_nemo_worker == 0:
                print('NEMO model run successfully started')
                status['RUN_NEMO'] = f'run nemo worker successful at {req_time}'
                status['NEMO_runs'] = status['NEMO_runs'] + 1
                print(status)
            if run_nemo_worker != 0:
                print(run_nemo_worker)
                print('starting model failed, terminating program')
                status['RUN_NEMO'] = f'run NEMO worker failure at {req_time}'
                print(status)
                status['NEMO_runs'] = status['NEMO_runs'] - 1
                print('stopping container incase it started.')
                req_time = datetime.now().strftime(FMT)
                status['STOP_CONTAINER'] = f'stop container worker started at {req_time}'
                print(status)
                container_stop = stop_container.main(args.config_location)
                req_time = datetime.now().strftime(FMT)
                if container_stop == 0:
                    print('container already stopped')
                    status['STOP_CONTAINER'] = f'stop container worker ran successfully at {req_time}'
                    print(status)
                if container_stop == 1:
                    print('container was still running but has been stopped')
                    status['STOP_CONTAINER'] = f'stop container worker ran successfully at {req_time}'
                    print(status)
                if container_stop > 1:
                    print(container_stop)
                    print('stop container worker failed, program terminating')
                    status['STOP_CONTAINER'] = f'stop container worker failed at {req_time}'
                    status['NEMO_runs'] = status['NEMO_runs'] - 1
                    print(status)
                    sys.exit('container stop worker failed')
                sys.exit('run_nemo worker failed')

            # watch model
            req_time = datetime.now().strftime(FMT)
            status['WATCH_NEMO'] = f'watch nemo worker started at {req_time}'
            print(status)
            watch_nemo_worker = watch_nemo.main(args.config_location)
            req_time = datetime.now().strftime(FMT)
            if watch_nemo_worker == 0:
                print('NEMO model ran successfully')
                status['WATCH_NEMO'] = f'nemo ran successfully at {req_time}'
                print(status)
            if watch_nemo_worker != 0:
                print(watch_nemo_worker)
                print('model run failed, terminating program')
                status['WATCH_NEMO'] = f'run NEMO worker failure at {req_time}'
                print(status)
                status['NEMO_runs'] = status['NEMO_runs'] - 1
                sys.exit('watch NEMO worker failed')

            req_time = datetime.now().strftime(FMT)
            status['STOP_CONTAINER'] = f'stop container worker started at {req_time}'
            print(status)
            container_stop = stop_container.main(args.config_location)
            req_time = datetime.now().strftime(FMT)
            if container_stop == 0:
                print('container already stopped')
                status['STOP_CONTAINER'] = f'stop container worker ran successfully at {req_time}'
                print(status)
            if container_stop == 1:
                print('container was still running but has been stopped')
                status['STOP_CONTAINER'] = f'stop container worker ran successfully at {req_time}'
                print(status)
            if container_stop > 1:
                print(container_stop)
                print('stop container worker failed, program terminating')
                status['STOP_CONTAINER'] = f'stop container worker failed at {req_time}'
                status['NEMO_runs'] = status['NEMO_runs'] - 1
                print(status)
                sys.exit('container stop worker failed')

            # clean_up = clean_up.main(args.config_location)
            # if clean_up == 0:
            #     print('clean up successful')
            # if stop_container != 0:
            #     print('clean up was unsuccessful')
            #     sys.exit('stop container worker failure')

            RUN_NEMO = False

        # if RUN_SARGASSIUM == True:
        #     print('Running Sargassium tracking now')
        #     # use sargassium product to create seeding locations
        #     raster_gen = rasteriogeoref.main(args.config_location)
        #     if raster_gen == 0:
        #         print('seeding locations for openParcels successfully generated')
        #     if raster_gen != 0:
        #         print('seeding worker failed, terminating program')
        #         sys.exit('seeding worker failure')
            # run open parcels
            #status['SARGASSIUM_runs'] = status['SARGASSIUM_runs'] + 1
            # plot open parcels

            # clean up

            RUN_SARGASSIUM = False
        req_time = datetime.now().strftime(FMT)
        status['sleep'] = f'entering sleep mode at {req_time} will check again in {str(config["POLL_INTERVAL"])} minutes'
        print(status)
        print(f'entering sleep mode at {req_time} will check again in {str(config["POLL_INTERVAL"])} minutes')
        time.sleep(config['POLL_INTERVAL']*60)
    return 0

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['MANAGER']
    return config

if __name__ == '__main__':
    main()