#!/bin/sh
set -v -e -x

ncpu=-j`grep -c ^processor /proc/cpuinfo`

WORK=`mktemp -d`
cd $WORK
git clone https://github.com/mackyle/xar xar
cd xar/xar
./autogen.sh --prefix=/home/worker
make $ncpu && make install

cd $WORK
git clone https://github.com/planetbeing/xpwn
mkdir xpwn-build
cd xpwn-build
cmake ../xpwn/
make $ncpu dmg-bin
# `make install` installs way too much stuff
cp dmg/dmg /home/worker/bin
strip /home/worker/bin/dmg

cd $WORK
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH=$PATH:$PWD/depot_tools
mkdir breakpad
cd breakpad
fetch breakpad
cd src
touch README
./configure
make $ncpu src/tools/mac/dump_syms/dump_syms
# `make install` is broken because there are two dump_syms binaries.
cp src/tools/mac/dump_syms/dump_syms /home/worker/bin
strip /home/worker/bin/dump_syms

cd $WORK
virtualenv /home/worker/venv
. /home/worker/venv/bin/activate
git clone -b repo-sync-options https://github.com/luser/reposado.git # https://github.com/wdas/reposado
cd reposado
python setup.py install

cd $WORK
mkdir -p /opt/data-reposado/{html,metadata}
repoutil --configure <<EOF
/opt/data-reposado/html/
/opt/data-reposado/metadata/
http://example.com/
EOF

cd $WORK
git clone https://github.com/luser/breakpad-scrape-system-symbols.git
cd breakpad-scrape-system-symbols
python setup.py install

cd /tmp
rm -rf $WORK
