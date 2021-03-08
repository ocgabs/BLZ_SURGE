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
from nemo_cmd.namelist import namelist2dict
from nemo_nowcast import NowcastWorker, WorkerError

NAME = 'watch_nemo'
logger = logging.getLogger(NAME)
#redirect stdout and stderr to log files
sys.stdout = open('/SRC/logging/worker_logs/watch_nemo.txt', 'w')
sys.stderr = open('/SRC/logging/worker_logs/watch_nemo_errors.txt', 'w')

#Interval of how often to check the NEMO model is still running...
POLL_INTERVAL = 1 * 60  # seconds


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_nemo --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.run(watch_nemo, success, failure)


def success(parsed_args):
    logger.info('NEMO run completed')
    msg_type = 'success'
    return msg_type


def failure(parsed_args):
    logger.critical('NEMO run failed')
    msg_type = 'failure'
    return msg_type

#function to watch nemo model it reads the time step file every min, once the time step reaches
#its expected final value it checks the run output to see if the model run was successful.
def watch_nemo(parsed_args, config, tell_manager):
    ymd = arrow.now().format('YYYY-MM-DD') #get the current date in the specified format
    dirs = dir_gen(config) #generate directory locations based on YAML config file
    logger.debug(dirs)
    args = args_gen(config) #generate command arguments based on YAML config file
    logger.debug(args)
    sim_length = length_simulation(dirs) #calculate length of simulation in time steps
    logger.debug(sim_length)
    time_step = start_t_step(dirs)
    logger.debug(time_step)
    time.sleep(POLL_INTERVAL)
    while time_step < sim_length: 
        #define, open and extract time step
        time_step_file = dirs['results_dir']+'/time.step' 
        with open(time_step_file) as f:
            time_step = f.readlines()
        time_step = [x.strip() for x in time_step]
        time_step = int(time_step[0])
        logger.debug(time_step)
        #calcaulte percentage of completed model run
        percent_done = 1-((sim_length - time_step) / (sim_length))
        percent_done = int(percent_done*100)
        msg = (
                f'timestep: {time_step} '
                f'{percent_done}% percent complete'
            )
        logger.info(msg)
        time.sleep(POLL_INTERVAL)
    #check to if model run was successful
    run_succeeded = _confirm_run_success(dirs, sim_length)
    if not run_succeeded:
        raise WorkerError
    checklist = {
        'nowcast': {
            'run date': ymd,
            'completed': run_succeeded,
        }
    }
    return checklist
#generate directory locations based on YAML config file
def dir_gen(config): 
    dirs = {
            'results_dir' : config['watch']['NEMO']['results_dir'],
            }
    return dirs
#generate command arguments based on YAML config file
def args_gen(config):
    args = {
        'duration' : config['watch']['NEMO']['duration'],
        'config_name' : config['watch']['NEMO']['config_name'],
        'time_step' : config['watch']['NEMO']['time_step']
        }
    return args
#calculate length of simulation in time steps
def length_simulation(dirs):
    with open(dirs['results_dir']+'namelist_cfg') as f:
        len_sim = f.readlines()
    len_sim = len_sim[9]
    len_sim = len_sim.split(' ')
    len_sim = int(len_sim[7])
    return len_sim

def start_t_step(dirs):
    with open(dirs['results_dir']+'namelist_cfg') as f:
        tstep = f.readlines()
    tstep = tstep[8]
    tstep = tstep.split(' ')
    tstep = int(tstep[7])
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
def _confirm_run_success(dirs, sim_length):
    run_succeeded = True
    results_dir = dirs['results_dir']
    if not os.path.isdir(results_dir):
        run_succeeded = False
        logger.critical(f'No results directory: {results_dir}')
        # Continue the rest of the checks in the temporary run directory
    if os.path.isfile(results_dir+'output.abort.nc'):
        run_succeeded = False
        logger.critical(f'Run aborted: {results_dir/"output.abort.nc"}')
    try:
        time_step_file = dirs['results_dir']+'time.step'
        with open(time_step_file) as f:
            time_step = f.readlines()
        time_step = [x.strip() for x in time_step]
        time_step = int(time_step[0]) 
        if time_step != sim_length:
            run_succeeded = False
            logger.critical(
                f'Run failed: final time step is {time_step} not {sim_length-1}'
            )
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(f'Run failed; no time.step file')
        pass
    try:
        ocean_output_file = dirs['results_dir']+'ocean.output'
        with open(ocean_output_file) as f:
            for line in f:
                if 'E R R O R' in line:
                    run_succeeded = False
                    logger.critical(
                        f'Run failed; 1 or more E R R O R in: {results_dir}ocean.output'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(f'Run failed; no ocean.output file')
        pass
    try:
        solver_stat = dirs['results_dir']+'solver.stat'
        with open(solver_stat) as f:
            for line in f:
                if 'NaN' in line:
                    run_succeeded = False
                    logger.critical(
                        f'Run failed; NaN in: {results_dir}solver.stat'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(f'Run failed; no solver.stat file')
        pass
 #   if not (results_dir / 'restart').exists():
 #       run_succeeded = False
 #       logger.critical('Run failed; no restart/ directory')
    return run_succeeded


if __name__ == '__main__':
    main()  #pragma: no cover
