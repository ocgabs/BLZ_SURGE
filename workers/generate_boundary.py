#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: thopri
"""

# Copyright 2021 Thopri National Oceanography Centre

"""
Script takes the processed netcdf files and uses the NEMO tools to generate weighted netcdf files that
can be used by the NEMO model. 

"""

import glob
import logging
import shlex
from pathlib import Path
import os
import sys
import arrow
import subprocess
from argparse import ArgumentParser
import yaml

def main():
    parser = ArgumentParser(description='Process GRIB files')
    parser.add_argument('config_location', help='location of YAML config file')
    args = parser.parse_args()
    config = read_yaml(args.config_location)
    #get current date in specified format
    start_ymd = arrow.now().format('YYYY-MM-DD')

    dirs = dir_gen(config) #generate directory locations using YAML config file

    files = readfilename(dirs) #read the files that are in the input directory one for each variable

    num_var = len(files) #number of variables

    args = args_gen(config) #generate the command arguments from the YAML config file

    #for each variable
    for f in range(num_var):
        #get the file name of variable netcdffile
        filename = files['file'+str(f+1)]

        #from filename extract parameters required, config, variable, year, month, day
        parameters = process_filename(filename)

        #create output name from the input filename
        outputfilename = gen_outputname(parameters, dirs)

        #populate namelist file using namelist template and YAML config file
        namelist = pop_namelist(args, parameters, dirs, files, outputfilename, f)
        #remove previous model run weight files
        delete = delete_old_weight(outputfilename)

        #generate the weighted netcdf files, one for each variable
        generate = generate_weight(args, dirs, files, outputfilename)
        #Check files are generated
        check = QA_weights_file(outputfilename)

    checklist = {f'{start_ymd} boundary conditions files generated'}
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


#Function to generate directory locations from YAML file
def dir_gen(config): 
    dirs = {
            'netcdf_dest_dir' : config['generate']['boundary']['netcdf_dest_dir'],
            'namelist_dir' : config['generate']['boundary']['namelist_dir'],
            'weights_dir' : config['generate']['boundary']['weights_dir']
            }
    return dirs
#Function to generate command arguments from YAML file
def args_gen(config):
    args = {
        'template_1' : config['generate']['boundary']['template_1'],
        'template_2' : config['generate']['boundary']['template_2'],
        'file_out_1' : config['generate']['boundary']['file_out_1'],
        'file_out_2' : config['generate']['boundary']['file_out_2'],
        'input_1' : config['generate']['boundary']['input_key_1'],
        'input_2' : config['generate']['boundary']['input_key_2'],
        }
    return args
#Function to read filename and parse into a dictionary with an entry for each variable present
def readfilename(dirs):
    list_of_files = glob.iglob(dirs["netcdf_dest_dir"]+'*.nc')
    sorted_files = sorted(list_of_files, key=os.path.getctime)
    #latest_file = max(list_of_files, key=os.path.getctime)
    file1 = sorted_files[-1]
    file2 = sorted_files[-2]
    file3 = sorted_files[-3]
    return {'file1' : file1, 'file2' : file2, 'file3' : file3 }
#Function to process the read filenames, generates a dictionary listing parameters for each file
def process_filename(filename):
    config,var,date = str.split(filename, '_')
    date = date[:-3]
    year = date[1:5]
    month = date[6:8]
    day = date[9:11]
    config = str.split(config,'/')
    config = config[-1]
    
    return {'config' : config, 'var': var, 'year': year, 'month': month, 'day': day }
#function to create output weighted file name
def gen_outputname(parameters, dirs):
    output_2 = dirs['weights_dir']+parameters['config']+'_'+parameters['var']+"_weights-bicubic.nc"
    return output_2
#Populate namelist function, the namelist files that are required as input to the weighting executables
#are created here by populating a template file.
def pop_namelist(args, parameters, dirs, files, outputfilename, f):
    start_ymd = arrow.now().format('YYYY-MM-DD')
    # Read in the file
    with open(dirs["namelist_dir"]+args['template_1'], 'r') as file :
      filedata = file.read()
    # Replace the target string
    filedata = filedata.replace(args['input_1'], files['file'+str(f+1)])
    # Write the file out again
    with open(dirs["namelist_dir"]+args['file_out_1'], 'w') as file:
      file.write(filedata)
    # Read in the file
    with open(dirs["namelist_dir"]+args['template_2'], 'r') as file :
      filedata = file.read()
    # Replace the target string
    filedata = filedata.replace(args['input_1'], files['file'+str(f+1)])
    filedata = filedata.replace(args['input_2'],outputfilename)
    # Write the file out again
    with open(dirs["namelist_dir"]+args['file_out_2'], 'w') as file:
      file.write(filedata)

    checklist = {f'{start_ymd} namelist '+files['file'+str(f+1)]+' file populated'}
    return checklist
#remove old weight files from previous model runs.
def delete_old_weight(outputfilename):
    try:
        os.remove(outputfilename)
        err = 'old weighting files deleted'
    except IOError:
        err = 'no weighting files in folder'
    return err
#Function to generate weight files, uses the NEMO model weighting tools
def generate_weight(args, dirs, files, outputfilename):
    # move to the namelist directoy then execute the relevent nemo tool providing the relevent namelist file
    os.system('cd '+dirs['namelist_dir']+' && echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripgrid.exe')
    os.system('cd '+dirs['namelist_dir']+' && echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scrip.exe')
    os.system('cd '+dirs['namelist_dir']+' && echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripshape.exe')
    os.system('cd '+dirs['namelist_dir']+' && echo "namelist_reshape_bicubic_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scrip.exe')
    os.system('cd '+dirs['namelist_dir']+' && echo "namelist_reshape_bicubic_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripshape.exe')
    #remove intermediate files no longer required
    os.system('cd '+dirs['namelist_dir']+' && rm remap_nemo_grid_atmos.nc')
    os.system('cd '+dirs['namelist_dir']+' && rm remap_data_grid_atmos.nc')
    os.system('cd '+dirs['namelist_dir']+' && rm data_nemo_bilin_atmos.nc')
    os.system('cd '+dirs['namelist_dir']+' && rm weights_bilinear_atmos.nc')
    os.system('cd '+dirs['namelist_dir']+' && rm data_nemo_bicubic_atmos.nc')
#QA weight netcdf folder function to see if the weighting files have been created.
def QA_weights_file(outputfilename):
    try:
        os.path.exists(outputfilename)
        err = 0
        status = 'QA Check: weights file does exist!'
    except:
        err = 1
    
    if err == 1:
        status = 'QA Check: weights file does not exist'


    return status 

if __name__ == '__main__':
    main()

