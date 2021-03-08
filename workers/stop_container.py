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


NAME = 'stop_container'
logger = logging.getLogger(NAME)
#redirect stdout and stderr to log files to allow debug and monitoring of worker
sys.stdout = open('/SRC/logging/worker_logs/stop_container.txt', 'w')
sys.stderr = open('/SRC/logging/worker_logs/stop_container_errors.txt', 'w')


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.download_weather --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    #worker.cli.add_date_option(
    #    '--forecast-date', default=arrow.now().floor('day'), help='Date for which to download the weather forecast.')
    worker.run(stop_container, success, failure)

def success(parsed_args):
    logger.info('stop container worker successful')
    msg_type = 'success'
    return msg_type

def failure(parsed_args):
    logger.critical('stop container worker failed, please stop container manually')
    msg_type = 'failure'
    return msg_type

def stop_container(parsed_args, config, *args):
    status = 'unable to stop container'
    dirs = dir_gen(config) #generate directory locations as per YAML config file
    logger.debug(dirs)
    logger.critical('Nowcast Worker crashed or failed please check logs.........')
    logger.critical('Stopping Container...........')
    f = open(dirs['status_dir']+'crashed.txt', 'w')
    f.close()
    status = 'container stopped successfully'
    return status

def dir_gen(config): 
    dirs = {
            'status_dir' : config['clean']['up']['status_dir'],
            }
    return dirs


if __name__ == '__main__':
    main()  # pragma: no cover
