from argparse import ArgumentParser
import numpy as np
import pytest
from glob import glob
from datetime import timedelta as delta
from os import path
import time
from netCDF4 import Dataset
import csv
import os
import yaml
import json
import sys

def main(config_loc=''):
    start = time.time()
    if config_loc == '':
        parser = ArgumentParser(description='RUN PARCELS worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('eco_location', help='location of ecosystem file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()

        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    code = exit_code(config,'find_seed')
    if args.force == False:
        if code != '0':
            sys.exit(1)
    POLL = eco_poll(args.eco_location,'run_parcels')
    list_of_files = glob(config['data_path'] + config['file_parse'])  # * means all if need specific format then *.csv
    mtimes = 0
    for file in list_of_files:
        mtime = os.path.getmtime(file)
        if start - mtime <= (POLL/1000*1.25):
            mtimes = mtimes + 1
    if mtimes >= 3:
        print('new netcdf data found, running open parcels worker now....')
        args.force = True

    if args.force == True:
        from parcels import ErrorCode, FieldSet, ParticleSet, ScipyParticle, JITParticle, AdvectionRK4, ParticleFile
        with open(config['lon_csv']) as csvfile:
            file1 = csv.reader(csvfile, delimiter=',')
            LOS = []
            for row in file1:
                LO = row[0]
        #        LA = row[1]
                LOS.append(LO)
        #        LAS.append(LA)
        with open(config['lat_csv']) as csvfile:
            file2 = csv.reader(csvfile, delimiter=',')
            LAS = []
            for row in file2:
                LA = row[0]
                LAS.append(LA)

        start = time.time()
        # data_path = path.join(path.dirname(__file__), 'NemoCurvilinear_data/')
        data_path = config['data_path']
        ufiles = sorted(glob(data_path+config['ufile_parse']))
        ufiles = ufiles[-1]
        vfiles = sorted(glob(data_path+config['vfile_parse']))
        vfiles = vfiles[-1]

        start_date = ufiles.split('_')[2]
        end_date = ufiles.split('_')[3]

        if ufiles.split('_')[3] != vfiles.split('_')[3] and ufiles.split('_')[2] != vfiles.split('_')[2]:
            print('error U and V files do not have same start and end dates.... terminating')
            sys.exit(3)

        grid_file = config['grid_file']
        filenames = {'U': {'lon': grid_file,
                               'lat': grid_file,
                               'data': ufiles},
                         'V': {'lon': grid_file,
                               'lat': grid_file,
                               'data': vfiles}}
        variables = {'U': 'uos', 'V': 'vos'}
        dimensions = {'lon': 'glamf', 'lat': 'gphif','time': 'time_counter' }
        field_set = FieldSet.from_nemo(filenames, variables, dimensions)

            #Plot u field
        #field_set.U.show()

            # Make particles initial position list
        #nc_fid = Dataset(grid_file, 'r') #open grid file nc to read
        #lats = nc_fid.variables['nav_lat'][:]  # extract/copy the data
        #lons = nc_fid.variables['nav_lon'][:]

        #lonE=lons[:,169-3]
        #latE=lats[:,169-3]

        #npart = 3000
        #lonp = [i for i in np.linspace(min(lonE), max(lonE), npart)]
        #latp = [i for i in np.linspace(15.98, max(latE), npart)] #this makes a list!

        pset = ParticleSet.from_list(field_set, JITParticle, lon=LOS, lat=LAS)
        pfile = ParticleFile(config['out_dir']+config['out_file']+'_'+start_date+'_'+end_date+'.nc', pset, outputdt=delta(hours=0.5))
        kernels = pset.Kernel(AdvectionRK4)
        #Plot initial positions
        #pset.show()
        def DeleteParticle(particle, fieldset, time):
            particle.delete()


        pset.execute(kernels, runtime=delta(hours=118), dt=delta(hours=0.1),  output_file= pfile, recovery={ErrorCode.ErrorOutOfBounds: DeleteParticle})

        pfile.close()

        #plotTrajectoriesFile("nBelize_nemo_sargaso_particlesT2");

        #pset.show(domain={'N':-31, 'S':-35, 'E':33, 'W':26})
        #pset.show(field=field_set.U)
        #pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2))
        #pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2), with_particles=False)
        print('RUN PARCELS worker Complete, going to sleep for ' + str(POLL/60000) + ' minutes')
        end = time.time()
        print(end-start)
        sys.exit(0)
    else:
        sys.exit(2)

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['RUN_PARCELS']
    return config

def eco_poll(YAML_loc,worker_name):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        eco_file = yaml.safe_load(f)
    for eco in eco_file['apps']:
        if eco['name'] == worker_name:
            eco_poll = eco['restart_delay']
    return eco_poll

def exit_code(config,worker):
    with open(config['pm2log'], 'r') as f:
        lines = f.read().splitlines()
    for line in range(len(lines),0,-1):
        last_line = lines[line-1]
        if worker in last_line and 'exited with code' in last_line:
            last_line = last_line.split(' ')
            code = last_line[8]
            code = code[1]
            return code

    return -1

if __name__ == '__main__':
    main()  # pragma: no cover
