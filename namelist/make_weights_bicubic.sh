#!/bin/bash
# Within the bilinear and bicubic namelists ensure that:
# 1. the name of the data input_file is correct
# 2. the name of the NEMO coordinate file for nemo_file is correct
# 3. the input_lon, input_lat, nemo_lon, nemo_lat variables
#    correspond to the approriate fields in your input_file and nemo_file

#rm Forcing_u10_weights_bicubic.nc
#rm Forcing_v10_weights_bicubic.nc
#rm Forcing_msl_weights_bicubic.nc

echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripgrid.exe
echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scrip.exe
echo "namelist_reshape_bilin_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripshape.exe
echo "namelist_reshape_bicubic_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scrip.exe
echo "namelist_reshape_bicubic_atmos" | /SRC/NEMOGCM/TOOLS/WEIGHTS/scripshape.exe

rm remap_nemo_grid_atmos.nc
rm remap_data_grid_atmos.nc
rm data_nemo_bilin_atmos.nc
rm weights_bilinear_atmos.nc
rm data_nemo_bicubic_atmos.nc
