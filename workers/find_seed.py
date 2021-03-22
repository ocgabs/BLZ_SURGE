import matplotlib.pyplot as plt
import numpy as np
import rasterio
import xarray as xr
from rasterio.plot import show
from rasterio.crs import CRS
import netCDF4 as nc
import shapely.geometry as geom
from argparse import ArgumentParser
import yaml
from descartes.patch import PolygonPatch
import os
import datetime
import requests
import bs4
import json
import sys
import time
from glob import glob

def main(config_loc=''):
    #start = time.time()
    if config_loc == '':
        parser = ArgumentParser(description='find seeds worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('eco_location', help='location of ecosystem file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)

    code1,timestamp1 = exit_code(config,'get_sargassium')
    if code1 != '0':
        sys.exit(1)
    if code1 == -1:
        print('no log entry for previous worker found, assume first start')
        sys.exit(1)
    code2,timestamp2 = exit_code(config,'find_seed')
    if code2 == -1:
        print('no log for previous run found, assume first start')
        args.force = True

    if args.force == False:
        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        if code2 == 0 or 2 and timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True

    POLL = eco_poll(args.eco_location,'find_seed')
    # list_of_files = glob(config['dest_dir'] + config['file_parse'])  # * means all if need specific format then *.csv
    # mtimes = 0
    # for file in list_of_files:
    #     mtime = os.path.getmtime(file)
    #     if start - mtime <= (POLL/1000*1.25):
    #         mtimes = mtimes + 1
    # if mtimes >= 1:
    #     print('new sargassium data found, running seed location worker now....')
    #     args.force = True

    if args.force == True:
        print('reading in Sargassium image')
        data = rasterio.open(config['dest_dir']+config['tiff_name'])
        sband = data.read(1)
        # FIND pixels with sargassum
        print('finding seed locations....')
        spx ,spy =np.where((sband < 252) & (sband > 0))
        spx.size
        # will be good to read more about the product to know what the different values mean!

        # Get locations with Sargasso
        # Acumuladores
        slo = np.array([])
        sla = np.array([])
        # Loop through your list of coords
        print('getting seed coordinates.....')
        for i in range(0, spx.size):
            # Get pixel coordinates from map coordinates
            lo, la = data.xy(spx[i], spy[i])
            slo = np.append(slo, lo)
            sla = np.append(sla, la)
            # print('Pixel Y, X coords: {}, {}'.format(py, px))

        # Make a shapley multipoint with the sargasso locations
        spoints = geom.MultiPoint((np.array([slo, sla]).T).tolist())

        len(spoints)

        # Read in NEMO grid
        print('reading in NEMO grid')
        bathy = config['bathy_meter']
        bat = nc.Dataset(bathy)
        lat = bat['nav_lat'][:]
        lon = bat['nav_lon'][:]
        h = bat['Bathymetry'][:]

        if config['plot'] == True:
            # Rough Plot on a map (*not proper lon/lat projection)
            fig, ax0 = plt.subplots(nrows=1)
            im = ax0.pcolormesh(lon, lat, h)
            fig.colorbar(im, ax=ax0)
            plt.show()
            bat.close()

        # Find lola of model domain perimeter
        lon = np.array(lon)
        lat = np.array(lat)
        plo = np.concatenate((lon[:, 0], lon[-1, :], np.flipud(lon[:, -1]), np.flipud(lon[0, :])), axis=0)
        pla = np.concatenate((lat[:, 0], lat[-1, :], np.flipud(lat[:, -1]), np.flipud(lat[0, :])), axis=0)

        # Needs to be a shaply polygon to intersect them with the locations with Sargasso
        # To get it into shaply format:
        # give plo and pla an extra empty dimension
        plo = plo[:, np.newaxis]
        pla = pla[:, np.newaxis]

        # combine x y arrays into a two dimensional sequence of coordinates
        coord = np.append(plo, pla, axis=1)

        # make a shapley polygon
        nbox = geom.Polygon(coord)

        # Now find the locations (slo, sla) with Sargaso inside the NEMO domain (nbox)
        print('finding seed locations within NEMO domain')
        sloc_range = np.zeros(slo.size, dtype=bool)
        for i in range(slo.size):
            sloc_range[i] = nbox.contains(spoints[i])

        if config['plot'] == True:
            # plotting!
            fig, (ax1) = plt.subplots(nrows=1)

            ax1.plot(slo[sloc_range], sla[sloc_range], '.r', ms=10, zorder=3)
            patch = PolygonPatch(nbox, facecolor='k', alpha=0.5, zorder=1)
            ax1.add_patch(patch)
            ax1.plot(slo, sla, '.b', ms=10, zorder=2)

        sum(sloc_range)
        slo[sloc_range]
        sla[sloc_range]

        ilon = slo[sloc_range]
        ilat = sla[sloc_range]
        print('saving output CSV file')
        np.savetxt(config['dest_dir'] + 'ilon.csv', ilon, delimiter=',')
        np.savetxt(config['dest_dir'] + 'ilat.csv', ilat, delimiter=',')
        print('worker ran successfully, sleeping for '+str(POLL/60000) + ' minutes')
        print('The End')
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
    config = config_file['FIND_SEEDS']
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
            timestamp = last_line[0]
            timestamp = timestamp[:-1]
            code = code[1]
            return code,timestamp

    return -1,-1

def timestamp_check(timestamp1,timestamp2):
    dt_timestamp1 = datetime.datetime.strptime(timestamp1,"%Y-%m-%dT%H:%M:%S")
    dt_timestamp2 = datetime.datetime.strptime(timestamp2,"%Y-%m-%dT%H:%M:%S")
    if dt_timestamp1 > dt_timestamp2:
        return True
    else:
        return False

if __name__ == '__main__':
    main()  # pragma: no cover