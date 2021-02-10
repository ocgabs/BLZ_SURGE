### Installs the framework for the NEMO Ocean Engine compilation ###
####################################################################
FROM thopri/nemo-base:latest as base
FROM debian:buster as surge

# Based on NEMO-Docker by Pierre Derian, contact@pierrederian.net, www.pierrederian.net
MAINTAINER thopri  <thopri@noc.ac.uk> 
ARG NEMO_REF_CONFIG=GYRE_PISCES
ARG NEMO_CONFIG=BLZ_SURGE
ARG KEY=key_nosignedzero

COPY --from=base /usr/local /usr/local

USER root

### dependencies for NEMO:
# bash, perl, svn, fortran90 compiler, mpi, netcdf, netcdf-fortran, make
# from http://www.nemo-ocean.eu/Using-NEMO/User-Guides/Basics/NEMO-Quick-Start-Guide
### dependencies for XIOS: netcdf4 hdf5
# from http://forge.ipsl.jussieu.fr/ioserver/wiki/documentation
### notes:
# ssh is required in order for MPI to run properly
# nano, python2.7 are not mandatory but useful when we have to work in the container
ENV PACKAGES="subversion make gcc g++ ssh nfs-common"
ENV PACKAGES_NEMO="perl gfortran"
ENV PACKAGES_XIOS="liburi-perl zlib1g zlib1g-dev libcurl4"

### first update then install the main packages
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ${PACKAGES} ${PACKAGES_NEMO} ${PACKAGES_XIOS} 

ENV REF_CONFIG ${NEMO_REF_CONFIG}
ENV CONFIG ${NEMO_CONFIG}
ENV WDIR /SRC
ENV MNT_DIR /mnt/data
ENV XDIR ${WDIR}/XIOS
ENV INPUTS ${WDIR}/INPUTS
ENV START_FILES ${WDIR}/START_FILES
ENV CDIR ${WDIR}/NEMOGCM
ENV TDIR ${WDIR}/NEMOGCM/TOOLS
ENV EXP ${CDIR}/CONFIG/$CONFIG/EXP00

RUN mkdir ${WDIR} && mkdir -p ${MNT_DIR}

WORKDIR ${WDIR}

RUN svn co --non-interactive --trust-server-cert http://forge.ipsl.jussieu.fr/nemo/svn/branches/UKMO/dev_r8814_surge_modelling_Nemo4/NEMOGCM dev_r8814_surge_modelling_Nemo4 \
     && ln -s dev_r8814_surge_modelling_Nemo4 NEMOGCM

RUN svn co -r2022 http://forge.ipsl.jussieu.fr/ioserver/svn/XIOS/branchs/xios-2.5/ xios-2.5_r2022 \
    && ln -s xios-2.5_r2022 XIOS

COPY arch_NEMOGCM/arch* NEMOGCM/ARCH/
COPY arch_XIOS/arch* XIOS/arch/

WORKDIR ${XDIR}
# Enable test_client to be built
RUN sed -i "s/#bld::target test_client.exe/bld::target test_client.exe/" /SRC/XIOS/bld.cfg
# Build XIOS
RUN ./make_xios --full --prod --netcdf_lib netcdf4_par --arch DEBIAN

WORKDIR ${CDIR}/CONFIG

RUN mkdir ${CONFIG}

COPY MY_SRC/* ${CONFIG}/MY_SRC/ 

RUN printf 'y\nn\nn\nn\nn\nn\nn\nn\n' | ./makenemo -v 3 -n ${CONFIG} -m DEBIAN clean
#RUN ln -s  ${XDIR}/bin/xios_server.exe ${EXP}/xios_server.exe

COPY cpp_${CONFIG}.fcm ${CONFIG}/cpp_${CONFIG}.fcm
#ADD MY_SRC.tar.gz ${CONFIG}/

RUN ./makenemo -v 3 -n ${CONFIG} -m DEBIAN add_key ${KEY}
#RUN ./makenemo -v 3 -r ${REF_CONFIG} -n ${CONFIG} -m DEBIAN add_key ${KEY}
RUN ln -s  ${XDIR}/bin/xios_server.exe ${EXP}/xios_server.exe 

WORKDIR /${CONFIG}
CMD ["/bin/sh","./run_surge.sh"]
