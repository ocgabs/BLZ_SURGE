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
C-RISC NEMO nowcast weather model clean up worker

Worker cleans the model runtime directory and trims log and output files 
to ensure filespace limits are not reached


"""
import logging
import logging.config
from pathlib import Path
import arrow
import os
import time
import sys

from nemo_nowcast import NowcastWorker
from nemo_nowcast.fileutils import FilePerms


NAME = 'clean_up'
logger = logging.getLogger(NAME)
#redirect stdout and stderr to log files to allow debug and monitoring of worker
sys.stdout = open('/SRC/logging/worker_logs/clean_up.txt', 'w')
sys.stderr = open('/SRC/logging/worker_logs/clean_up_errors.txt', 'w')


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nemo_nowcast.workers.rotate_logs --help`
    """
    worker = NowcastWorker(
        NAME, description=__doc__, package='nemo_nowcast.workers')
    worker.init_cli()
    worker.run(clean_up, success, failure)


def success(parsed_args):
    # logger_name is required because file system handlers get loaded in
    # rotate_logs()
    logger.info('workspace successfully cleared', extra={'logger_name': NAME})
    msg_type = 'success'
    return msg_type


def failure(parsed_args):
    # logger_name is required because file system handlers get loaded in
    # rotate_logs()
    logger.critical('failed to clear workspace', extra={'logger_name': NAME})
    msg_type = 'failure'
    return msg_type

#Main clean up function
def clean_up(parsed_args, config, *args):
    #get todays date in the specifed format
    ymd = arrow.now().format('YYYY-MM-DD-HH')
    # logger_name is required because file system handlers get loaded below
    logger.info('cleaning up workspace', extra={'logger_name': NAME})
    dirs = dir_gen(config) #generate directory locations as per YAML config file
    logger.debug(dirs)
    args = args_gen(config) #generate command line arguments as per YAML config file
    logger.debug(args)
    trim_re = trim_restart_files(args, dirs)
    logger.debug(trim_re)
    run = remove_run_files(args,dirs) #remove model runtime files
    logger.debug(run)
    out = remove_output_file(args,dirs) #remove model output files
    logger.debug(out)
    trim_log = trim_log_files(args,dirs) #trim log files to age as defined in YAML file
    logger.debug(trim_log)
    trim_out = trim_output_files(args,dirs) #trim output files to age as defined in YAML file
    logger.debug(trim_out)
    checklist = {f'{ymd} Clean up': "Workspace Cleared"}
    finish = write_completed_file(args, dirs) #write completed txt file that will stop container
    logger.debug(finish)
    return checklist
#Generate directory locations as defined in YAML config file
def dir_gen(config): 
    dirs = {
            'run_dir' : config['clean']['up']['run_dir'],
            'log_dir' : config['clean']['up']['log_dir'],
            'out_dir' : config['clean']['up']['out_dir'],
            'status_dir' : config['clean']['up']['status_dir'],
            'restart_dir' : config['clean']['up']['restart_dir'],
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
        'log_1' : config['clean']['up']['log_1'],
        'log_2' :config['clean']['up']['log_2'],
        'circus_log' : config['clean']['up']['circus_log'],
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
    try:
        os.remove(dirs['log_dir']+args['circus_log'])
        num = num+1
    except IOError:
        err = err + 1
    status = 'number of run files removed: '+str(num)
    return status
#Function to remove all model output files from model run directory
def remove_output_file(args, dirs):
    status = 'unable to remove model output file'
    run_files = os.listdir(dirs['run_dir'])
    for each_file in run_files:
        if each_file.startswith(args['config_name']):
            os.remove(dirs['run_dir']+each_file)
    status = 'model output cleared from run directory'
    return status
    
#Trim each of the log sub directories to a defined interval specified in YAML config
def trim_log_files(args, dirs):
    status = 'log file trim unsuccessful'
    current_time = time.time()
    for f in os.listdir(dirs['log_dir']+args['log_1']):
        creation_time = os.path.getctime(dirs['log_dir']+args['log_1']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            os.remove(dirs['log_dir']+args['log_1']+f)
        else:
            status1 = 'log 1 files trimmed successfully'
    for f in os.listdir(dirs['log_dir']+args['log_2']):
        creation_time = os.path.getctime(dirs['log_dir']+args['log_2']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            os.remove(dirs['log_dir']+args['log_2']+f)
        else:
            status2 = 'log 2 files trimmed successfully'
    status = status1+status2
    return status
#Trim each of the output sub directories to a defined interval as specified in YAML config
def trim_output_files(args, dirs):
    status = 'output files trim unsuccessful'
    current_time = time.time()
    for f in os.listdir(dirs['out_dir']+args['out_1']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_1']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            os.remove(dirs['out_dir']+args['out_1']+f)
        else: 
            status1 = 'out 1 trim successfull (csv) '
    for f in os.listdir(dirs['out_dir']+args['out_2']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_2']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            os.remove(dirs['out_dir']+args['out_2']+f)
        else:
            status2 = ' out 2 trim successfull (netcdf) '
    for f in os.listdir(dirs['out_dir']+args['out_3']):
        creation_time = os.path.getctime(dirs['out_dir']+args['out_3']+f)
        if (current_time - creation_time) // (24 * 3600) >= args['num_days']:
            try:
                os.remove(dirs['out_dir']+args['out_3']+f)
            except OSError:
                pass
        else:
            status3 = ' out 3 trim successfull (plots)'
    status = status1+status2+status3
    return status

def trim_restart_files(args, dirs):
    status = 'restart file trim unsuccessful'
    num = 0
    with open(dirs['run_dir']+'namelist_cfg') as f:
        restart_num = f.readlines()
    restart_num = restart_num[8]
    restart_num = restart_num.split(' ')
    restart_num = int(restart_num[7])
    restart_files = os.listdir(dirs['restart_dir'])
    for each_file in restart_files:
        #restart0 = each_file.split('/')
        #restart0 = restart0[-1]
        restart0 = each_file.split('_')
        restart0 = restart0[1]
        restart0 = int(restart0.lstrip('0'))
        if restart0 < restart_num-1:
            os.remove(dirs['restart_dir']+each_file)
            num = num + 1
    status = 'number of restart files trimmed: '+str(num)

    return status

#write completed txt file in status directory, this stops the container!!!!
def write_completed_file(args, dirs):
    status = 'completed text file not written'
    f = open(dirs['status_dir']+'completed.txt', 'w')
    f.close()
    status = 'completed txt file written'
    return status

if __name__ == '__main__':
    main()  # pragma: no cover
