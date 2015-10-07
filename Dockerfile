FROM ubuntu:15.10
RUN apt-get update && apt-get install -y git python curl pax gzip tar subversion autoconf build-essential libxml2-dev openssl libssl-dev make libz-dev libusb-dev cmake libbz2-dev libpng-dev wget
RUN apt-get install -y virtualenv
RUN useradd -d /home/worker -s /bin/bash -m worker
RUN mkdir /opt/data-reposado/
RUN chown worker.worker /opt/data-reposado/
ADD run.sh list-packages.py DumpBreakpadSymbols.py PackageSymbolDumper.py /home/worker/
RUN chmod +x /home/worker/run.sh /home/worker/list-packages.py /home/worker/DumpBreakpadSymbols.py /PackageSymbolDumper.py
USER worker
WORKDIR /home/worker
ADD setup.sh /tmp/
RUN /bin/sh /tmp/setup.sh

