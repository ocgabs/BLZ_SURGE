#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tues Aug 28 13:41:34 2018

@author: thopri
"""

# Copyright 2021 Thopri National Oceanography Centre

"""
C-RISC NEMO nowcast weather model clean up worker

Worker cleans the model runtime directory and trims log and output files 
to ensure filespace limits are not reached


"""

from pathlib import Path
import os
import time
import sys
from argparse import ArgumentParser
import yaml
from subprocess import Popen,PIPE

#Main clean up function
def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='RUN NEMO worker')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    print('seeing if surge container is running....')
    container = chk_container(config)
    if container:
        print('container still running, terminating')
        sys.exit(7)

    #get todays date in the specifed format
    # logger_name is required because file system handlers get loaded below
    print('cleaning up workspace')
    dirs = dir_gen(config) #generate directory locations as per YAML config file
    args = args_gen(config) #generate command line arguments as per YAML config file
    print('############################################################')
    print('Removing Old Restart Files.....')
    trim_re = trim_restart_files(args, dirs)
    print(trim_re)
    print('############################################################')
    run = remove_run_files(args,dirs) #remove model runtime files
    print(run)
    print('############################################################')
    print('Removing Old Output Files.....')
    out_status,out_error = remove_output_file(args,dirs) #remove model output files
    print(out_status)
    print(out_error)
    print('############################################################')
    print('Removing Old Forcing Files.....')
    trim_for_rem,trim_for_keep,trim_for_err = trim_force_files(args,dirs)#trim log files to age as defined in YAML file
    print(trim_for_rem)
    print(trim_for_keep)
    print(trim_for_err)
    print('############################################################')
    print('Removing Old Log Files.....')
    trim_logs_rem,trim_logs_keep,trim_logs_err= trim_log_files(args,dirs)
    print(trim_logs_rem)
    print(trim_logs_keep)
    print(trim_logs_err)
    print('############################################################')
    print('Removing Old Sargassium Files.....')
    trim_sar_rem,trim_sar_keep,trim_sar_err = trim_sar_files(args,dirs)
    print(trim_sar_rem)
    print(trim_sar_keep)
    print(trim_sar_err)
    print('############################################################')
    print('Removing Old Output Files.....')
    trim_out_rem,trim_out_keep,trim_out_err = trim_output_files(args,dirs) #trim output files to age as defined in YAML file
    print(trim_out_rem)
    print(trim_out_keep)
    print(trim_out_err)
    print('worker ran successfully, exiting now')
    sys.exit(0)

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

def chk_container(config):
    cont = True
    container = Popen(['pgrep', 'nemo'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = container.communicate()
    stdout = stdout.decode('utf-8')
    if stdout == '':
	    cont = False
    #container = stdout.split('\n')
    #container = container[1].split(' ')
    #container = [x for x in container if x]
    #try:
    #    container_ID = container[0]
    #    container_name = container[1]
    #except IndexError:
    #    cont = False
    #    return container
    #if container_name != config['container_name']:
    #    cont = False
    return cont

#Generate directory locations as defined in YAML config file
def dir_gen(config): 
    dirs = {
            'run_dir' : config['clean']['up']['run_dir'],
            'forcing_dir' : config['clean']['up']['forcing_dir'],
            'log_dir': config['clean']['up']['log_dir'],
            'out_dir' : config['clean']['up']['out_dir'],
            'restart_dir' : config['clean']['up']['restart_dir'],
            'sargassium_dir': config['clean']['up']['sargassium_dir'],
            }
    return dirs
#Generate command arguments as defined in YAML config file
def args_gen(config):
    args = {
        'config_name' : config['clean']['up']['config_name'],
        'del_1' : config['clean']['up']['del_1'],
        'del_2' : config['clean']['up']['del_2'],
        'del_3' : config['clean']['up']['del_3'],
        'del_4' : config['clean']['up']['del_4'],
        'del_5' : config['clean']['up']['del_5'],
        'del_6' : config['clean']['up']['del_6'],
        'num_days' : config['clean']['up']['num_days'],
        'sub_1': config['clean']['up']['sub_1'],
        'sub_2': config['clean']['up']['sub_2'],
        'log_days' : config['clean']['up']['log_days'],
        'out_1' : config['clean']['up']['out_1'],
        'out_2' : config['clean']['up']['out_2'],
        'out_3' : config['clean']['up']['out_3'],

        }
    return args
#Function to remove model runtime files and circus process log file
def remove_run_files(args, dirs):
    status = 'run file remove not successful'
    num = 0
    err = 0
    try:
        os.remove(dirs['run_dir']+args['del_1'])
        num = num+1
    except IOError:
        err = err + 1
    try:
        os.remove(dirs['run_dir']+args['del_2'])
        num = num+1
    except IOError:
        err = err + 1
    try:
        os.remove(dirs['run_dir']+args['del_3'])
        num = num+1
    except IOError:
        err = err + 1
    try:
        os.remove(dirs['run_dir']+args['del_4'])
        num = num+1
    except IOError:
        err = err + 1
    try:
        os.remove(dirs['run_dir']+args['del_5'])
        num = num+1
    except IOError:
        err = err + 1
    try:
        os.remove(dirs['run_dir']+args['del_6'])
        num = num+1
    except IOError:
        err = err + 1
    # try:
    #     os.remove(dirs['log_dir']+args['circus_log'])
    #     num = num+1
    # except IOError:
    #     err = err + 1
    status = 'number of NEMO run files removed: '+str(num)
    return status
#Function to remove all model output files from model run directory
def remove_output_file(args, dirs):
    status = 'unable to remove model output file'
    run_files = os.listdir(dirs['run_dir'])
    num = 0
    err = 0
    for each_file in run_files:
        if each_file.startswith(args['config_name']):
            try:
                os.remove(dirs['run_dir']+each_file)
                num = num + 1
            except IOError:
                err = err + 1
    status = str(num)+' model output cleared from run directory'
    errors = str(err) + ' errors resulting from trying to delete files in run directory'
    return status,errors
    
#Trim each of the log sub directories to a defined interval specified in YAML config
def trim_force_files(args, dirs):
    current_time = time.time()
    status = 0
    new = 0
    error = 0
    try:
        for f in os.listdir(dirs['forcing_dir']+args['sub_1']):
            creation_time = os.path.getctime(dirs['forcing_dir']+args['sub_1']+f)
            if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
                try:
                    os.remove(dirs['forcing_dir']+args['sub_1']+f)
                    status = status + 1
                except IOError:
                    error = error + 1
            else:
                new = new + 1
    except UnboundLocalError:
        status1 = 'no force 1 files to trim'
        print(status1)
    try:
        for f in os.listdir(dirs['forcing_dir']+args['sub_2']):
            creation_time = os.path.getctime(dirs['forcing_dir']+args['sub_2']+f)
            if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
                try:
                    os.remove(dirs['forcing_dir']+args['sub_2']+f)
                    status = status + 1
                except IOError:
                    error = error + 1
            else:
                new = new + 1
    except UnboundLocalError:
        status2 = 'no force 2 files to trim'
        print(status2)
    files_rem = str(status)+' files removed from forcing directories'
    new_files = str(new)+' files kept in forcing directories'
    errors = str(error)+' errors trying to remove files from forcing directories'
    return files_rem,new_files,errors
#Trim each of the log sub directories to a defined interval specified in YAML config
def trim_sar_files(args, dirs):
    remove = 0
    keep = 0
    error = 0
    current_time = time.time()
    try:
        for f in os.listdir(dirs['sargassium_dir']):
            creation_time = os.path.getctime(dirs['sargassium_dir']+f)
            if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
                try:
                    os.remove(dirs['sargassium_dir']+f)
                    remove = remove + 1
                except IOError:
                    error = error + 1
            else:
                keep = keep + 1
    except UnboundLocalError:
        status1 = 'no sargassium files to trim'
        print(status1)
    removing = str(remove)+' files removed from sargassium directory'
    keeping = str(keep)+' files kept in sargassium directory'
    errors = str(error)+' errors in removing files from sargassium directory'
    return removing,keeping,errors
#Trim each of the log sub directories to a defined interval specified in YAML config
def trim_log_files(args, dirs):
    status = 0
    keep = 0
    error = 0
    current_time = time.time()
    for f in os.listdir(dirs['log_dir']):
        creation_time = os.path.getctime(dirs['log_dir']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['log_days']:
            try:
                os.remove(dirs['log_dir']+f)
                status = status + 1
            except IOError:
                error = error+1
        else:
            keep = keep + 1
    files_rem = str(status)+' log files removed from log directory'
    keeping = str(keep)+' log files kept in log directory'
    errors = str(error)+' errors in removing files from log directory'
    return files_rem,keeping,errors

#Trim each of the output sub directories to a defined interval as specified in YAML config
def trim_output_files(args, dirs):
    remove = 0
    keep = 0
    error = 0
    current_time = time.time()
    for f in os.listdir(dirs['out_dir']+args['out_1']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_1']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            try:
                os.remove(dirs['out_dir']+args['out_1']+f)
                remove = remove + 1
            except IOError:
                error = error + 1
        else: 
            keep = keep + 1
    for f in os.listdir(dirs['out_dir']+args['out_2']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_2']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            try:
                os.remove(dirs['out_dir'] + args['out_2'] + f)
                remove = remove + 1
            except IOError:
                error = error + 1
        else:
            keep = keep + 1
    for f in os.listdir(dirs['out_dir']+args['out_3']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_3']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            try:
                os.remove(dirs['out_dir'] + args['out_3'] + f)
                remove = remove + 1
            except IOError:
                error = error + 1
        else:
            keep = keep + 1
    removing = str(remove)+' files removed from output directories'
    keeping = str(keep)+' files kept in output directories'
    errors = str(error)+' errors in removing files from output directories'
    return removing,keeping,errors

def trim_restart_files(args, dirs):
    status = 'restart file trim unsuccessful'
    num = 0
    try:
        with open(dirs['run_dir']+'namelist_cfg') as f:
            restart_num = f.readlines()
        restart_num = restart_num[8]
        restart_num = restart_num.split(' ')
        restart_num = [x for x in restart_num if x]
        restart_num = int(restart_num[2])
        restart_files = os.listdir(dirs['restart_dir'])
        for each_file in restart_files:
            #restart0 = each_file.split('/')
            #restart0 = restart0[-1]
            restart0 = each_file.split('_')
            try:
                restart0 = restart0[1]
                restart0 = int(restart0.lstrip('0'))
                if restart0 < restart_num-1:
                    os.remove(dirs['restart_dir']+each_file)
                    num = num + 1
            except IndexError:
                print('no restart files to trim')
    except FileNotFoundError:
        print('namelist_cfg not found')
    status = 'number of restart files trimmed: '+str(num)

    return status

if __name__ == '__main__':
    main()  # pragma: no cover
