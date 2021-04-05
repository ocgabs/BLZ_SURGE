#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 17:52:52 2020

@author: thopri
"""

import os
from argparse import ArgumentParser
import yaml
import sys
import datetime
import ftplib
from glob import glob

def main(config_loc=''):

    if config_loc == '':
        parser = ArgumentParser(description='Copy FTP files worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()

        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc,'FTP_UPLOAD')
    if args.force == False:
        code1,timestamp1 = exit_code(config,'plot_tracks','0')
        if code1 != '0':
            print('unable to find a successful run of previous worker, terminating now')
            sys.exit(1)
        code2,timestamp2 = exit_code(config,'ftp_upload','0')
        if code2 == -1:
            print('no log for previous run found, assume first start')
            args.force = True
    if args.force == False:
        timestamp_chk = timestamp_check(timestamp1,timestamp2)
        if timestamp_chk == True:
            print('no successful run of worker since successful run of previous worker, running now....')
            args.force = True

    if args.force == True:
        cred = read_yaml(config['cred_file'],'FTP_CRED')
        list_of_files = glob(config['folder_loc']+'.png')# files to send
        print('files found in output folder......')
        print(list_of_files)

        print('starting FTP session...')
        try:
            session = ftplib.FTP(cred['server_address']+cred['server_path'], cred['server_username'], cred['server_password'])
        except:
            print(session)
            print('FTP session failed....')
            sys.exit()

        for file in list_of_files:
            filename = file.split('/')
            filename = filename[-1]
            if filename not in session.nlst():
                with open(file,'rb') as f:
                    print('file ' + filename +' doesnt exist on ftp server, uploading now....')
                    try:
                        session.storbinary('STOR '+filename, f) # send the file
                        print('upload successful')
                    except:
                        print('upload of '+filename+' unsuccessful')
            else:
                print('file '+filename+' already exists on server')
        print('uploads complete, closing session now')
        session.quit()
        print('worker ran successfully exiting')
        sys.exit(0)
    else:
        sys.exit(2)

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc,section):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file[section]
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

if __name__ == '__main__':
    main()  # pragma: no cover
