FROM ubuntu:15.10
# If host is running squid-deb-proxy on port 8000, populate /etc/apt/apt.conf.d/30proxy
# By default, squid-deb-proxy 403s unknown sources, so apt shouldn't proxy ppa.launchpad.net
RUN awk '/^[a-z]+[0-9]+\t00000000/ { printf("%d.%d.%d.%d\n", "0x" substr($3, 7, 2), "0x" substr($3, 5, 2), "0x" substr($3, 3, 2), "0x" substr($3, 1, 2)) }' < /proc/net/route > /tmp/host_ip.txt
RUN perl -pe 'use IO::Socket::INET; chomp; $socket = new IO::Socket::INET(PeerHost=>$_,PeerPort=>"8000"); print $socket "HEAD /\n\n"; my $data; $socket->recv($data,1024); exit($data !~ /squid-deb-proxy/)' <  /tmp/host_ip.txt \
  && (echo "Acquire::http::Proxy \"http://$(cat /tmp/host_ip.txt):8000\";" > /etc/apt/apt.conf.d/30proxy) \
  && (echo "Acquire::http::Proxy::ppa.launchpad.net DIRECT;" >> /etc/apt/apt.conf.d/30proxy) \
  || echo "No squid-deb-proxy detected on docker host"
RUN apt-get update && apt-get install -y git python curl pax gzip tar subversion autoconf build-essential libxml2-dev openssl libssl-dev make libz-dev libusb-dev cmake libbz2-dev libpng-dev wget virtualenv
RUN useradd -d /home/worker -s /bin/bash -m worker
RUN mkdir /opt/data-reposado/
RUN mkdir /home/worker/bin/
ADD lipo /home/worker/bin/
RUN chmod +x /home/worker/bin/lipo
RUN chown -R worker.worker /opt/data-reposado/ /home/worker/bin/
ADD run.sh list-packages.py PackageSymbolDumper.py /home/worker/
RUN chmod +x /home/worker/run.sh /home/worker/list-packages.py /home/worker/PackageSymbolDumper.py
USER worker
WORKDIR /home/worker
ADD setup.sh /tmp/
RUN /bin/sh /tmp/setup.sh
