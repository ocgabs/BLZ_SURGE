# BLZ_SURGE Operational Particle Tracking Model
Operational Belize surge model with an open parcels post processing component.

The readme describes how to use the BLZ-SURGE NEMO configuration and associated
particle tracking modules within an operational framework. 

Prerequisites
=============

Sargassum Forecasting has the following requirements:

-containerisation framework: docker
-python package manager: miniconda or anaconda
-nodejs package manager: npm 
-cron service running

This system is only compatible with Linux, so far it has been tested on Fedora and Ubuntu.

System Setup
=============
The framework consists of three parts:

- Containerised NEMO surge model config
- Python workers to undertake different jobs (download weather etc)
- Javascript process manager to run and monitor the python workers

NEMO surge model
-----------------
The Belize model config has been built into a docker container, there are several dockerfile
versions in the repository, but a suitable container has been built and is available on dockerhub.
Please see supplementary info to build NEMO containers.

Python workers
--------------
The actual work of running the model, collating data and running the particle tracking is undertaken
by python scripts known as workers. These have the following allotted tasks:

- download weather: (atmospheric forcing)
- process forcing: (process forcing data to NEMO format)
- generate boundary: (generate weighting files, only needed once)
- run nemo: (set up and start NEMO surge container)
- watch nemo: (monitor the running container and QA output when complete)
- get sargassium: (get sargassium forecast product)
- find seed: (find seed locations within sargassium product)
- run parcels: (run openparcels module using NEMO output and seed locations to produce particle tracks)
- clean up: (clean up NEMO directory, trim log files and remove old output files)

Workers have different behaviour depending on their type, e.g. download weather runs daily updating its
data folder with new data. Whereas process forcing checks that download weather was successful and also 
checks that the data is newer than its poll/restart interval. 

The workers are configured using a yaml file located in the config directory.

PM2 Process Manager
-------------------
PM2 is a production grade process manager that is primarily used to monitor JS apps. However, it
is also good for monitoring python processes. The system is able to restart failed and finished 
processes at a defined interval and also provides logging and monitoring tools. The monitoring 
process is defined in a yaml ecosystem file located in the config directory.


Installation
-------------

The framework has been designed and tested on Linux, both Fedora and Ubuntu have been used. Once the requirements are in place the framework can be installed as follows:

Clone the repository (best practise is from user home directory) and switch to correct branch

```shell
$ git clone https://github.com/ocgabs/BLZ_SURGE
$ git checkout surge-container
```
The repository needs to be renamed due to filename parsing requirements, until then please rename manually as follows:

