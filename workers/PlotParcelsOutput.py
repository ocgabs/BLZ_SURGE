#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 17:52:52 2020

@author: gmaya
"""

import datetime as dt  # Python standard library datetime  module
import numpy as np
from netCDF4 import Dataset  # http://code.google.com/p/netcdf4-python/
import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap, addcyclic, shiftgrid
import os
from random import randint
import cartopy
import cartopy.crs as ccrs
from matplotlib import colors as c
import arrow
from argparse import ArgumentParser
import yaml
import sys
from glob import glob

def main(config_loc=''):

    if config_loc == '':
        parser = ArgumentParser(description='RUN PARCELS worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('eco_location', help='location of ecosystem file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()

        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    code1,timestamp1 = exit_code(config,'run_parcels','0')
    if code1 != '0':
        print('unable to find a successful run of previous worker, terminating now')
        sys.exit(1)
    code2,timestamp2 = exit_code(config,'plot_tracks','0')
    if code2 == -1:
        print('no log for previous run found, assume first start')
        args.force = True

    if args.force == False:
        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        if timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True
    POLL = eco_poll(args.eco_location,'plot_tracks')
    infiles = sorted(glob(config['input_dir']+'*.nc'))
    infile = infiles[-1]
    dates = infile.split('_')
    enddate = dates[-1]
    enddate = enddate[:-3]
    startdate = dates[-2]
    nc_fid = Dataset(infile, 'r')  # Dataset is the class behavior to open the file
                                    # and create an instance of the ncCDF4 class
    #nc_attrs, nc_dims, nc_vars = ncdump(nc_fid) #ncdump functions needs to be coded
    # Extract data from NetCDF file
    lats = nc_fid.variables['lat'][:]  # extract/copy the data
    lons = nc_fid.variables['lon'][:]
    time = nc_fid.variables['time'][:]
    plt.figure(figsize=[15, 15])  # a new figure window
    ax = plt.subplot(111, projection=ccrs.PlateCarree())  # specify (nrows, ncols, axnum)
    minlon = np.min(lons)
    maxlon = np.max(lons)
    minlat = np.min(lats)
    maxlat = np.max(lats)
    ax.set_extent([minlon+config['set_extent_W'], maxlon+config['set_extent_E'],
                   minlat+config['set_extent_S'], maxlat+config['set_extent_N']], crs=ccrs.PlateCarree())  # set extent
    ax.set_title('Forecast Particle Trajectories '+startdate+' to '+enddate, fontsize=20)  # set title
    ax.add_feature(cartopy.feature.LAND, zorder=0)  # add land polygon
    ax.add_feature(cartopy.feature.COASTLINE, zorder=10)  # add coastline polyline
    #progress_time = start_time + timedelta(seconds=int(time[i]) * args['time_step'])
    #FMT = '%d %b %Y %H:%M'
    #progress_time = progress_time.strftime(FMT)
    #plt.text((minlon + 1.75), (maxlat - 1.75), progress_time, fontsize=20, bbox=dict(facecolor='cyan', boxstyle='round'))
    gl = ax.gridlines(crs=ccrs.PlateCarree(), linewidth=2, color='black', alpha=0.5, linestyle='--', draw_labels=True)
    gl.xlabel_style = {'size': 18, 'color': 'black'}
    gl.ylabel_style = {'size': 18, 'color': 'black'}
    gl.xlabels_top = False  # no xlabels at top
    gl.ylabels_left = False  # no y labels on left
    # make a color map of fixed colors
    #cmap = c.ListedColormap(['#00004c', '#000080', '#0000b3', '#0000e6', '#0026ff', '#004cff',
                             #'#0073ff', '#0099ff', '#00c0ff', '#00d900', '#33f3ff', '#73ffff', '#c0ffff',
                             #(0, 0, 0, 0),
                             #'#ffff00', '#ffe600', '#ffcc00', '#ffb300', '#ff9900', '#ff8000', '#ff6600',
                             #'#ff4c00', '#ff2600', '#e60000', '#b30000', '#800000', '#4c0000'])
    # define bounds for colour bar
    #bounds = [-2, -1, -0.75, -0.50, -0.30, -0.25, -0.20, -0.15, -0.1, -0.05, 0.05, 0.1, 0.15, 0.20, 0.25, 0.30, 0.50, 0.75,
    #          1, 2]
    #norm = c.BoundaryNorm(bounds, ncolors=cmap.N)  # cmap.N gives the number of colors of your palette
    # prodice contour data to plot using colour map, norm and defined bounds
    for x in range(1, config['num_particles']):
        p = randint(0, len(lats) - 1)  # Returns a random integer between the specified integers.
        # PLOT

        plt.plot(lons[p, :], lats[p, :], 'r')
    #mm = ax.contourf(lon, lat, ssh, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, levels=bounds)
    ## make a color bar
    #cbar = plt.colorbar(mm, cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds, ax=ax, orientation='horizontal',
    #                    pad=0.05)
    #cbar.ax.set_xticklabels(cbar.ax.get_xticklabels(), rotation='vertical')
    # save figure as png file in output folder
    #plt.savefig(dirs['animation_plots_dir'] + args['config_name'] + "_" + str(time[i]) + "_sea_surface_height.png",
    #            bbox_inches='tight')

    #plt.savefig(dirs['animation_plots_dir']+args['config_name']+"_"+str(time[i])+"_sea_surface_height.png",bbox_inches='tight')

    plt.savefig(config['out_dir']+'forecast_tracks'+'_'+startdate+'_'+enddate+'.png',bbox_inches='tight')

        # plt.plot(lons[:,30],lats[:,30],'b.')
    plt.show()

    dlat=np.diff(lats) #along track difference of latitude
    dlon=np.diff(lons)
    pstop=0
    delp=0
    nstop=[None]
    wstop=[None]
    la0 = []
    for x in range(len(dlat)):
        pdlat=dlat.data[x,:] #along track difference of latitude of each particle
        pdlon=dlon.data[x,:]
        plat=lats.data[x,:]
        plon=lons.data[x,:]
        ptime=time.data[x,:]
        nla = np.isnan(plat) #Check if particle was deleted, if position is NAN
        if nla.any()==True :
            delp=delp+1
        #if ptime.any() == 'NaT': #when are particles deleted
        nan_indx = np.argwhere(np.isnan(plat))
        if len(la0) > 0 and len(la0[0]) > 0:
            wstop.append(nan_indx)
        la0 = np.where(pdlat == 0) #find where dlat ==0
        lo0 = np.where(pdlon == 0)
        if len(la0) > 0 and len(la0[0]) > 0 and len(lo0) > 0 and len(lo0[0]) > 0:   #this checks if la0 is NOT empty
            pstop=pstop+1 #if la0 and lo0 NOT empty particle has stoped

    print(pstop)
    print('deleted particles ' +str(delp))
    nstop.append(pstop)
    sys.exit(0)
    #print('when particle stopped' '\n' + str(wstop))

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['PLOT_TRACKS']
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

def exit_code(config,worker,code_find=None):
    if code_find != None:
        with open(config['pm2log'], 'r') as f:
            lines = f.read().splitlines()
        for line in range(len(lines),0,-1):
            last_line = lines[line-1]
            if worker in last_line and 'exited with code'in last_line:
                last_line = last_line.split(' ')
                code = last_line[8]
                code = code[1]
                if code != code_find:
                    continue
                timestamp = last_line[0]
                timestamp = timestamp[:-1]
                return code,timestamp
    if code_find == None:
        with open(config['pm2log'], 'r') as f:
            lines = f.read().splitlines()
        for line in range(len(lines),0,-1):
            last_line = lines[line-1]
            if worker in last_line and 'exited with code'in last_line:
                last_line = last_line.split(' ')
                code = last_line[8]
                timestamp = last_line[0]
                timestamp = timestamp[:-1]
                code = code[1]
                return code,timestamp
    return -1,-1

if __name__ == '__main__':
    main()  # pragma: no cover
