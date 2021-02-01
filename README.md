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

The notes for the docker build were built on those made by Pierre DERIAN
https://github.com/pderian/NEMOGCM-Docker (see also BUILD_NEMO/readme.txt)

0) Prerequisites and path definitions
=====================================

Prerequisits to be placed in $INPUTS (defined below)::

  * domain_cfg.nc
  * BLZE12_bdytide_rotT_*.nc   (FES boundary tidal forcing)
  * coordinates.bdy.nc (coordinates for FES boundary forcing)

Define some paths (edit the path for $INPUTS accordingly)::

  export CONFIG=BLZ_SURGE
  export WDIR=$HOME/$CONFIG
  export INPUTS=$WDIR/INPUTS
  export EXP=$WDIR/RUN_NEMO/EXP_tideonly


1) Clone this repository
========================

Clone the repository ::

  cd $HOME
  git clone https://github.com/NOC-MSM/BLZ_SURGE.git $CONFIG



2) Get XIOS2.5 @ r2022 code
===========================

Note when NEMO (nemo.exe / opa) is compiled it is done with reference to a
particular version of XIOS. So on NEMO run time the version of XIOS that built
`xios_server.exe` must be compatible with the version of XIOS that built
nemo.exe / opa.

Download XIOS2.5 and prep::

  cd $WDIR/BUILD_NEMO
  svn co -r2022 http://forge.ipsl.jussieu.fr/ioserver/svn/XIOS/branchs/xios-2.5/  xios-2.5_r2022
  cd xios-2.5_r2022

Link the xios-2.5_r2022 to a generic XIOS directory name (The generic name is
  used in the NEMO build arch files)::

  ln -s  $WDIR/BUILD_NEMO/xios-2.5_r2022  $WDIR/BUILD_NEMO/XIOS2


3) Get NEMO codebase
====================

Get the code::

  cd $WDIR/BUILD_NEMO
  svn co http://forge.ipsl.jussieu.fr/nemo/svn/branches/UKMO/dev_r8814_surge_modelling_Nemo4/NEMOGCM dev_r8814_surge_modelling_Nemo4

Make a link between where the inputs files are and where the model expects them ::

    ln -s $INPUTS $EXP/bdydta

Now `$EXP/bdydta` should directly contain `BLZE12_bdytide_rotT_*.nc` and
`coordinates.bdy.nc`


4) Copy the architecture files
==============================

Copy NEMO and XIOS arch files to appropriate folder for building::

  cp $WDIR/BUILD_NEMO/arch_NEMOGCM/arch* $WDIR/BUILD_NEMO/dev_r8814_surge_modelling_Nemo4/ARCH
  cp $WDIR/BUILD_NEMO/arch_XIOS/arch* $WDIR/BUILD_NEMO/XIOS2/arch




5) Build the Debian Docker image
================================

cd $WDIR/BUILD_NEMO/Docker
docker build -t nemo/compiler .


6) Start an interactive container
=================================

Start an interactive container sharing the source files as a Volume.
This way the host SRC will be available from within the container as /SRC.
/!\ Note: /host/path/to/SRC must be the _absolute_ path to the host SRC directory
(at least on Mac OS X)::

  docker run -v $WDIR:/$CONFIG -t -i nemo/compiler /bin/bash
  # I.e. docker run -v /host/path/to/BLZ_SURGE:/BLZ_SURGE -t -i nemo/compiler /bin/bash

From here on, unless otherwise stated, all the commands are executed within the
 docker container.

7) Compile XIOS
===============

::

  cd /BLZ_SURGE/BUILD_NEMO/XIOS2
  ./make_xios --dev --netcdf_lib netcdf4_seq --arch DEBIAN

Copy the executable to the experiment directory::

  cp /BLZ_SURGE/BUILD_NEMO/XIOS2/bin/xios_server.exe  /BLZ_SURGE/RUN_NEMO/EXP_tideonly/.



8) Build NEMO executable
========================

Make NEMO executable::

  cd /BLZ_SURGE/BUILD_NEMO/dev_r8814_surge_modelling_Nemo4/CONFIG
  ./makenemo -v 3 –m DEBIAN -n BLZ_SURGE

Copy the executable to the experiment directory::

  cp /BLZ_SURGE/BUILD_NEMO/dev_r8814_surge_modelling_Nemo4/CONFIG/BLZ_SURGE/BLD/bin/nemo.exe  /BLZ_SURGE/RUN_NEMO/EXP_tideonly/.


9) Run NEMO
===========

::

  cd /BLZ_SURGE/RUN_NEMO/EXP_tideonly/
  mpirun -n 2 ./nemo.exe : -n 1 ./xios_server.exe
