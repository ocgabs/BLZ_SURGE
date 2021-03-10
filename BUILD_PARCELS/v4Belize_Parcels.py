from parcels import ErrorCode, FieldSet, ParticleSet, ScipyParticle, JITParticle, AdvectionRK4, ParticleFile
from argparse import ArgumentParser
import numpy as np
import pytest
from glob import glob
from datetime import timedelta as delta
from os import path
import time
from netCDF4 import Dataset


import csv
with open('/projectsa/CME/BLZ_SURGE/PARCELS/ilonv.csv') as csvfile:
    file1 = csv.reader(csvfile, delimiter=',')
    LOS = []
    for row in file1:
        LO = row[0]
#        LA = row[1]
        LOS.append(LO)
#        LAS.append(LA)
with open(r'/projectsa/CME/BLZ_SURGE/PARCELS/ilatv.csv') as csvfile:
    file2 = csv.reader(csvfile, delimiter=',')
    LAS = []
    for row in file2:
        LA = row[0]
        LAS.append(LA)
print(type(LAS))

start = time.time()
# data_path = path.join(path.dirname(__file__), 'NemoCurvilinear_data/')
data_path = '/projectsa/accord/GCOMS1k/OUTPUTS/BLZE12_02/2011/'
ufiles = sorted(glob(data_path+'BLZE12_1h_*U.nc'))
vfiles = sorted(glob(data_path+'BLZE12_1h_*V.nc'))

grid_file = '/projectsa/accord/GCOMS1k/INPUTS/BLZE12/BLZE12_coordinates.nc'
filenames = {'U': {'lon': grid_file,
                       'lat': grid_file,
                       'data': ufiles},
                 'V': {'lon': grid_file,
                       'lat': grid_file,
                       'data': vfiles}}
variables = {'U': 'ssu', 'V': 'ssv'}
dimensions = {'lon': 'glamf', 'lat': 'gphif','time': 'time_counter' }
field_set = FieldSet.from_nemo(filenames, variables, dimensions)
	
	#Plot u field
#field_set.U.show()

    # Make particles initial position list
nc_fid = Dataset(grid_file, 'r') #open grid file nc to read
lats = nc_fid.variables['nav_lat'][:]  # extract/copy the data
lons = nc_fid.variables['nav_lon'][:]

lonE=lons[:,169-3]
latE=lats[:,169-3]

npart = 3000
lonp = [i for i in np.linspace(min(lonE), max(lonE), npart)] 
latp = [i for i in np.linspace(15.98, max(latE), npart)] #this makes a list!
	
pset = ParticleSet.from_list(field_set, JITParticle, lon=lonp, lat=latp)
pfile = ParticleFile("nBelize_nemo_sargaso_particlesT2", pset, outputdt=delta(hours=0.5))
kernels = pset.Kernel(AdvectionRK4)
#Plot initial positions
#pset.show()
def DeleteParticle(particle, fieldset, time):
    particle.delete()


pset.execute(kernels, runtime=delta(days=7), dt=delta(hours=0.1),  output_file= pfile, recovery={ErrorCode.ErrorOutOfBounds: DeleteParticle})

pfile.close()

#plotTrajectoriesFile("nBelize_nemo_sargaso_particlesT2");

#pset.show(domain={'N':-31, 'S':-35, 'E':33, 'W':26})
#pset.show(field=field_set.U)
#pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2))
#pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2), with_particles=False)


end = time.time()
print(end-start)
