#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tues Aug 28 13:41:34 2018

@author: thopri
"""

# Copyright 2018 Thopri National Oceanography Centre
# Based on 2016 Doug Latornell, 43ravens

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
C-RISC NEMO nowcast weather model make plots worker

Worker takes the model output and processes the output in the following ways:

* move model output netcdf file to designated output folder
* produce time series plots of the locations listed in the station_location text file
* produce spatial plots of whole domain at the interval and total time specified in YAML config file
* check for threshold exceedance as defined in station_location text file for each location
* produce csv time series files for each station location
Still in progress
+ check whole domain for a global threshold exceedance
+ produce spatial plot of location listed in station location text file
+ ouput threshold exceedance check (currently just a python dictionary written to log file)

"""
import logging
import os
import glob
import sys
import shutil
import imageio
from datetime import datetime
from datetime import timedelta
import datetime as dt
import json

# **IMPORTANT**: matplotlib must be imported before anything else that uses it
# because of the matplotlib.use() call below
import matplotlib
matplotlib.use('Agg')
from matplotlib import colors as c
import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs
import pandas as pd

import arrow
from argparse import ArgumentParser
import yaml

#Main function that processes model output
#main function to run the NEMO model
def main(config_loc=''):
    # start = time.time()
    if config_loc == '':
        parser = ArgumentParser(description='plotting worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()
        if args.force == True:
            print('force flag enabled, running worker now....')
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)

    if args.force == False:
        code1,timestamp1 = exit_code(config,'watch_nemo','0')
        if code1 != '0':
            print('unable to find a successful run of previous worker, terminating now')
            sys.exit(1)
        code2,timestamp2 = exit_code(config,'make_plots','0')
        if code2 == -1:
            print('no log for previous run found, assume first start')
            args.force = True

        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        if timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True

    if args.force == True:
        #get todays date in the format specifed
        start_ymd = arrow.now().format('YYYY-MM-DD')
        dirs = dir_gen(config) #generate directory locations as per YAML config file
        print(dirs)
        args = args_gen(config) #generate command arguments as per YAML config file
        print(args)
        dataset_name = readoutputname(dirs) #read model output file name to get datasetname
        print(dataset_name)
        lat,lon = read_coords(dataset_name) #extract lat and lons from dataset file
        stations = read_stations(dirs, args) #read station_location txt file for time series locations and thresholds
        print(stations)
        run_time = write_run_time(dataset_name, dirs)
        print(run_time)
        #station_loc = plot_station_locations(dirs, args, stations, lat, lon)
        #print(station_loc)
        station_ind = generate_IJ(lat, lon, stations) #calculate I and J indices for time series locations
        print(station_ind)
        time_series = extract_timeseries(dataset_name, station_ind) #extract time series for time series locations
        plot = plot_timeseries(time_series, dirs, station_ind, args)
        print(plot)
        #plot1 = plot_SSH(dataset_name, args, lat, lon, dirs) #plot ssh spatial plots at the defined interval
        #print(plot1)
        thres_check = check_thres_station(time_series, station_ind, dirs, args) #check for threshold exceedance at defined station locations
        print(thres_check)
        csv = export_csv(time_series, args, dirs) #export time series as csv files
        print(csv)
        #result = move_netcdf(dirs, dataset_name) #move model output netcdf file from model run directory
        #print(result)
        test = global_thres_exccedance_check(time_series, args)
        print(test)

        print('worker ran successfully, exiting now')
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
        config = yaml.safe_load(f)
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

def timestamp_check(timestamp1,timestamp2):
    dt_timestamp1 = datetime.strptime(timestamp1,"%Y-%m-%dT%H:%M:%S")
    dt_timestamp2 = datetime.strptime(timestamp2,"%Y-%m-%dT%H:%M:%S")
    if dt_timestamp1 > dt_timestamp2:
        return True
    else:
        return False

#Function to generate directory locations based on YAML config file
def dir_gen(config): 
    dirs = {
            'station_dir' : config['make']['plots']['station_dir'],
            'plots_dir' : config['make']['plots']['plots_dir'],
            'model_output_dir' : config['make']['plots']['model_output_dir'],
            'csv_dir' : config['make']['plots']['csv_dir'],
            'netcdf_dir' : config['make']['plots']['netcdf_dir'],
            'animation_plots_dir' : config['make']['plots']['animation_plots_dir'],
            }
    return dirs
#Function to generate command arguments from YAML config file
def args_gen(config):
    args = {
        'tot_t' : config['make']['plots']['total_time'],
        'interval' : config['make']['plots']['interval'],
        'global_thres' : config['make']['plots']['global_thres'],
        'station_list' : config['make']['plots']['station_list'],
        'config_name' : config['make']['plots']['config_name'],
        'time_step' : config['make']['plots']['time_step'],
        }
    return args
