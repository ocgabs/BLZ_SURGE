#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 17:52:52 2020

@author: gmaya
"""

import datetime as dt  # Python standard library datetime  module
import numpy as np
from netCDF4 import Dataset  # http://code.google.com/p/netcdf4-python/
import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap, addcyclic, shiftgrid
import os
from random import randint

nc_f = 'Belize_nemo_particles_3000p30d.nc'  # Your filename
nc_fid = Dataset(nc_f, 'r')  # Dataset is the class behavior to open the file
                                # and create an instance of the ncCDF4 class
#nc_attrs, nc_dims, nc_vars = ncdump(nc_fid) #ncdump functions needs to be coded
# Extract data from NetCDF file
lats = nc_fid.variables['lat'][:]  # extract/copy the data
lons = nc_fid.variables['lon'][:]
time = nc_fid.variables['time'][:]
plt.figure()
for x in range(1,100):
    p=randint(0,len(lats)-1) #Returns a random integer between the specified integers.
    # PLOT
    
    plt.plot(lons[p,:],lats[p,:],'r') 
    
    # plt.plot(lons[:,30],lats[:,30],'b.') 
plt.show()
dlat=np.diff(lats) #along track difference of latitude
dlon=np.diff(lons)
pstop=0
delp=0
nstop=[None]
wstop=[None]
la0 = []
for x in range(len(dlat)):
    pdlat=dlat.data[x,:] #along track difference of latitude of each particle
    pdlon=dlon.data[x,:]
    plat=lats.data[x,:]
    plon=lons.data[x,:]
    ptime=time.data[x,:]
    nla = np.isnan(plat) #Check if particle was deleted, if position is NAN
    if nla.any()==True :
        delp=delp+1
    #if ptime.any() == 'NaT': #when are particles deleted
    nan_indx = np.argwhere(np.isnan(plat))
    if len(la0) > 0 and len(la0[0]) > 0:
        wstop.append(nan_indx)
    la0 = np.where(pdlat == 0) #find where dlat ==0
    lo0 = np.where(pdlon == 0)
    if len(la0) > 0 and len(la0[0]) > 0 and len(lo0) > 0 and len(lo0[0]) > 0:   #this checks if la0 is NOT empty
        pstop=pstop+1 #if la0 and lo0 NOT empty particle has stoped 
        
print(pstop)
print('deleted particles ' +str(delp))
nstop.append(pstop)
#print('when particle stopped' '\n' + str(wstop))

            
