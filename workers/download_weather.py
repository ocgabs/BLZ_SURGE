#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 13:41:34 2018

@author: thopri
"""

# Copyright 2021 Thopri National Oceanography Centre

"""NEMO nowcast weather model products download worker.

Downloads GRIB filter files from NOAA GFS model as specified in the YAML Nowcast file, 
Worker script gets latestest model run or if not present (still processing/running etc) will 
download the previous model run.

"""
from time import sleep
import datetime
import arrow
import requests
from argparse import ArgumentParser
import yaml
import os
import json
import sys

def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='Download Weather Worker')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)
    #Load inital variables
    ymd = arrow.now().format('YYYY-MM-DD') #generate Todays date in specified format
    day_now = UtcNow() # creates the current time and date in the form of a dictionary
    model_run = Model_run() #Identify which model run to use, i.e. latest one
    arg = arg_gen(config, day_now, model_run) #generate arguments to use in functions these are loaded from YAML file
    t = ForeCast(arg) #Generate forecast file numbers (hourly in specific format)
    E = 0 #Initial error code number
    ## Check that the forecast files exist
    for i in range(int(arg["forecast_hrs"])): #For each of the forecast hours requested
        GRIB = HTTP_HEAD(config, arg, model_run, t, i) #Do a http head request to check date file exists
        if GRIB != 200: #If returned code is anyhting other than 200 (200 shows file is present)
            print('HTTP head req return code not 200 but '+str(GRIB))
            print('trying previous day forecast')
            E = 1 #Change error code to 1
            break
        print(str(i+1)+' of '+str(int(arg["forecast_hrs"]))+' forecast files present')
    #If E = 0 then all files are present and then a http request for the data can be made
    if E == 0:
        print('all files present, downloading them now....')
        for i in range(int(arg["forecast_hrs"])):
            DL = HTTP_req(config, arg, model_run, t, i) #Request and download all data
            print(str(i + 1) + ' of ' + str(int(arg["forecast_hrs"])) + ' forecast files downloaded')
            if type(DL) == int:
                print('Error in HTTP req: Error Code '+str(DL))
                E = 3 #Set error code to 3
                break
        #Create checklist to be written to checklist YAML file
        checklist = {f'{ymd} forecast': "Current Model Run Downloaded"}

    #If E is 1 then the IF statement catching HTTP error codes has activated
    if E == 1:
        day_now = UtcMinus24() #Get new day dictionary for 6 hours previous
        model_run = ModelMinus24() #Get new model run parameters i.e. previous one
        arg = arg_gen(config, day_now, model_run) #Regenerate arguments (Not sure if needed)
        for i in range(int(arg["forecast_hrs"])):
            GRIB = HTTP_HEAD(config, arg, model_run, t, i) #Http Head request for previous model run
            if GRIB != 200: #If the return code is not 200 (showing file is present) then
                print('HTTP head req return code not 200 but ' + str(GRIB))
                print('raising error code 3')
                E = 3  # Change error code to 3
                break
            print(str(i + 1) + ' of ' + str(int(arg["forecast_hrs"])) + ' forecast files present')
    #If E is still 1 then previous model data is present
    if E == 1:
        for i in range(int(arg["forecast_hrs"])):
            DL = HTTP_req(config, arg, model_run, t, i)  #Request and download data
            print(str(i + 1) + ' of ' + str(int(arg["forecast_hrs"])) + ' forecast files downloaded')
            if type(DL) == int:
                print('Error in HTTP req: Error Code '+str(DL))
                E = 3 #Set error code to 3
                break
    if E == 3: #If E = 3 then both the current and previous model runs are not present (or URL template is incorrect)
        print('Error code 3')
        sys.exit(3)
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

#Function to make HTTP HEAD requests to GFS server to check GRIB data files are present (often the latest run is only partially present)
def HTTP_HEAD(config, arg, model_run, t, i):
    url_template = config['weather']['download']['url_template']
    hours = str(t[i])
    URL = url_template.format(**arg)
    URL = URL.format(hours = hours)
    #print(URL)
    try:
        r = requests.head(URL)
    except requests.exceptions.ConnectionError:
        print('connection error retrying after 10 seconds')
        sleep(10)
        r = requests.head(URL)
    sleep(1)
    return r.status_code
#Function to make HTTP requests to download the relevent section of the GFS model
def HTTP_req(config, arg, model_run, t, i,redirect=False):
    url_template = config['weather']['download']['url_template']
    hours = str(t[i])
    URL = url_template.format(**arg)
    URL = URL.format(hours = hours)
    #print(URL
    try:
        response = requests.get(URL)
    except requests.exceptions.ConnectionError:
        print('connection error retrying after 10 seconds')
        sleep(10)
        response = requests.get(URL)
    if response.status_code != 200:
        return response.status_code
    #print(response.status_code)
    file_name = arg["dest_dir"]+arg["file_name"]+str(t[i])
    with open(file_name, 'wb') as f:
        f.write(response.content)
    sleep(1)
    return response

#function to create a list of forcast hours in the correct format in insert into the request URL
def ForeCast(arg):
    f = []
    for i in range(int(arg["forecast_hrs"])):
        f.insert(i, '{0:03}'.format(i))
    return f
#Function to pull all the command arguments from the YAML config file
def arg_gen(config, day_now, model_run):
    arguments = {
        'forecast_hrs' : config['weather']['download']['forecast_hrs'],
        'leftlon' : config['weather']['download']['leftlon'],
        'rightlon': config['weather']['download']['rightlon'],
        'toplat' : config['weather']['download']['toplat'],
        'bottomlat' : config['weather']['download']['bottomlat'],
        'var1' : config['weather']['download']['var1'],
        'var2' : config['weather']['download']['var2'],
        'var3' : config['weather']['download']['var3'],
        'lev1' : config['weather']['download']['lev1'],
        'lev2' : config['weather']['download']['lev2'],
        'file_template' : config['weather']['download']['file_template'],
        'run_time': 'Fgfs.'+day_now["year"]+day_now["month"]+day_now["day"]+'%2F'+model_run,
        'model_run' : model_run,
        'model_run' : model_run,
        'file_name' : 'gfs.t'+model_run+'z.pgrb2.0p25.f',
        'hours' : '{hours}',
        'dest_dir' : config['weather']['download']['dest_dir']
        }
    return arguments
#Function to calculate the current year, month, day and hour in UTC time
def UtcNow():
    now = datetime.datetime.utcnow()
    now = now.timetuple()
    year = '{0:04}'.format(now[0])
    month = '{0:02}'.format(now[1])
    day = '{0:02}'.format(now[2])
    hour = '{0:02}'.format(now[3])
    return {'year': year, 'month': month, 'day': day, 'hour': hour }
#Function to calcuate year, month, day 6 hours previous to current values.
def UtcMinus24():
    now = datetime.datetime.utcnow()
    minus = now - datetime.timedelta(hours=24)
    minus = minus.timetuple()
    year = '{0:04}'.format(minus[0])
    month = '{0:02}'.format(minus[1])
    day = '{0:02}'.format(minus[2])
    hour = '{0:02}'.format(minus[3])
    return {'year': year, 'month': month, 'day': day, 'hour': hour }

#function to calculate which model one to download, there are runs every 6 hours
# at midnight, 6 am, noon and 6 pm. Currently only a daily midnight run is downloaded, 
# as the model is currently unable to run with restart lengths of less than a day.
def Model_run():
    hour = '00'	
    now = datetime.datetime.utcnow()
    now = now.timetuple()
    #print(now[3])
    if 0 < now[3] <=6:
        hour = '00'
    if 6 < now[3] <= 12:
        hour = '00'
        #hour = '06'
    if 12 < now[3] <= 18:
        hour = '00'
        #hour = '12'
    if 18 < now[3] <= 24:
        hour = '00'
        #hour = '18'
    return hour
#Funciton to calcule the model hour 6 hours previous to current HourNow
def ModelMinus24():
    hour = '00'
    now = datetime.datetime.utcnow()
    minus = now - datetime.timedelta(hours=24)
    minus = minus.timetuple()
    if 0 < minus[3] <=6:
        hour = '00'
    if 6 < minus[3] <= 12:
        hour = '00'
        #hour = '06'
    if 12 < minus[3] <= 18:
        hour = '00'
        #hour = '12'
    if 18 < minus[3] <= 24:
        hour = '00'
        #hour = '18'
    return hour

if __name__ == '__main__':
    main()
