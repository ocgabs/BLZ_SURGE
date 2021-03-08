

from parcels import FieldSet, ParticleSet, JITParticle, AdvectionRK4_3D
from glob import glob
import numpy as np
from datetime import timedelta as delta
from os import path




# data_path = path.join(path.dirname(__file__), 'NemoCurvilinear_data/')
data_path = '/projectsa/accord/GCOMS1k/OUTPUTS/BLZE12_01/2011/'
ufiles = sorted(glob(data_path+'BLZE12_1h_*U.nc'))
vfiles = sorted(glob(data_path+'BLZE12_1h_*V.nc'))

grid_file = '/projectsa/accord/GCOMS1k/INPUTS/BLZE12/BLZE12_coordinates.nc'
filenames = {'U': {'lon': grid_file,
                       'lat': grid_file,
                       'data': ufiles},
                 'V': {'lon': grid_file,
                       'lat': grid_file,
                       'data': vfiles}}
variables = {'U': 'ubar', 'V': 'vbar'}
dimensions = {'lon': 'glamf', 'lat': 'gphif','time': 'time_counter' }
field_set = FieldSet.from_nemo(filenames, variables, dimensions)

#For 3D ocean field plotting
#Matplotlib inline
#
#depth_level = 1
#print("Level[%d] depth is: [%g %g]" % (depth_level, field_set.W.grid.depth[depth_level], field_set.W.grid.depth[depth_level+1]))

#pset.show(field=field_set.W, domain={'N':15, 'N':21, 'W':89 ,'W':85.5}, depth_level=depth_level)
