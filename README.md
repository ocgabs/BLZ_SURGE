# BLZ_SURGE Operational Particle Tracking Model
Operational Belize surge model with an open parcels post processing component.

The readme describes how to use the BLZ-SURGE NEMO configuration and associated
particle tracking modules within an operational framework. 

Prerequisites
=============

To use this framework the following prerequisites are required:

- containerisation framework: docker or podman
- python package manager: conda or pip
- node package manager: NPM

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

PM2 Process Manager
-------------------
PM2 is a production grade process manager that is primarily used to monitor JS apps. However, it
is also good for monitoring python processes. The system is able to restart failed and finished 
processes at a defined interval and also provides logging and monitoring tools. The monitoring 
process is defined in a yaml ecosystem file located in the config directory.

Python workers
--------------
The actual work of running the model, collating data and running the particle tracking is undertaken
by python scripts known as workers. These have the following allotted tasks:

- download weather: (atmospheric forcing)
- process forcing: (process forcing data to NEMO format)
- generate boundary: (generate weighting files, only needed once)
- run nemo: (set up and start NEMO surge container)
- watch nemo: (monitor the running container and QA output when complete)
- get sargassium: (get sargassium forecast product and create seed locations)
- run parcels: (run openparcels module using NEMO output and seed locations to produce particle tracks)
- clean up: (clean up NEMO directory, trim log files and remove old output files)

Workers have different behaviour depending on their type, e.g. download weather runs daily updating its
data folder with new data. Whereas process forcing checks that download weather was successful and also 
checks that the data is newer than its poll/restart interval. 

The workers are configured using a yaml file located in the config directory.

To install operational framework:
=================================

clone the repo and switch to surge container branch:
```commandline
$ git clone https://github.com/ocgabs/BLZ_SURGE
$ git checkout surge-container
```
build and activate the python environment:
```commandline
$ conda env create -f environment.yaml
$ conda activate BLZ-SURGE
```
This will build the conda environment with all the dependencies required for the python
workers. 

Install the process manager PM2:
```commandline
$ npm install pm2:latest -g
```
The framework is now installed and ready to use. To start the framework the following command is required:

```commandline
$ pm2 config/ecosystem.yml
```
To monitor the system it recommended to run the following in separate terminals:

```commandline
$ pm2 monit
$ pm2 logs
$ pm2 status
```
This will start an interactive dashboard (monit) with realtime logs for each process, a logging screen (logs)
that shows all logs as they are generated, and finally the current status of all processes (status). 

For information please see accompanying user manual.