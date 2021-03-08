from parcels import FieldSet, ParticleSet, ScipyParticle, JITParticle, AdvectionRK4, ParticleFile,Variable
from argparse import ArgumentParser
import numpy as np
import pytest
from glob import glob
from datetime import timedelta as delta
from os import path
import time
from netCDF4 import Dataset

start = time.time()
# data_path = path.join(path.dirname(__file__), 'NemoCurvilinear_data/')
data_path = 'INPUTS/'
ufiles = sorted(glob(data_path+'BLZE12_1h_*U.nc'))
vfiles = sorted(glob(data_path+'BLZE12_1h_*V.nc'))

grid_file = 'INPUTS/BLZE12_coordinates.nc'
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

#     # Make particles initial position list
#nc_fid = Dataset(grid_file, 'r') #open grid file nc to read
#lats = nc_fid.variables['nav_lat'][:]  # extract/copy the data
#lons = nc_fid.variables['nav_lon'][:]
#
#lonE=lons[:,169-3]
#latE=lats[:,169-3]
#
#npart = 3000
#lonp = [i for i in np.linspace(min(lonE), max(lonE), npart)]
#latp = [i for i in np.linspace(15.98, max(latE), npart)] #this makes a list!

lonp = np.load('sargassium/slo.npy')
latp = np.load('sargassium/sla.npy')
latp = np.ndarray.tolist(latp)
lonp = np.ndarray.tolist(lonp)
maxlats = field_set.gridset.grids[0].lat.max()
minlats = field_set.gridset.grids[0].lat.min()
maxlons = field_set.gridset.grids[0].lon.max()
minlons = field_set.gridset.grids[0].lon.min()

for i in range(len(latp)):
    if latp[i] >= maxlats:
        latp[i] = -999.999
        lonp[i] = -999.999
    if latp[i] <= minlats:
        latp[i] = -999.999
        lonp[i] = -999.999
    if lonp[i] >= maxlons:
        latp[i] = -999.999
        lonp[i] = -999.999
    if lonp[i] <= minlons:
        latp[i] = -999.999
        lonp[i] = -999.999

latp = [x for x in latp if x != -999.999]
lonp = [x for x in lonp if x != -999.999]

pset = ParticleSet.from_list(field_set, JITParticle, lon=lonp, lat=latp)
pfile = ParticleFile("RUN_PARCELS/Belize_nemo_particles_3000p30d", pset, outputdt=delta(hours=0.5))
kernels = pset.Kernel(AdvectionRK4)
#Plot initial positions
#pset.show()

pset.execute(kernels, runtime=delta(days=30), dt=delta(hours=0.1),
            output_file=pfile)
#plotTrajectoriesFile("Belize_nemo_particles_t2.nc");

#pset.show(domain={'N':-31, 'S':-35, 'E':33, 'W':26})
#pset.show(field=field_set.U)
#pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2))
#pset.show(field=fieldset.U, show_time=datetime(2002, 1, 10, 2), with_particles=False)


end = time.time()
print(end-start)
