#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tues Aug 28 13:41:34 2018

@author: thopri
"""

# Copyright 2021 Thopri National Oceanography Centre

"""
NEMO nowcast stop container worker

Worker looks for and if running stops the container name listed in the config file


"""
from argparse import ArgumentParser
from subprocess import Popen, PIPE
import yaml
import os
from time import sleep
import json

def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='stop container running that matches name in config file')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)

    with open(config['status_dir'] + 'worker_status.json', 'r') as fp:
        status = json.load(fp)
    if status['STOP_CONTAINER'] == False:
        print('NEMO not finished or not running, going back to sleep for '+ str(config['POLL_INTERVAL']/60000) + ' minutes')
    if status['STOP_CONTAINER'] == True:

        print('NEMO finished, going to check the container stopped.....')

        container = Popen(['docker', 'ps'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = container.communicate()
        stdout = stdout.decode('utf-8')
        container = stdout.split('\n')
        container = container[1].split(' ')
        container = [x for x in container if x]
        container_ID = container[0]
        if len(container_ID) == 0:
            print('no containers running, all is well')
            return 0
        container_name = container[1]

        if container_name == config['container_name']:
            print('container still running, going to stop it now check stdout and stderr below.')
            stop_container = Popen(['docker', 'stop', container_ID], stdout=PIPE, stderr=PIPE)
            stdout, stderr = stop_container.communicate()
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
            print(stderr)
            print(stdout)
            return 1

        if container_name != config['container_name']:
            print(container_name)
            print('valid container not found, check container name above with config file...')
            return 2
        status['STOP_CONTAINER'] = False
        status['CLEAN_UP'] = True
        with open(config['status_dir'] + 'worker_status.json', 'w') as fp:
            json.dump(status, fp)
        print('Stop container Worker Complete, going to sleep for ' + str(config['POLL_INTERVAL']/60000) + ' minutes')

    return 0

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['STOP_CONTAINER']
    return config



if __name__ == '__main__':
    main()