#Read model output filename from model run diectory
def readoutputname(dirs):
    list_of_files = glob.glob(dirs["model_output_dir"]+'*T.nc')
    sorted_files = sorted(list_of_files, key=os.path.getctime)
    latest_file = max(sorted_files, key=os.path.getmtime)
    return latest_file
#Function to read the station locations from the station list file define in YAML config
def read_stations(dirs, args):
    station_list = dirs['station_dir']+args['station_list']
    with open(station_list) as f:
        content = f.readlines()
    # you may also want to remove whitespace characters like `\n` at the end of each line
    content = [x.strip() for x in content] 
    content = [x.split(' ') for x in content]
    return content
#read lat and lon coordinates from model output file
def read_coords(dataset_name):

    f = Dataset(dataset_name)
    lat = f.variables["nav_lat"][:]
    lon = f.variables["nav_lon"][:]
    lat = lat[:,0]
    lon = lon[0,:]
    f.close()
    
    return lat, lon
#generate I and J indices for each station location
def generate_IJ(lat, lon, stations):
    station_indices = {}
    num_stations = len(stations)
    for f in range(num_stations):
        lat_station = float(stations[f][2])
        lon_station = float(stations[f][3])
        thres = float(stations[f][4])
        station = stations[f][0]  
        idx = (np.abs(lat-lat_station)).argmin()
        idy = (np.abs(lon-lon_station)).argmin()
        station_indices[station] = [idx, idy, thres]
      
    return station_indices
#Extract time series for each set of station IJ indices
def extract_timeseries(dataset_name, station_ind):
    station_elev = {}
    f = Dataset(dataset_name)
    for key in station_ind:
        idx = station_ind[key][0]
        idy = station_ind[key][1]
        elev = f.variables["zos"][:,idx,idy]
        time = f.variables['time_counter'][:]
        time_series = np.column_stack([time,elev])
        station_elev[key] = time_series
           
    return station_elev

def write_run_time(dataset_name, dirs):
    status = 'unable to write run time json file'
    f = Dataset(dataset_name)
    time = f.variables['time_counter'][:]
    start = time[0]
    end = time[-1]
    time_list = {}
    day_zero = dt.datetime(1900,1,1,0,0,0,0)
    
    days = start/(24*60*60)
    delta = dt.timedelta(days)
    offset = day_zero+delta
    start = offset.strftime('%Y-%m-%d')
    time_list['start'] = start

    days = end/(24*60*60)
    delta = dt.timedelta(days)
    offset = day_zero+delta
    end = offset.strftime('%Y-%m-%d')
    time_list['end'] = end

    with open(dirs['plots_dir']+'run_time.json', 'w') as i:
        json.dump(time_list, i)

    status = 'run time json written successfully'
    return status

