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
from glob import glob
import paramiko

def main(config_loc=''):

    if config_loc == '':
        parser = ArgumentParser(description='Copy FTP files worker')
        parser.add_argument('config_location', help='location of YAML config file')
        parser.add_argument('-f', '--force', action='store_true', help='force start of worker')
        args = parser.parse_args()

        config = read_yaml(args.config_location,'FTP_UPLOAD')
        if config == 1:
            print('unable to read the nowcast yaml file')
    else:
        config = read_yaml(config_loc,'FTP_UPLOAD')
        if config == 1:
            print('unable to read the nowcast yaml file')
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
        if cred == 1:
            print('unable to read the FTP credentials yaml file')
        print('opening SFTP connection...')
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(cred['server_address'], username=cred['server_username'], password=cred['server_password'])
            sftp = ssh.open_sftp()
            print('opening of STFP connection successful')
        except:
            print('SFTP connection failed....')
            sys.exit('SFTP connection failure')

        list_of_folders = config['folders'].split(',')
        print('folders to upload from....')
        print(list_of_folders)

        for folder in list_of_folders:
            f_name = folder.split('-')
            f_name = f_name[0]
            f_type = folder.split('-')
            f_type = f_type[1]
            print('uploading from '+f_name)
            list_of_files = glob(config['folder_ouput_loc']+f_name+'/*.'+f_type)# files to send
            if len(list_of_files) == 0:
                print('no files to upload going to next folder...')
                continue
            print('files found in folder '+f_name+'......')
            print(list_of_files)
            file_chk = 0
            for file in list_of_files:
                filename = file.split('/')
                filename = filename[-1]
                f_name = folder.split('-')
                f_name = f_name[0]
                remotepath = cred['server_path']+f_name+'/'+filename
                try:
                    sftp.put(file, remotepath)
                except:
                    file_chk = file_chk +1
                    print('upload of '+filename+' unsuccessful')
                    print('trying next file in list')
            if file_chk == 0:
                print('all files for folder '+f_name+' uploaded')
            else:
                print(str(file_chk)+' files did not successfully upload')
        print('uploads from all folders complete, closing connection now')
        sftp.close()
        ssh.close()
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