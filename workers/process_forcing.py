#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 13:41:34 2018

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
"""C-RISC NEMO nowcast weather model products download worker.

Processes GRIB filter files from NOAA GFS model as specified in the YAML Nowcast file, converts
the hourly files in to netcdf files suitable to use in NEMO. I.e. hours on concatinated into a single
netcdf with each parameter having its own file.


"""
import logging
import os
from pathlib import Path
import time
import datetime
import shutil
import arrow
import requests
import sys
import pygrib
import netCDF4 as nc
import numpy as np
import glob
import yaml
from argparse import ArgumentParser
import json
from time import sleep
import glob

#Process Forcing function to convert the hourly GRIB files into combined NETCDF file for each variable
def main(config_loc=''):
    #start = time.time()
    if config_loc == '':
        parser = ArgumentParser(description='RUN NEMO worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()
        if args.force == True:
            print('force flag enabled, running worker now....')
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    if args.force == False:
    	code1,timestamp1 = exit_code(config,'download_weather','0')
    	if code1 != '0':
        	print('unable to find a successful run of previous worker, terminating now')
        	sys.exit(1)
    	code2,timestamp2 = exit_code(config,'process_forcing','0')
    	if code2 == -1:
        	print('no log for previous run found, assume first start')
        	args.force = True

        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        print(timestamp1)
        print(timestamp2)
        if timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True

    # ymd = arrow.now().format('YYYY-MM-DD') #Get current data in given format
    #
    # list_of_files = glob.glob(config['forcing']['process']['grib_dir']+'*')  # * means all if need specific format then *.csv
    # if len(list_of_files) != config['forcing']['process']['forecast_hrs']:
    #     print('there are no enough GRIB files to cover forecast hours, program terminating')
    #     sys.exit(1)
    # mtimes = 0
    # for file in list_of_files:
    #     mtime = os.path.getmtime(file)
    #     if start-mtime <= (POLL/1000*1.25):
    #         mtimes = mtimes + 1
    # if mtimes == config['forcing']['process']['forecast_hrs']:
    #     print('new grib data found, running process forcing worker now....')
    #     args.force = True

    if args.force == True:
        dir = dir_gen(config) #get directory values from YAML file
        model_run = ModelRun(dir) #Calculate the model run hour by finding the latest GRIB download
        arg = arg_gen(config, model_run)#get command arguments from YAML file
        t = ForeCast(arg) #Generate list of file forcast numbers in a specifc format
        i = 0
        lats, lons = getlatandlon(config, arg, dir, model_run, t, i) #get lat and lon values from a GRIB file
        delete = delete_old_netcdf(dir) #remove any existing NETCDF files from destination folder
        #The C parameter refers to the three variable NETCDF files that need to created, for a value of 0, 1, and 2
        #a different variable netcdf file is created.
        C = 0
        createNetCDF(lats, lons, dir, C, arg) #create empty NETCDF file with correct dimensions and variables
        loaddataNetCDF(config, arg, dir, model_run, t, i, C) #Load data into created NETCDF file
        C = 1
        createNetCDF(lats, lons, dir, C, arg)
        loaddataNetCDF(config, arg, dir, model_run, t, i, C)
        C = 2
        createNetCDF(lats, lons, dir, C, arg)
        loaddataNetCDF(config, arg, dir, model_run, t, i, C)
        print('GRIB files successfully processed')
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
        with open(config['forcing']['process']['pm2log'], 'r') as f:
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
        with open(config['forcing']['process']['pm2log'], 'r') as f:
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
    dt_timestamp1 = datetime.datetime.strptime(timestamp1,"%Y-%m-%dT%H:%M:%S")
    dt_timestamp2 = datetime.datetime.strptime(timestamp2,"%Y-%m-%dT%H:%M:%S")
    if dt_timestamp1 > dt_timestamp2:
        return True
    else:
        return False

#Function to calculate the number of hours since 1900 for a given model run
#This is used convert the UTC time of the GRIB forecast data into time understood by the NEMO model.
def hourssince1900(config, arg, dir, model_run, t, i):
    filename = dir["grib_dir"]+arg["file_template"]+str(t[i])    
    filename = filename.format(**arg)
    grbs = pygrib.open(filename)
    grb = grbs.select(name=arg["var1_des"])[0]
    Date_1900 = datetime.datetime(1900,1,1,0,0,0,0)
    DateTime = datetime.datetime(grb.validDate.year, grb.validDate.month, grb.validDate.day, grb.validDate.hour, 0,0,0)
    diff = DateTime - Date_1900
    days, seconds = diff.days, diff.seconds
    hours = days *24 + (seconds // 3600)
    return hours

#Function to get lat and lon values from latest GRIB file
def getlatandlon(config, arg, dir, model_run, t, i):
    filename = dir["grib_dir"]+arg["file_template"]+str(t[i])
    filename = filename.format(**arg)    
    grbs = pygrib.open(filename) 
    grb = grbs.select(name=arg["var1_des"])[0]
    lats,lons = grb.latlons() 
    lats = lats[:,0]
    lats = np.flip(lats,0)
    lons = lons[0,:]
    return lats,lons
#generate command arguments for worker from YAML file
def arg_gen(config, model_run):
    arguments = {
        'forecast_hrs' : config['forcing']['process']['forecast_hrs'],
        'var1' : config['forcing']['process']['var1'],
        'var2' : config['forcing']['process']['var2'],
        'var3' : config['forcing']['process']['var3'],
        'var1_des' : config['forcing']['process']['var1_des'],
        'var2_des' : config['forcing']['process']['var2_des'],
        'var3_des' : config['forcing']['process']['var3_des'],
        'file_template' : config['forcing']['process']['file_template'],
        'model_run' : model_run,
        'hours' : '{hours}'
        }   
    return arguments
#Generate command arguments from YAML file for directory locations
def dir_gen(config):
    arguments = {
        'netcdf_dest_dir' : config['forcing']['process']['netcdf_dest_dir'],
        'grib_dir' : config['forcing']['process']['grib_dir'],
        'netcdf_name' : config['forcing']['process']['netcdf_name'],
        }   
    return arguments
#Function to generate forcast numbers in a specific format, required to find GRIB files
def ForeCast(arg):
    f = []
    for i in range(int(arg["forecast_hrs"])):
        f.insert(i, '{0:03}'.format(i)) 
    return f

#Function to identify the model run of the lastest download files. Specifically the hour run, 
#The GFS model is run at 00, 06, 12 and 18 hours.
def ModelRun(dir):
    list_of_files = glob.glob(dir["grib_dir"]+'/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    hour = latest_file[-19:-17]
    #hour = '00'
    return hour

#Create empty NETCDF files for each variable with the correct dimensions and meta data, units etc
#The C parameter defines which variable the file is prepared for
def createNetCDF(lats, lons, dir, C, arg):
    #get current date in specified format
    ymd = arrow.now().format('YYYY-MM-DD')
    #C parameter defines which variable to use in creating empty file
    if C == 0:
        #create empty netcdf file in desired location with specified file name
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var1"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'w', format = 'NETCDF3_CLASSIC')
        #create required dimensions, the spatial lat and lon need to be defined but time does not require a length (Classic NETCDF allows one unbound dimension)
        force.createDimension('lat', len(lats))
        force.createDimension('lon', len(lons))
        force.createDimension('time', None)
        #create required variables to insert into file, spatial lat and lon, the variable itself and time are required
        longitude = force.createVariable('longitude','f4', 'lon')
        latitude = force.createVariable('latitude','f4', 'lat')
        var = force.createVariable(arg['var1'], 'f4', ('time', 'lat', 'lon'))
        time = force.createVariable('time', 'i4', 'time')
        #insert lat and lon data into netcdf file
        longitude[:] = lons[:]
        latitude[:] = lats[:]
        #add description of file, what the variable is, and where the data comes from
        force.description = "Dataset of NCEP GFS Forecast (0.25 degree grid) "+str(arg['var1_des'])
        force.history = "Created on " + str(datetime.date.today())
        #add units and long names of variables    
        longitude.units = 'degrees east'
        longitude.long_name = 'longitude'
        latitude.units  = 'degrees north'
        latitude.long_name = 'latitude'
        time.units = 'hours since 01-01-1900'
        time.long_name = 'time'
        var.units = 'm s**-1'
        var.long_name = arg['var1_des']
        #close netcdf file
        force.close()
        #write to nowcast log
    if C == 1:
        
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var2"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'w', format = 'NETCDF3_CLASSIC')
        
        force.createDimension('lat', len(lats))
        force.createDimension('lon', len(lons))
        force.createDimension('time', None)
            
        longitude = force.createVariable('longitude','f4', 'lon')
        latitude = force.createVariable('latitude','f4', 'lat')
        var = force.createVariable(arg['var2'], 'f4', ('time', 'lat', 'lon'))
        time = force.createVariable('time', 'i4', 'time')
        
        longitude[:] = lons[:]
        latitude[:] = lats[:]
        
        force.description = "Dataset of NCEP GFS Forecast (0.25 degree grid)" +str(arg['var2_des'])
        force.history = "Created on " + str(datetime.date.today())
            
        longitude.units = 'degrees east'
        longitude.long_name = 'longitude'
        latitude.units  = 'degrees north'
        latitude.long_name = 'latitude'
        time.units = 'hours since 01-01-1900'
        time.long_name = 'time'
        var.units = 'm s**-1'
        var.long_name = arg['var2_des']
        force.close()
    if C == 2:
        
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var3"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'w', format = 'NETCDF3_CLASSIC')
        
        force.createDimension('lat', len(lats))
        force.createDimension('lon', len(lons))
        force.createDimension('time', None)
            
        longitude = force.createVariable('longitude','f4', 'lon')
        latitude = force.createVariable('latitude','f4', 'lat')
        var = force.createVariable(arg['var3'], 'f8', ('time', 'lat', 'lon'))
        time = force.createVariable('time', 'i4', 'time')
        
        longitude[:] = lons[:]
        latitude[:] = lats[:]
        
        force.description = "Dataset of NCEP GFS Forecast (0.25 degree grid)"+str(arg['var3_des'])
        force.history = "Created on " + str(datetime.date.today())
            
        longitude.units = 'degrees east'
        longitude.long_name = 'longitude'
        latitude.units  = 'degrees north'
        latitude.long_name = 'latitude'
        time.units = 'hours since 01-01-1900'
        time.long_name = 'time'
        var.units = 'Pa'
        var.long_name = arg['var3_des']
        force.close()

#Function to write data from all the hourly GRIB files into the prepared NETCDF file.
#The C parameter defines which variable is written.    
def loaddataNetCDF(config, arg, dir, model_run, t, i, C):
    #get current date in the specifed format
    ymd = arrow.now().format('YYYY-MM-DD')
    #The C parameter determines which variable is written to the netcdf file
    if C == 0:
        #open netcdf file in the desired location with desired filename
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var1"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'a')
        #For each of the hourly GRIB files......
        for i in range(int(arg["forecast_hrs"])):
            print('writing hour '+str(i+1)+' for variable '+str(arg["var1"])+' to file')
            #read the GRIB filename from the YAML config file
            filename = dir["grib_dir"]+arg["file_template"]+str(t[i])
            #filename = '/Volumes/projectsa/C_RISC/TEST/gfs.t06z.pgrb2.0p25.f'+str(t[i])
            #create file name from YAML config, and i index parameter
            filename = filename.format(**arg)
            #open the GRIB file
            grbs = pygrib.open(filename)
            #select the desired variable
            grb = grbs.select(name=arg["var1_des"])[0]
            #extract the data
            var = grb.values
            #Flip the extracted data
            var = np.flip(var,0)
            #insert data into NETCDF file variable
            var1 = force.variables[arg['var1']]        
            var1[i,:,:] = var[:,:]
            #convert time into hours since 1900
            time_num = hourssince1900(config, arg, dir, model_run, t, i)
            #insert into NETCDF file
            time = force.variables['time']
            time[i] = time_num
        #close netcdf file
        force.close()
        #write to Nowcast Logger
            
    if C == 1:
        
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var2"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'a')
       
        for i in range(int(arg["forecast_hrs"])):
            print('writing hour ' + str(i + 1) + ' for variable ' + str(arg["var2"]) + ' to file')
            filename = dir["grib_dir"]+arg["file_template"]+str(t[i])
            #filename = '/Volumes/projectsa/C_RISC/TEST/gfs.t06z.pgrb2.0p25.f'+str(t[i])
            filename = filename.format(**arg)
            grbs = pygrib.open(filename) 
            grb = grbs.select(name=arg["var2_des"])[0]
            var = grb.values
            var = np.flip(var,0)
            var2 = force.variables[arg['var2']]
            var2[i,:,:] = var[:,:]
            time_num = hourssince1900(config, arg, dir, model_run, t, i)
            time = force.variables['time']
            time[i] = time_num
        force.close()
    if C == 2:
        
        force = nc.Dataset(dir["netcdf_dest_dir"]+dir["netcdf_name"]+'_'+arg["var3"]+'_y'+ymd[0:4]+'m'+ymd[5:7]+'d'+ymd[8:10]+'h'+arg['model_run']+'.nc', 'a')
       
        for i in range(int(arg["forecast_hrs"])):
            print('writing hour ' + str(i + 1) + ' for variable ' + str(arg["var3"]) + ' to file')
            filename = dir["grib_dir"]+arg["file_template"]+str(t[i])
            #filename = '/Volumes/projectsa/C_RISC/TEST/gfs.t06z.pgrb2.0p25.f'+str(t[i])
            filename = filename.format(**arg)
            grbs = pygrib.open(filename) 
            grb = grbs.select(name=arg["var3_des"])[0]
            var = grb.values
            var = np.flip(var,0)
            var3 = force.variables[arg['var3']]
            var3[i,:,:] = var[:,:]
            time_num = hourssince1900(config, arg, dir, model_run, t, i)
            time = force.variables['time']
            time[i] = time_num
        force.close()
#Function to purge old NETCDF files from previous model runs.
def delete_old_netcdf(dir):
    status = 'unable to delete old netcdf files'
    shutil.rmtree(dir['netcdf_dest_dir'])
    os.makedirs(dir['netcdf_dest_dir'])
    status = 'old netcdf file removal successful'
    return status

if __name__ == '__main__':
    main()  # pragma: no cover
