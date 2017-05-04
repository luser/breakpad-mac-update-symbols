#!/bin/sh
. /home/worker/venv/bin/activate

set -v -e -x

base="$(realpath $(dirname $0))"
export PATH="$PATH:/home/worker/bin:$base"

cd /home/worker

mkdir -p symbols artifacts
# Download and dump update packages.
python "${base}/get_update_packages.py" --dump_syms=/home/worker/bin/dump_syms_mac /home/worker/symbols

# Hand out artifacts
cd symbols
zip -r9 /home/worker/artifacts/target.crashreporter-symbols.zip * || echo "No symbols dumped"
