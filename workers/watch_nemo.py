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
C-RISC NEMO nowcast weather model watch NEMO worker

Worker watches the NEMO model run and when complete checks to see if it comepleted successfully

"""
import logging
import os
from pathlib import Path
import shlex
import subprocess
import time
import sys
import arrow
from argparse import ArgumentParser
import yaml
from subprocess import Popen,PIPE
import json
from time import sleep

#function to watch nemo model it reads the time step file every min, once the time step reaches
#its expected final value it checks the run output to see if the model run was successful.
def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='Process GRIB files')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('eco_location', help='location of ecosystem file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()
        if args.force == True:
            print('force flag enabled, running worker now....')
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    POLL = eco_poll(args.eco_location,'watch_nemo')
    if args.force == False:
        print('seeing if surge container is running....')
        container = Popen(['docker', 'ps'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = container.communicate()
        stdout = stdout.decode('utf-8')
        container = stdout.split('\n')
        container = container[1].split(' ')
        container = [x for x in container if x]
        try:
            container = container[1]
            if container == config['container_name']:
                print('NEMO surge container running, going to watch it now......')
            args.force = True
        except IndexError:
            print('NEMO surge container not running, going to sleep for '+str(POLL/60000)+' minutes')

    if args.force == True:
        print('checking NEMO progress.....')
        ymd = arrow.now().format('YYYY-MM-DD') #get the current date in the specified format
        sim_length = length_simulation(config) #calculate length of simulation in time steps
        time_step = start_t_step(config)
        while time_step < sim_length:
            #define, open and extract time step
            time_step_file = config['results_dir']+'/time.step'
            with open(time_step_file) as f:
                time_step = f.readlines()
            time_step = [x.strip() for x in time_step]
            time_step = int(time_step[0])
            #calcaulte percentage of completed model run
            percent_done = 1-((sim_length - time_step) / (sim_length))
            percent_done = int(percent_done*100)
            msg = (
                    f'timestep: {time_step} of {sim_length}\n'
                    f'{percent_done}% percent complete'
                )
            print(msg)
            container = Popen(['docker', 'ps'], stdout=PIPE, stderr=PIPE)
            stdout, stderr = container.communicate()
            stdout = stdout.decode('utf-8')
            container = stdout.split('\n')
            container = container[1].split(' ')
            container =  [x for x in container if x]
            try:
                container_ID = container[0]
            except IndexError:
                print('no containers running, program terminating')
                print('checking to see if model was successful....')
                # check to if model run was successful
                run_succeeded = _confirm_run_success(config, sim_length)
                if not run_succeeded:
                    print('Run Failed')
                return 1
            print('Container ID: '+str(container_ID))
            container_name = container[1]
            if container_name != config['container_name']:
                print('container no longer running stopping watch process....')
                print('checking to see if model was successful....')
                # check to if model run was successful
                run_succeeded = _confirm_run_success(config, sim_length)
                if not run_succeeded:
                    print('Run Failed')
                return 2

            time.sleep(config['WATCH_INTERVAL']*60)
        #check to if model run was successful
        run_succeeded = _confirm_run_success(config, sim_length)
        if not run_succeeded:
            print('Run Failed')
        checklist = {
            'nowcast': {
                'run date': ymd,
                'completed': run_succeeded,
            }
        }
        print('NEMO watching finished, checking container has stopped....')
        print('giving container time to stop on its own, sleeping for 5 mins...')
        time.sleep(300)
        print('waking up.... going to check the container stopped.....')

        container = Popen(['docker', 'ps'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = container.communicate()
        stdout = stdout.decode('utf-8')
        container = stdout.split('\n')
        container = container[1].split(' ')
        container = [x for x in container if x]
        try:
            container_ID = container[0]
            container_name = container[1]

            if container_name == config['container_name']:
                print('container still running, going to stop it now check stdout and stderr below.')
                stop_container = Popen(['docker', 'stop', container_ID], stdout=PIPE, stderr=PIPE)
                stdout, stderr = stop_container.communicate()
                stdout = stdout.decode('utf-8')
                stderr = stderr.decode('utf-8')
                print(stderr)
                print(stdout)
                print('Watch Worker Complete, going to sleep for ' + str(POLL/ 60000) + ' minutes')
                return 1

            if container_name != config['container_name']:
                print(container_name)
                print('valid container not found, maybe different container is running? check container name above with config file...')
                print('Watch Worker Complete, going to sleep for ' + str(POLL/ 60000) + ' minutes')
                return 2

        except IndexError:
            print('no containers running, all is well')

        print('Watch Worker Complete, going to sleep for ' + str(POLL/60000) + ' minutes')
    return 0

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['WATCH_NEMO']
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

#calculate length of simulation in time steps
def length_simulation(config):
    with open(config['results_dir']+'namelist_cfg') as f:
        len_sim = f.readlines()
    len_sim = len_sim[9]
    len_sim = len_sim.split(' ')
    len_sim = int(len_sim[7])
    return len_sim

def start_t_step(config):
    with open(config['results_dir']+'namelist_cfg') as f:
        tstep = f.readlines()
    tstep = tstep[8]
    tstep = tstep.split(' ')
    tstep = int(tstep[8])
    return tstep
    
#check to see if run was successful, tests include:
#does the results directory exist?
#does output.abort.nc exist?
#has the expetect number of time steps been carried out?
#does the time.step file exist?
#does the ocean.output file exist?
#are there E R R O R logs in the ocean.output file?
#Does the solver.stat file exist?
#Are the NaN values in the solver.stat file?
#if all these pass then the model is considered to have successfully run
def _confirm_run_success(config, sim_length):
    run_succeeded = True
    results_dir = config['results_dir']
    if not os.path.isdir(results_dir):
        run_succeeded = False
        print(f'No results directory: {results_dir}')
        # Continue the rest of the checks in the temporary run directory
    if os.path.isfile(results_dir+'output.abort.nc'):
        run_succeeded = False
        print(f'Run aborted: {results_dir/"output.abort.nc"}')
    try:
        time_step_file = config['results_dir']+'time.step'
        with open(time_step_file) as f:
            time_step = f.readlines()
        time_step = [x.strip() for x in time_step]
        time_step = int(time_step[0]) 
        if time_step != sim_length:
            run_succeeded = False
            print(
                f'Run failed: final time step is {time_step} not {sim_length-1}'
            )
    except FileNotFoundError:
        run_succeeded = False
        print(f'Run failed; no time.step file')
        pass
    try:
        ocean_output_file = config['results_dir']+'ocean.output'
        with open(ocean_output_file) as f:
            for line in f:
                if 'E R R O R' in line:
                    run_succeeded = False
                    print(
                        f'Run failed; 1 or more E R R O R in: {results_dir}ocean.output'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        print(f'Run failed; no ocean.output file')
        pass
    try:
        solver_stat = config['results_dir']+'solver.stat'
        with open(solver_stat) as f:
            for line in f:
                if 'NaN' in line:
                    run_succeeded = False
                    print(
                        f'Run failed; NaN in: {results_dir}solver.stat'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        print(f'Run failed; no solver.stat file')
        pass
 #   if not (results_dir / 'restart').exists():
 #       run_succeeded = False
 #       logger.critical('Run failed; no restart/ directory')
    return run_succeeded


if __name__ == '__main__':
    main()  #pragma: no cover
