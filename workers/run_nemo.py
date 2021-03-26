#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tues Aug 28 13:41:34 2018

@author: thopri
"""

# Copyright 2021 Thopri National Oceanography Centre

"""
NEMO weather model run NEMO worker

Worker takes the processed boundary files, creates the runtime files required and starts the NEMO model

"""

import glob
import logging
import shlex
import shutil
import json
from pathlib import Path
import os
import sys
import arrow
import datetime as dt
from datetime import datetime
import calendar
import re
from subprocess import Popen, PIPE
from argparse import ArgumentParser
import yaml
from time import sleep
import json
import glob
import time
import datetime

#main function to run the NEMO model
def main(config_loc=''):
    # start = time.time()
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
    code1,timestamp1 = exit_code(config,'process_forcing','0')
    if code1 != '0':
        print('unable to find a successful run of previous worker, terminating now')
        sys.exit(1)
    code2,timestamp2 = exit_code(config,'run_nemo','0')
    if code2 == -1:
        print('no log for previous run found, assume first start')
        args.force = True

    if args.force == False:
        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        if timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True

    # list_of_files = glob.glob(config['netcdf_dir'] + '*')  # * means all if need specific format then *.csv
    # mtimes = 0
    # for file in list_of_files:
    #     mtime = os.path.getmtime(file)
    #     if start - mtime <= (POLL/1000*1.25):
    #         mtimes = mtimes + 1
    # if mtimes >= 3:
    #     print('new netcdf data found, running run NEMO worker now....')
    #     args.force = True

    if args.force == True:
        #get start date in specified format
        start_ymd = arrow.now().format('YYYY-MM-DD-HH')
        print(start_ymd)
        delete = delete_old_fluxes(config) #remove old flux boundary files
        print(delete)
        move = move_netcdf_files(config) #move netcdf boundary files to flux folder
        print(move)
        params = process_filename(config) #read config parameters from filename
        print(params)
        move1 = move_weight_files(config) #move weight files to flux folder
        print(move1)
        weight_vars = read_weight_vars(config) #read weight parameters from files and populate dictionary
        leap = is_leap(params)# is it a leap year?
        day_str = day_of_the_week(params) #generate a string of correct format specifying day of the week
        if config['restart'] == True:
            print('restart flag enabled, using restart file.......')
            print('checking timestep log .........')
            timesteps, date0 = read_timestep_log(config, params)
            nn_it000 = timesteps + 1
            #nn_it000 = read_nn_it000(args, dirs)
            nn_itend = calc_nn_itend(config, timesteps) #length of simulation in time steps
            restart_length = length_restart(config, timesteps)
            restart_write = write_restart(config)
        else:
            print('restart disabled, starting new timestep log.......')
            with open(config['config_dir']+'timestep_log.json','w') as fp:
                json.dump(params, fp)
            nn_it000 = 1
            date0 = params['year']+params['month']+params['day']
            nn_itend = int(sim_length(config) - (3600/config['time_step']))
            restart_length = length_restart(config, nn_it000)
            restart_write = write_restart(config)
        pop_namelist(config, params, leap, weight_vars, nn_itend, day_str, restart_length, nn_it000, restart_write, date0) #populate namelist file with
        #all the required parameters to run the model, (start and end date etc)
        #start the model
        start_nemo(config)
        print('nemo model started')
        print('sleeping for 1 min to allow container to start')
        sleep(60)
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
        config_file = yaml.safe_load(f)
    config = config_file['RUN_NEMO']
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
    dt_timestamp1 = datetime.datetime.strptime(timestamp1,"%Y-%m-%dT%H:%M:%S")
    dt_timestamp2 = datetime.datetime.strptime(timestamp2,"%Y-%m-%dT%H:%M:%S")
    if dt_timestamp1 > dt_timestamp2:
        return True
    else:
        return False

#Function to move weighted NETCDF files to flux folder
def move_weight_files(config):
    src_files = os.listdir(config['weights_dir'])
    dest = config['boundary_dest']
    err = 'unable to move weighted files'
    for file_name in src_files:
        full_file_name = os.path.join(config['weights_dir'], file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, dest)
    err = 'weighted files moved successfully'
    return err
#Move nefcdf boundary files to flux folder
def move_netcdf_files(config):
    src_files = os.listdir(config['netcdf_dir'])
    dest = config['boundary_dest']
    err = 'unable to move netcdf files'
    for file_name in src_files:
        full_file_name = os.path.join(config['netcdf_dir'], file_name)
        if (os.path.isfile(full_file_name)):
            copy_file_name = file_name[:-6]
            copy_file_name = copy_file_name+'.nc'
            copy_file_name = dest + copy_file_name
            shutil.copy(full_file_name, copy_file_name)
    err = 'netcdf files moved successfully'
    return err    
#Process boundary filename to get the parameters for model run
def process_filename(config):
    list_of_files = glob.iglob(config["netcdf_dir"]+'*')
    latest_file = max(list_of_files, key=os.path.getctime)
    config,var,date = str.split(latest_file, '_')
    date = date[:-3]
    year = date[1:5]
    month = date[6:8]
    day = date[9:11]
    hour = date[12:14]
    config = str.split(config,'/')
    config = config[-1]
    
    return {'config' : config, 'var' : var, 'year' : year, 'month' : month, 'day' : day, 'hour' : hour }
#Calculate day of the week as a string
def day_of_the_week(params):
    year = int(params['year'])
    month = int(params['month'])
    day = int(params['day'])
    weekday = dt.date(year, month, day).weekday()
    days = {
        0 : 'mon',
        1 : 'tues',
        2 : 'weds',
        3 : 'thurs',
        4 : 'fri',
        5 : 'sat',
        6 : 'sun'       
        }
    day_str = days[weekday]
    
    return day_str    
#is it a leap year? (this currently always says true as false creates problems with model config)
def is_leap(params):
    isleap = calendar.isleap(int(params['year']))
    isleap = int(isleap)
    isleap = 1
    return isleap
#calculate length of simulation in model timesteps e.g. how many 6 mins are there in 120 hours?
def calc_nn_itend(config, timesteps):
    dt_hr = config['time_step']/(60*60)
    nn_itend_init = int(config['duration']/dt_hr)
    nn_itend = nn_itend_init + timesteps
    nn_itend = int(nn_itend - (3600/config['time_step']))
    if nn_itend >= 99999999:
        print('Out of Steps Error: run model with restart disabled (False) to reset timesteps')
        nn_itend = 'NaN'
    return nn_itend

def sim_length(config):
    dt_hr = config['time_step']/(60*60)
    sim_length = int(config['duration']/dt_hr)
    return sim_length

def write_restart(config):
    dt_hr = config['time_step']/(60*60)
    restart_write = int(config['restart_int']/dt_hr)
    return restart_write  

def length_restart(config, timesteps):
    #dt_hr = args['time_step']/(60*60)
    #restart_length = args['restart_int']/dt_hr
    #restart_length = int(restart_length + nn_it000 - 1) 
    restart_length = timesteps
    restart_length = format(restart_length, '08d')
    return restart_length

#def read_nn_it000(args, dirs):
#    list_of_files = glob.iglob(dirs["restart_dir"]+'*.nc')
#    oldest_file = min(list_of_files, key=os.path.getctime)
#    restart_name = oldest_file
#    nn_it000 = restart_name.split('_')
#    nn_it000 = nn_it000[2]
#    nn_it000 = nn_it000.lstrip('0')
#    nn_it000 = int(nn_it000)
#    nn_it000 = nn_it000 + 1
#    return nn_it000

def read_timestep_log(config,params):
    with open(config['config_dir']+'timestep_log.json','r') as f:
        t_log = json.load(f)
    t0 = t_log['year']+'-'+t_log['month']+'-'+t_log['day']+'-'+str(config['hour_start'])
    current_t = params['year']+'-'+params['month']+'-'+params['day']+'-'+str(config['hour_start'])
    FMT = '%Y-%m-%d-%H'
    tdelta = datetime.strptime(current_t,FMT)-datetime.strptime(t0,FMT)
    tdelta_sec = tdelta.total_seconds()
    timesteps = int(tdelta_sec/config['time_step'])
    date0 = t_log['year']+t_log['month']+t_log['day']
    return timesteps, date0

#Read the weight netcdf file names to get the required variables to populate namelist file
def read_weight_vars(config):
    list_of_files = glob.iglob(config["weights_dir"]+'*')
    r = re.compile(config['var1'])
    file1 = list(filter(r.match, list_of_files))
    list_of_files = glob.iglob(config["weights_dir"]+'*')
    r = re.compile(config['var2'])
    file2 = list(filter(r.match, list_of_files))
    list_of_files = glob.iglob(config["weights_dir"]+'*')
    r = re.compile(config['var3'])
    file3 = list(filter(r.match, list_of_files))

    file1 = str.split(str(file1), '/')
    file1 = file1[-1]
    full_file_name1 = file1[:-2]
    file1 = str.split(file1, '_')
    var1 = file1[1]
    name_short1 = file1[0] +'_'+file1[1]

    file2 = str.split(str(file2), '/')
    file2 = file2[-1]
    full_file_name2 = file2[:-2]
    file2 = str.split(file2, '_')
    var2 = file2[1]
    name_short2 = file2[0] +'_'+file2[1]

    file3 = str.split(str(file3), '/')
    file3 = file3[-1]
    full_file_name3 = file3[:-2]
    file3 = str.split(file3, '_')
    var3 = file3[1]
    name_short3 = file3[0] +'_'+file3[1]

    return {'full_file_name1' : full_file_name1, 
            'full_file_name2' : full_file_name2,
            'full_file_name3' : full_file_name3,
            'name_short1' : name_short1,
            'name_short2' : name_short2,
            'name_short3' : name_short3,
            'var1' : var1,
            'var2' : var2,
            'var3' : var3,
            }
#Populate namelist file with strings calculated from input filenames
def pop_namelist(config, params, leap, weight_vars, nn_itend, day_str, restart_length, nn_it000, restart_write, date0):
    start_ymd = arrow.now().format('YYYY-MM-DD')
# Read in the file
    with open(config["config_dir"]+config['namelist_template'], 'r') as file :
      filedata = file.read()
    # Replace the target string
    filedata = filedata.replace('key_A', config['config_name'])
    filedata = filedata.replace('key_B', str(nn_itend))
    filedata = filedata.replace('key_C', date0)
    filedata = filedata.replace('key_D', params['hour'])
    filedata = filedata.replace('key_E', str(leap))
    filedata = filedata.replace('key_F', str(config['restart']))
    filedata = filedata.replace('key_G', weight_vars['name_short1'])
    filedata = filedata.replace('key_H', weight_vars['var1'])
    filedata = filedata.replace('key_I', day_str)
    filedata = filedata.replace('key_J', weight_vars['full_file_name1'])
    filedata = filedata.replace('key_K', weight_vars['name_short2'])
    filedata = filedata.replace('key_L', weight_vars['var2'])
    filedata = filedata.replace('key_M', weight_vars['full_file_name2'])
    filedata = filedata.replace('key_N', weight_vars['name_short3'])
    filedata = filedata.replace('key_O', weight_vars['var3'])
    filedata = filedata.replace('key_P', weight_vars['full_file_name3'])
    filedata = filedata.replace('key_Q', str(restart_length))
    filedata = filedata.replace('key_R', str(nn_it000))
    filedata = filedata.replace('key_S', str(restart_write))
    filedata = filedata.replace('key_T', str(config['hour_start'])+'00')

    # Write the file out again
    with open(config["config_dir"]+config['pop_namelist'], 'w') as file:
      file.write(filedata)

    checklist = {f'{start_ymd} namelist_cfg file populated'}
    return 0
#remove old files from previous runs from flux folder
def delete_old_fluxes(config):
    status = 'unable to delete old flux files'
    shutil.rmtree(config['boundary_dest'])
    os.makedirs(config['boundary_dest'])
    status = 'flux files deleted successfully'
    return status    
#start the model, and direct terminal output into log file that is indivdually dated
def start_nemo(config):
    start_ymd = arrow.now().format('YYYY-MM-DD-HH-MM-SS')
    if config['container'] == 'podman':
        os.system('podman run --rm -v '+config['container_mount']+':/'+config['container_dir']+':z '
                  +config['container_name']+' &> '+config['container_log']+'containerlog-'+start_ymd+'.txt &')
    if config['container'] == 'docker':
        os.system('docker run --rm -v '+config['container_mount']+':/'+config['container_dir']+' '
                  +config['container_name']+' &> '+config['container_log']+'containerlog-'+start_ymd+'.txt &')

if __name__ == '__main__':
    main()  # pragma: no cover

