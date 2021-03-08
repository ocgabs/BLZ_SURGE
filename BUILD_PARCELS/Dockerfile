
# See https://github.com/NOC-MSM/BLZ_SURGE

FROM continuumio/miniconda3 AS build

# Install the package as normal:
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -a -y

# Install conda-pack:
RUN conda install -c conda-forge -y conda-pack

# Use conda-pack to create a standalone enviornment
# in /venv:
RUN conda-pack -n py3_parcels_mpi -o /tmp/env.tar && \
  mkdir /py3_parcels_mpi && cd /py3_parcels_mpi && tar xf /tmp/env.tar && \
  rm /tmp/env.tar

# We've put venv in same path it'll be in final image,
# so now fix up paths:
RUN /py3_parcels_mpi/bin/conda-unpack

# The runtime-stage image; we can use Debian as the
# base image since the Conda env also includes Python
# for us.
FROM debian:buster AS runtime

# Copy /venv from the previous stage:
COPY --from=build /py3_parcels_mpi /py3_parcels_mpi

# Add entry to bashrc of container to activate environment on container start
RUN echo source /py3_parcels_mpi/bin/activate >> ${HOME}/.bashrc

# When image is run, run the code with the environment
# activated:
#SHELL ["/bin/bash", "-c"]
#ENTRYPOINT source /py3_parcels_mpi/bin/activate && \
#            python -c "import numpy; print('success!')"





