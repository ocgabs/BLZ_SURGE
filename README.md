# BLZ_SURGE
Belize surge model


This recipe describes how to build NEMO and XIOS appropriate for a surge model
using Docker.

Note the is a slight modification to the MY_SRC/diaharm_fast.F90 (line 68)
relative to  surge configurations built on other machines (e.g. AMM7_SURGE on
  ARCHER[1,2] https://doi.org/10.5281/zenodo.4022309).
This is because of incompatability of compilers used across machines.
Cray (e.g. ARCHER2):
CHARACTER( LEN = 10 ), DIMENSION(5), PARAMETER :: m_varName2d = (/'ssh','u2d','v2d','ubfr','vbfr'/)
GNU (here):
CHARACTER( LEN = 10 ), DIMENSION(3), PARAMETER :: m_varName2d = (/'ssh','u2d','v2d'/)

This repository is based upon original work by Pierre Derian: 
<contact@pierrederian.net> (https://github.com/pderian/NEMOGCM-Docker), Nikyle Nguyen <NLKNguyen@MSN.com> 
(https://github.com/NLKNguyen/alpine-mpich), Simon Holgate: https://github.com/simonholgate/nemo-mpich <hello@simonholgate.org.uk> and thopri.


Prerequisites and path definitions
=====================================

Prerequisites to be placed in a INPUTS directory (see below)::

  * domain_cfg.nc
  * BLZE12_bdytide_rotT_*.nc   (FES boundary tidal forcing)
  * coordinates.bdy.nc (coordinates for FES boundary forcing)

Structure:
The git repo contains BUILD_NEMO and RUN_NEMO. BUILD_NEMO contains the dockerfiles to build the two stages of the surge container. The first stage, BASE creates an container that contains all the libraries requried to run NEMO and XIOS e.g. MPICH, NETCDF, NetCDF FORTRAN etc. This acts as a primer for the surge container which takes the BASE container and builds NEMO and XIOS on top of it. 

Once complete NEMO and XIOS are contained within the container and can be run using the docker run command and run_surge shell script that links the NEMO and XIOS executables along with INPUT data and runs the model saving output in a mounted folder that contains the NEMO model config files. An example is contained in RUN_NEMO. 

**Note**: the user does not need to build these containers, they can be pulled from the docker hub repository (see simple method).

The container can also be used interactively if prefered using the -it flag and calling bash as the container command. See Interactive Section.

The INPUTS directory is empty on cloning.  It needs to contain the forcing and
domain files that are generated externally to this instruction set. These files
are copied/linked into the `bdydta` folder in the experiment directory using the run_surge shell script.

First Steps
===========

Clone this repository
========================

Clone the repository ::

  cd $HOME
  git clone https://github.com/NOC-MSM/BLZ_SURGE.git BLZ_SURGE

Copy the INPUTS in place. EDIT <INPUTS_SOURCE> appropriately::

  rsync -uvt <INPUTS_SOURCE>/* $HOME/BLZ_SURGE/INPUTS/.

Simple Method:
=================

The user can build the container from scratch if required but both the base container and surge container are availble on docker hub. To use, first install docker and then pull the container::
  
  docker pull thopri/nemo-surge:8814

This will pull the container from the repository and install it locally. This means all the user really needs is the RUN_NEMO directory from the cloned repo. Assuming the Prerequisite input data is in the INPUTS directory the model can be run with the following command::

  docker run --rm -v /path/to/repo/RUN_NEMO/EXP_tideonly:/BLZ_SURGE thopri/nemo-surge:8814

The --rm flag removes container once finished, -v mounts the defined folder to the container. As no command is specified the container will run its default command which will run the shell script which links the executables and runs the model. 

Interactive Method
------------------

While the container runs automatically the user can start the container and use the model interactively by running following command::

  docker run --rm -it -v /path/to/repo/RUN_NEMO/EXP_tideonly:/BLZ_SURGE thopri/nemo-surge:8814 /bin/bash

Note the extra flag -it which makes the container interactive and starts a tty. There is also the command /bin/bash after the container name. This starts the bash shell rather than running the surge shell script the container is expecting.

After running this commmand, it will drop you in the mounted folder within the container. The user can then navigate the container as they wish. XIOS and NEMO are stored under /SRC directory. 

Advanced Method:
===================

If the user wishes to build from scratch then the following process can be used. Navigate to the BUILD_NEMO directory and build the base container::

  cd BUILD_NEMO
  docker build -t thopri/nemo-base base/

This tells docker that the base docker file is in the base folder and to tag (-t) the resulting container with the following name. It is important to build with this tag as the NEMO container built on top of base and it is expecting this tag. Once complete, (it takes awhile!) the NEMO container can be built as follows::

  docker build -t thopri/nemo-surge:8814 surge/

Once this completes then you have built your own NEMO surge model......

Run NEMO
===========

This section details how to run the model interactively and how the run_surge shell script works.

Link the NEMO exe and XIOS exe. ::
  
  cd /BLZ_SURGE
  ln -s /SRC/NEMOGCM/CONFIG/BLZ_SURGE/BLD/bin/nemo.exe .
  ln -s -f /SRC/XIOS/bin/xios_server.exe .

Make a link between where the inputs files are and where the model expects them ::

    cd /BLZ_SURGE/RUN_NEMO/EXP_tideonly
    ln -s ../../INPUTS bdydta
    ln -s ../../INPUTS/domain_cfg.nc .

Now `EXP_tideonly/bdydta` should directly contain `BLZE12_bdytide_rotT_*.nc` and
`coordinates.bdy.nc`
::

  cd /BLZ_SURGE/RUN_NEMO/EXP_tideonly/
  mpirun -n 2 ./nemo.exe : -n 1 ./xios_server.exe

NB the timestep, run length etc is not optimal, but it works!
