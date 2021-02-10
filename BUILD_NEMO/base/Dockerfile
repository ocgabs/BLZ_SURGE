### Installs the framework for the NEMO Ocean Engine compilation ###
####################################################################

FROM debian:buster as builder

MAINTAINER thopri <thopri@noc.ac.uk>

### dependencies for NEMO:
# bash, perl, svn, fortran90 compiler, mpi, netcdf, netcdf-fortran, make
# http://www.nemo-ocean.eu/Using-NEMO/User-Guides/Basics/NEMO-Quick-Start-Guide

### dependencies for XIOS: netcdf4 hdf5
# http://forge.ipsl.jussieu.fr/ioserver/wiki/documentation
### notes:
# ssh is required in order for MPI to run properly
# nano, python2.7 are not mandatory but useful when we have to work in the container

ARG REQUIRE="sudo make gcc g++ binutils file libc-dev ssh m4 libtool automake autoconf bzip2 bash"
ARG PACKAGES="wget bzip2 ca-certificates zlib1g zlib1g-dev libcurl3-openssl-dev libcurl4 git gfortran" 

RUN apt-get update && apt-get upgrade --no-install-recommends -y \
      && apt-get install  --no-install-recommends -y ${REQUIRE} ${PACKAGES} \ 
      && rm -rf /var/lib/apt/lists/*

#### INSTALL MPICH ####
# Source is available at http://www.mpich.org/static/downloads/

# Build Options:
# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below
ARG MPICH_VERSION="3.2.1"
ARG MPICH_CONFIGURE_OPTIONS=""
ARG MPICH_MAKE_OPTIONS

# Download, build, and install MPICH
RUN mkdir /tmp/mpich-src
WORKDIR /tmp/mpich-src
RUN wget http://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz \
      && tar xfz mpich-${MPICH_VERSION}.tar.gz  \
      && cd mpich-${MPICH_VERSION}  \
      && ./configure ${MPICH_CONFIGURE_OPTIONS}  \
      && make ${MPICH_MAKE_OPTIONS} && make install \
      && rm -rf /tmp/mpich-src


#### INSTALL HDF5 ####
ARG HDF5_VERSION="1.10.4"
ARG H5DIR=/usr/local
ARG HDF5_CONFIGURE_OPTIONS="--enable-parallel --enable-fortran \
      --prefix=${H5DIR}"
ARG CC=mpicc
ARG FC=mpif90
ARG F77=mpif77
ARG CXX=mpicxx
ARG LIBS="-ldl -lmpi"
ARG CFLAGS="-fPIC"
ENV CPPFLAGS="-I/usr/local/include -I/usr/include"
ENV LD_LIBRARY_PATH="/usr/lib:/usr/local/lib"
ENV LDFLAGS="-L/usr/local/lib -L/usr/lib"
# Download, build, and install HDF5
RUN mkdir /tmp/hdf5-src
WORKDIR /tmp/hdf5-src
RUN wget https://www.hdfgroup.org/package/source-gzip-4/?wpdmdl=13048 \
      -O hdf5-${HDF5_VERSION}.tar.gz \
      && tar xfz hdf5-${HDF5_VERSION}.tar.gz  \
      && mkdir hdf5-fortran \
      && cd hdf5-fortran  \
      && ../hdf5-${HDF5_VERSION}/configure ${HDF5_CONFIGURE_OPTIONS}  \
      && make check && make install \
      && rm -rf /tmp/hdf5-src


#### INSTALL PARALLEL NETCDF ####
ARG PNCDF_VERSION="1.9.0"
ARG PNCDFDIR=/usr/local
ARG PNCDF_CONFIGURE_OPTIONS="--with-mpi=/usr/local/bin \
      --enable-relax-coord-bound \
      --prefix=${PNCDFDIR}"

# Download, build, and install PNetCDF
RUN mkdir /tmp/pnetcdf-src
WORKDIR /tmp/pnetcdf-src
RUN wget https://parallel-netcdf.github.io/Release/parallel-netcdf-${PNCDF_VERSION}.tar.gz \
      && tar xfz parallel-netcdf-${PNCDF_VERSION}.tar.gz  \
      && cd parallel-netcdf-${PNCDF_VERSION}  \
      && ./configure ${PNCDF_CONFIGURE_OPTIONS}  \
      && make check && make install \
      && rm -rf /tmp/pnetcdf-src

#### INSTALL NETCDF-C ####
ARG NCDF_COMMIT="56f9489"
ARG NCDFDIR=/usr/local
ARG NCDF_CONFIGURE_OPTIONS="--enable-parallel-tests --enable-pnetcdf \
      --prefix=${NCDFDIR}"

# Download, build, and install PNetCDF
RUN mkdir /tmp/netcdf-src
WORKDIR /tmp/netcdf-src
RUN git clone https://github.com/Unidata/netcdf-c.git
WORKDIR /tmp/netcdf-src/netcdf-c 
#RUN git reset --hard ${NCDF_COMMIT} 
RUN autoreconf -i
COPY fix_tst_cdf5format_for_loop.patch .
#RUN git apply fix_tst_cdf5format_for_loop.patch \
RUN ./configure ${NCDF_CONFIGURE_OPTIONS}  \
      && make check && make install \
      && rm -rf /tmp/netcdf-src

#### INSTALL NETCDF-FORTRAN ####
#ARG NCDFF_COMMIT="56f9489"
ARG NCDFF_COMMIT="7328f52"
ARG NCDFFDIR=/usr/local
ARG NCDFF_CONFIGURE_OPTIONS="--enable-parallel-tests \
      --disable-shared --prefix=${NCDFDIR}"
ARG CFLAGS='-g -Wall'

# Download, build, and install PNetCDF
RUN mkdir /tmp/netcdff-src
WORKDIR /tmp/netcdff-src
RUN git clone https://github.com/Unidata/netcdf-fortran.git \
      && cd netcdf-fortran \
      && git reset --hard ${NCDFF_COMMIT} \
      && autoreconf -i \
      && ./configure ${NCDFF_CONFIGURE_OPTIONS}  \
      && make check && make install \
      && rm -rf /tmp/netcdff-src
