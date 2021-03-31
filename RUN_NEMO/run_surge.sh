#!/bin/bash
echo "Linking NEMO exe"
ln -s -f /SRC/NEMOGCM/CONFIG/BLZ-SURGE/BLD/bin/nemo.exe .
sleep 1
echo "Linking XIOS server"
ln -s -f /SRC/XIOS/bin/xios_server.exe .
sleep 1
echo "Linking Data INPUTS"
ln -s -f /BLZ-SURGE/INPUTS bdydta
ln -s -f /BLZ-SURGE/INPUTS/domain_cfg.nc .
sleep 1
echo "Running Model Now"
mpirun -n 4 ./nemo.exe : -n 2 ./xios_server.exe
