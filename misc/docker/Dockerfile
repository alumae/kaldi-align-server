FROM debian:9
MAINTAINER Tanel Alumae <alumae@gmail.com>

RUN apt-get update && apt-get install -y  \
    autoconf \
    automake \
    bzip2 \
    zip \
    g++ \
    gfortran \
    git \
    libatlas3-base \
    libtool-bin \
    make \
    python2.7 \
    python3 \
    python-pip \
    python-dev \
    python3-dev \
    sox \
    ffmpeg \
    subversion \
    wget \
    zlib1g-dev && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    ln -s -f /usr/bin/python3 /usr/bin/python ; ln -s -f bash /bin/sh

WORKDIR /opt

RUN git clone https://github.com/kaldi-asr/kaldi && \
    cd /opt/kaldi/tools && \
    make -j8 && \
    cd /opt/kaldi/src && ./configure --shared && \
    sed -i '/-g # -O0 -DKALDI_PARANOID/c\-O3 -DNDEBUG' kaldi.mk && \
    make -j8 depend && make -j8

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y locales

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8
    
ENV LANG en_US.UTF-8

RUN apt-get install -y openjdk-8-jre-headless

RUN apt-get install -y openjdk-8-jre-headless

RUN apt-get install -y python3-pip uuid-runtime icu-devtools

RUN pip3 install tornado textgrid

RUN echo 2 > /dev/null && \
    git clone https://github.com/alumae/kaldi-align-server.git
    
RUN perl -i -npe 's#KALDI_ROOT=.*#KALDI_ROOT=/opt/kaldi#' /opt/kaldi-align-server/aligner/align.sh

WORKDIR /opt/kaldi-align-server

ENTRYPOINT ["python3", "server/main.py"]