```shell
$ mv BLZ_SURGE BLZ-SURGE
```
Navigate to the BLZ-SURGE main directory and build the python environment using conda (select yes if asked to confirm):
```shell
$ conda env create -f environment.yml
$ conda activate BLZ-SURGE
````
Install the process manager PM2:

```shell
$ sudo npm install pm2@latest -g
```
A useful monitoring program to install is ctop, while it only workers for docker containers, once installed it allows the monitoring of the container. If using podman this does not work but running “podman events” in the terminal” will provide a feed showing container events e.g. start stop etc. There is also the possibility of using cockpit to provide a website based interface but this is all outside the scope of this manual.

Before first use
-----------------

Once the python environment and process manager are installed the framework is ready to go, however the system requires some initial setup steps to reflect the new install location, these are:

- Populate INPUTS folder
- Amend configuration files
- Generate weighting files
- set processor options

Populating INPUTS folder
-------------------------

The NEMO model requires a number of input files for it to successfully run. It is not possible to put this in the github repository, so they need to be added after it is cloned. The current requirements for files are:

- bathy_meter.nc
- coordinates.nc
- coordinates.bdy.nc
- domain_cfg.nc
- tidal forcing files.

If any of these are missing then the model will likely fail. 

Amend configuration files
-------------------------

The configuration files in the config folder will need updating with the relevant paths as by default they are setup for the user “thopri” in the home directory. For simplicity, it is best to clone the repository into the users home directory and then the only change required is to update the user name in the defined paths in the configuration files. 

In the ecosystem yml file, every worker entry has an cwd variable, this should be updated to reflect the current user. In the nowcast yaml files most paths will need the user name updating. Easiest way is to search for the default user “thopri” and replace with user on installation system. NOTE: the container name is prefixed with the name thopri but this is required to locate the container image on the docker repository so must be kept.

Generating weighting files
--------------------------

NEMO needs weighting files so it can map the atmospheric forcing onto its grid. There is a worker that can generate these files. So the process to generate is as follows, run the download_weather and process_forcing workers manually to generate some input to generate the weightings. Then run the generate_weights worker within the NEMO surge container as the relevant tools to create are stored inside.
```shell
$ python workers/download_weather.py config/nowcast.yaml
$ python workers/process_forcing.py config/nowcast.yaml -f
```
```shell
$ docker run --rm -v /path/to/BLZ-SURGE:BLZ-SURGE thopri/nemo-surge-blz:8814 python /BLZ-SURGE/workers/generate_boundary.py /BLZ-SURGE/config/nowcast.yaml
```
This should run all the steps to generate the weighting files. If successful the weighting files will appear in the weights folder within the main directory.

Changing number of processors
------------------------------

By default the container runs with 3 CPU processors allocated to the model. This can be changed to suit the architecture the model is running on. E.g. the workstation used for initial testing runs has 10 Cores and with hyper-threading 20 logical processors. Setting the container to use 12 NEMO processors resulted in a 100% utilisation of the system. Some trial and error maybe required for other setups.

The file to set the cores is called run_surge.sh and is located in the RUN_NEMO directory. The line to change is as follows:

```shell
mpirun -n 3 ./nemo.exe : -n 1 ./xios_server.exe
```
where the first number value is the number of NEMO cores to use. Set this values to one appropriate for your system. E.g. for an 4 core/ 8 processor machine, the starting point would be 3/5 NEMO cores. Different variations may result in quicker run times. NOTE: some core counts are not stable, currently the configuration is not stable on 2, 4 or 6 cores. But will run on 1, 3, 5 or 7 cores. 

The second number relates to the number of input/output servers to use, for NEMO there needs to be one of these servers for every 10 to 50 NEMO cores, so for systems below 10 cores this number should be 1, only increasing to 2 at higher core counts such as 25 cores. Best values to use would take some trial and error.

Once these steps are complete the framework should be ready to start.

Usage
------

At this point the framework is installed and should have all the files needed and be configured correctly. It is important that all commands are run from the conda environment created previously so ensure that the environment is loaded as follows:
```shell
$ conda activate BLZ-SURGE
```
It can be started as follows (from the BLZ-SURGE directory):
```shell
$ pm2 start config/ecosystem.yml
```
To monitor the system PM2 has some terminal tools:
```shell
$ pm2 monit
$ pm2 logs
$ pm2 status
```
Running each of these commands in a separate terminal will give information on the system, monit is an interactive dashboard, logs shows the log files as they are written in real time and status returns the current status of PM2 (which processes are running etc).

The system can be stopped with the following (again from the BLZ-SURGE main directory):
```shell
$ pm2 stop config/ecosystem.yml
```
Finally the processes can be removed from PM2 by:
```shell
$ pm2 delete config/ecosystem.yml
```
Individual workers can be stopped, started and deleted in the same way:
```shell
$ pm2 start download_weather
$ pm2 stop download_weather
$ pm2 reload download_weather
$ pm2 delete download_weather
```
Logs for individual workers can be inspected as follows:
```shell
$ pm2 logs download_weather
```
This will show both standard output and also errors (stdout and stderr). It is useful for debugging a single process as the main log feed can get overwhelming with the constant writing from each worker to it.

To monitor the exit codes of the workers, the log of the PM2 process can be scrutinized using:
```shell
$ pm2 logs PM2 
```
To see further back as by default only 15 lines for each log are shown the --lines flag can be used. e.g.
```shell
$ pm2 logs PM2 --lines 50
```
For the last 50 lines of the PM2 logs. 

It is also sensible to install a log rotate module for PM2 that ensures log files don’t get excessively large. This can be installed as follows:
```shell
$ pm2 install pm2-logrotate
$ pm2 reloadLogs
```
Periodically the PM2 logs will need to be flushed, this process removes all the old logs reclaiming disk space. At the moment there is no automatic method to this. To flush the logs:
```shell
$ pm2 flush
```
Individual workers can also be run using python command (from the BLZ-SURGE main directory),
```shell
$ python workers/download_weather.py config/nowcast.yaml
```
Some worker will require an -f flag, this is a force flag that overrides the workers checking to see if it needs to be run by comparing exit codes of the previous worker and itself. The workers that need the -f flag are:

-process_forcing
-run_nemo
-watch_nemo
-find_seed
-run_parcels
-plot_output
-make_plots

All other workers don’t rely on a previous worker output so do not need to check to see if it has successfully completed. NOTE: using force flag when previous worker has not ran successfully will result in unexpected behaviour.

When needed docker will pull and run the container but it can be pulled beforehand with this command:
```shell
$ docker pull thopri/nemo-surge-blz:8814
```
Scheduling
-----------

While most of the workers just look for the success of the previous worker and start based on that. However two workers need to be started at a defined interva as they provide the new data required to undertaken a new run. These are the download weather and get sargassum workers, both of these workers will start automatically with the pm2 start ecosystem.yml command but once complete unlike the other workers they do not get restarted. This functionality is implemented using Cron and the setting up of a cronjob. This is a scheduling process within Linux. To add entries the user needs to create a crontab file.
```shell
$ crontab -e
```
This opens the crontab and the following entry can be added.
```
30 8 * * * /usr/local/bin/pm2 start download_weather > /home/thopri/BLZ-SURGE/logs/cron-weather.log
30 8 * * * /usr/local/bin/pm2 start get_sargassium > /home/thopri/BLZ-SURGE/logs/cron-sar.log
```
This starts the two workers at 8:30 am, saving the terminal output to a log file. If a different time is desired the user can amend the first two values. The first being the minutes and second is the hours, e.g. 30 8 is 8:30 am.

This is essential to starting the framework operationally as without it the system will only run the model once.

To get email notifications, adding the following to the top of the crontab should result in emails being sent showing the worker starting.
```
MAILTO=example@email.com
```
If a cronjob does not start then troubleshooting will need to take place, common issues are the cron itself is not running or the crontab commands having incorrect syntax.

Further Information
-------------------

For more information please see manual in repository.
