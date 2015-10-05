FROM ubuntu:15.10
RUN apt-get update && apt-get install -y git python curl pax gzip tar subversion autoconf build-essential libxml2-dev openssl libssl-dev make libz-dev libusb-dev cmake libbz2-dev libpng-dev wget
ADD setup.sh /tmp/
RUN /bin/sh /tmp/setup.sh
ADD run.sh branch.py DumpBreakpadSymbols.py PackageSymbolDumper.py /
RUN chmod +x /run.sh /branch.py /DumpBreakpadSymbols.py /PackageSymbolDumper.py