#Plot time series as a graph and save as png in output directory    
def plot_timeseries(time_series, dirs, station_ind, args):
    status = 'unable to plot time series graphs......'
    with open(dirs['plots_dir']+'run_time.json', 'r') as i:
        times = json.load(i)
    start_time = times["start"]
    Date_1900 = dt.datetime(1900,1,1,0,0,0,0)
    fmt='%Y-%m-%d'
    DateTime = datetime.strptime(start_time,fmt)
    diff = DateTime - Date_1900
    days, seconds = diff.days, diff.seconds
    hours = days *24 + (seconds // 3600)
    seconds = hours*60*60

    for key in time_series: 
        thres = station_ind[key][2]
        plt.rc('font', size=18)
        plt.figure(key,figsize=[15,15])
        plt.title('Forecast for '+key+' starting on '+start_time,fontsize=20)
        plt.xlabel('Hours')
        plt.ylabel('Elevation (m)')
        
        plt.axhline(y=thres, color = 'r', linestyle='--', label= 'Threshold exceedance level')
        x_axis = time_series[key][:,0]
        x_axis = x_axis - seconds
        x_axis = x_axis/(60*60)
        #plt.annotate('threshold level', xy=(10,thres), xytext=(11, thres+0.5), arrowprops = dict(facecolor='black', shrink=0.05),)
        plt.plot(x_axis, time_series[key][:,1], label='Sea surface height')
        plt.legend()
        plt.grid(True)
        plt.show()
        plt.savefig(dirs['plots_dir']+key+'_'+start_time+"_sea_surface_height.png",bbox_inches='tight')
        
    status = 'time series plot generation successful'
    return status
# Produce spatial plots of SSH at the defined interval from YAML config file
def plot_SSH(dataset_name, args, lat, lon, dirs):
    status = 'unable to plot sea surface height maps'
    num_steps = (60*60)/args['time_step']
    time = np.arange(0, (args['tot_t']*num_steps), args['interval'])    
    maxlat = max(lat)
    minlat = min(lat)
    maxlon = max(lon)
    minlon = min(lon)
    f = Dataset(dataset_name)
    time_l = len(time)
    images = []
    with open(dirs['plots_dir']+'run_time.json', 'r') as i:
        times = json.load(i)
    start_time = times["start"]
    fmt='%Y-%m-%d'
    start_time = datetime.strptime(start_time,fmt)
    for i in range(time_l):
        plt.figure(figsize=[15,18])  # a new figure window
        ax = plt.subplot(111, projection=ccrs.PlateCarree())  # specify (nrows, ncols, axnum)
        ax.set_extent([minlon,maxlon,minlat,maxlat],crs=ccrs.PlateCarree()) #set extent
        ax.set_title('Total Sea Surface Height', fontsize=20) #set title
        ax.add_feature(cartopy.feature.LAND, zorder=0) #add land polygon
        ax.add_feature(cartopy.feature.COASTLINE, zorder=10) #add coastline polyline
        progress_time = start_time + timedelta(seconds = int(time[i])*args['time_step'])
        FMT = '%d %b %Y %H:%M'
        progress_time = progress_time.strftime(FMT)
        plt.text((minlon+1.75),(maxlat-1.75),progress_time,fontsize=20,bbox=dict(facecolor='cyan', boxstyle='round'))
        ssh = f.variables["zos"][time[i],:,:] #extract ssh from netcdf file

        gl = ax.gridlines(crs=ccrs.PlateCarree(), linewidth=2, color='black', alpha=0.5, linestyle='--', draw_labels=True)
        gl.xlabel_style = {'size': 18, 'color': 'black'}
        gl.ylabel_style = {'size': 18, 'color': 'black'}
        gl.xlabels_top = False #no xlabels at top
        gl.ylabels_left = False #no y labels on left
        # make a color map of fixed colors
        cmap = c.ListedColormap(['#00004c','#000080','#0000b3','#0000e6','#0026ff','#004cff',
                         '#0073ff','#0099ff','#00c0ff','#00d900','#33f3ff','#73ffff','#c0ffff', 
                         (0,0,0,0),
                         '#ffff00','#ffe600','#ffcc00','#ffb300','#ff9900','#ff8000','#ff6600',
                         '#ff4c00','#ff2600','#e60000','#b30000','#800000','#4c0000'])
        #define bounds for colour bar
        bounds=[-2,-1,-0.75,-0.50,-0.30,-0.25,-0.20,-0.15,-0.1,-0.05,0.05,0.1,0.15,0.20,0.25,0.30,0.50,0.75,1,2]
        norm = c.BoundaryNorm(bounds, ncolors=cmap.N) # cmap.N gives the number of colors of your palette
        #prodice contour data to plot using colour map, norm and defined bounds
        mm = ax.contourf(lon,lat,ssh, transform=ccrs.PlateCarree(), cmap=cmap,norm=norm, levels=bounds)
        ## make a color bar
        cbar = plt.colorbar(mm, cmap=cmap,norm =norm,boundaries=bounds, ticks=bounds, ax=ax, orientation='horizontal', pad=0.05)
        cbar.ax.set_xticklabels(cbar.ax.get_xticklabels(), rotation='vertical')
        #save figure as png file in output folder
        plt.savefig(dirs['animation_plots_dir']+args['config_name']+"_"+str(time[i])+"_sea_surface_height.png",bbox_inches='tight')
        #show plot (still needed?)
        plt.show()
        images.append(imageio.imread(dirs['animation_plots_dir']+args['config_name']+"_"+str(time[i])+"_sea_surface_height.png"))
    output_file = args['config_name']+'_SSH_Animation_0_to_'+str(args['tot_t'])+'_hours.gif'
    imageio.mimsave(dirs['plots_dir']+output_file, images, duration=1.0)
    #close netcdf file
    f.close()
    status = 'sea surface height graph plotting successful'
    return status

#Function to create spatial plot showing station locations. Red dots show the lat and long locations for each time series.    
def plot_station_locations(dirs, args, stations, lat, lon):
    status = 'unable to plot station location map'
    ymd = arrow.now().format('YYYY-MM-DD-HH')
    maxlat = max(lat)
    minlat = min(lat)
    maxlon = max(lon)
    minlon = min(lon)       
    plt.figure(figsize=[15,18])  # a new figure window
    ax = plt.subplot(111, projection=ccrs.PlateCarree())  # specify (nrows, ncols, axnum)
    ax.set_extent([minlon,maxlon,minlat,maxlat],crs=ccrs.PlateCarree())
    ax.set_title('Time Series Locations', fontsize=20)
    land_50m = cartopy.feature.NaturalEarthFeature('physical', 'land', '50m',
                                        edgecolor='k',
                                        facecolor=cartopy.feature.COLORS['land'])
    ax.add_feature(land_50m)
    ax.add_feature(cartopy.feature.LAKES)
    ax.add_feature(cartopy.feature.OCEAN)
    ax.add_feature(cartopy.feature.BORDERS)
    ax.add_feature(cartopy.feature.RIVERS)
    ax.coastlines(resolution='50m')
    gl = ax.gridlines(crs=ccrs.PlateCarree(), linewidth=2, color='black', alpha=0.5, linestyle='--', draw_labels=True)
    gl.xlabel_style = {'size': 16, 'color': 'black'}
    gl.ylabel_style = {'size': 16, 'color': 'black'}
    gl.xlabels_top = False
    gl.ylabels_left = False
    num_stations = len(stations)
    for f in range(num_stations):
        lat_station = float(stations[f][2])
        lon_station = float(stations[f][3])
        station = stations[f][0]         
        ax.plot(lon_station, lat_station, 'ro', markersize=15, transform=ccrs.Geodetic())
        ax.text((lon_station+0.33), (lat_station+0.33), station, transform=ccrs.PlateCarree(), fontsize=16)
        
    plt.savefig(dirs['plots_dir']+args['config_name']+"_"+"station_locations.png",bbox_inches='tight')

    plt.show()
    status = 'station location map plot successful'
    return status
#check for threshold exccedance across whole domain as defined in YAML config file
#This still needs work, only outputs model time interval not time in UTC or location
def global_thres_exccedance_check(time_series, args):
    for key in time_series:
        check_elev = time_series[key][:,1]
        c = [n > args['global_thres'] for n in check_elev]
        idx = [i for i, x in enumerate(c) if x]        
        sum_c = sum(c)
        if sum_c > 0:
            status = "Global threshold exceeded at interval "+str(idx)+"!"
        else:
            status = "Global threshold not exceeded"
        return status
#Function to check for threshold exceedance at station locations 
def check_thres_station(time_series, station_ind, dirs, args):
    with open(dirs['plots_dir']+'run_time.json', 'r') as i:
        times = json.load(i)
    start_time = times["start"]
    thres_check = {}
    interval = 1
    exceed = {}

    for key in time_series:
        check_elev = time_series[key][:,1]
        thres = station_ind[key][2]
        c = [n > thres for n in check_elev]
        idx = [i for i, x in enumerate(c) if x]       
        sum_c = sum(c)

        with open(dirs['plots_dir']+'run_time.json', 'r') as i:
            times = json.load(i)
        start_time = times["start"]
        start = dt.datetime.strptime(start_time, '%Y-%m-%d')

        for i in range(len(idx)):
            if i == (len(idx)-1):
                break
            diff = np.abs(idx[i]-idx[i+1])
            if diff == 1:
                #add to current interval
                interval = interval + 1
            else:
                #create new interval
                sim_time = str(start + timedelta(seconds=idx[i]*args['time_step']))
                thres_e = str(timedelta(seconds=int(interval*args['time_step'])))
                exceed[sim_time] = thres_e
                interval = 1

        thres_check[key] = exceed
        exceed.clear()

        if sum_c > 0:
            status = "threshold exceeded see json file"
        else:
            status = "threshold not exceeded"

    with open(dirs['csv_dir']+start_time+'_thres_check.json','w') as f:
        json.dump(thres_check,f)
    return status

#Export CSV files for each station location into output folder
def export_csv(time_series, args, dirs):
    with open(dirs['plots_dir']+'run_time.json', 'r') as i:
        times = json.load(i)
    start_time = times["start"]
    try:
        for key in time_series:
            pd.DataFrame(time_series[key]).to_csv(dirs['csv_dir']+key+'_'+start_time+'_time_series.csv', index=False, header = ['time, seconds from 1900','sea surface height (m)'])
        status = 'csv export successful'
    except IOError:
        status = 'unable to export csv files of station locations'
    return status
# move model output netcdf file to output folder
def move_netcdf(dirs, dataset_name):
    hr = arrow.now().format('HH')
    status = 'unable to move netcdf file'
    output = dataset_name.split('/')
    output = output[-1]
    result = dirs['netcdf_dir']+hr+'_'+output
    shutil.copy(dataset_name, result)
    status = 'netcdf file copied to output folder successfully'
    return status

if __name__ == '__main__':
    main()  # pragma: no cover
