#!/bin/bash
echo "Linking NEMO exe"
ln -s -f /SRC/NEMOGCM/CONFIG/BLZ_SURGE/BLD/bin/nemo.exe .
sleep 1
echo "Linking XIOS server"
ln -s -f /SRC/XIOS/bin/xios_server.exe .
sleep 1
echo "Linking Data INPUTS"
ln -s -f ~/BLZ_SURGE/INPUTS bdydta
sleep 1
echo "Running Model Now"
mpirun -n 2 ./nemo.exe : -n 1 ./xios_server.exe
