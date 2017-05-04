#!/bin/sh
. /home/worker/venv/bin/activate

set -v -e -x

base="$(realpath $(dirname $0))"
export PATH="$PATH:/home/worker/bin:$base"

cd /home/worker

if test "$PROCESSED_PACKAGES"; then
  curl -L "$PROCESSED_PACKAGES" | gzip -dc > processed-packages
  # Prevent reposado from downloading packages that have previously been
  # dumped.
  for f in `cat processed-packages`; do
      mkdir -p `dirname $f`
      touch $f
  done
fi

mkdir -p /opt/data-reposado/html /opt/data-reposado/metadata

# Make sure we're using the latest reposado.
git clone https://github.com/wdas/reposado
(cd reposado; python setup.py install)

# Grab a patched copy of repo_sync
curl -L https://github.com/luser/reposado/raw/04ed48690a2c5335f8b594d78bf894dd8713ab24/code/repo_sync > /home/worker/venv/bin/repo_sync

# First, just fetch all the update info.
repo_sync --no-download

# Next, fetch just the update packages we're interested in.
repo_sync $(python "${base}/list-packages.py")

# Now scrape symbols out of anything that was downloaded.
mkdir -p symbols artifacts
python "${base}/PackageSymbolDumper.py" --tracking-file=/home/worker/processed-packages --dump_syms=/home/worker/bin/dump_syms_mac /opt/data-reposado/html/content/downloads /home/worker/symbols

# Hand out artifacts
gzip -c processed-packages > artifacts/processed-packages.gz

cd symbols
zip -r9 /home/worker/artifacts/target.crashreporter-symbols.zip * || echo "No symbols dumped"
