FROM debian

SHELL ["/bin/bash", "-c"]

RUN apt-get update
RUN apt install -y git \
    python3 \
    python3-pytest \
    fasm \
    nodejs \
    wabt 
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /
RUN mkdir cont
COPY . cont
WORKDIR cont
