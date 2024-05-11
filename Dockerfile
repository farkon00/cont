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

RUN groupadd -g 2000 bischebis \
&& useradd -m -u 2001 -g bischebis bischebis

USER bischebis
WORKDIR /home/bischebis
RUN mkdir cont
COPY --chown=bischebis:bischebis . cont
WORKDIR cont
