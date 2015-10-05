#!/bin/sh
set -v -e -x

ncpu=-j`grep -c ^processor /proc/cpuinfo`

svn checkout http://xar.googlecode.com/svn/trunk/ xar-read-only
cd xar-read-only/xar
./autogen.sh
make $ncpu && make install
cd ../..

git clone https://github.com/planetbeing/xpwn
mkdir xpwn-build
cd xpwn-build
cmake ../xpwn/
make $ncpu
cd ..

git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH=$PATH:$PWD/depot_tools
mkdir breakpad
cd breakpad
fetch breakpad
cd src
touch README
./configure
make $ncpu
cd ../..


git clone https://github.com/wdas/reposado
mkdir -p /opt/data-reposado/{html,metadata}
cd reposado
python setup.py install
cd ..

repoutil --configure <<EOF
/opt/data-reposado/html/
/opt/data-reposado/metadata/
http://example.com/
EOF

