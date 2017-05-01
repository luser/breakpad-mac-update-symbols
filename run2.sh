#!/bin/sh
. /home/worker/venv/bin/activate

set -v -e -x

base="$(realpath $(dirname $0))"
export PATH="$PATH:/home/worker/bin:$base"

cd /home/worker

mkdir -p packages
# Download update packages.
python "${base}/get-update-packages.py" /home/worker/packages

# Now scrape symbols out of anything that was downloaded.
mkdir -p symbols artifacts
python "${base}/PackageSymbolDumper.py" --dmg=/home/worker/bin/dmg --dump_syms=/home/worker/bin/dump_syms_mac /home/worker/packages /home/worker/symbols

# Hand out artifacts
cd symbols
zip -r9 /home/worker/artifacts/target.crashreporter-symbols.zip * || echo "No symbols dumped"
