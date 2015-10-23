#!/bin/sh
set -v -e -x

export PATH=$PATH:~/bin

if test "$PROCESSED_PACKAGES"; then
  curl "$PROCESSED_PACKAGES" | gzip -dc > processed-packages
  # Prevent reposado from downloading packages that have previously been
  # dumped.
  for f in `cat processed-packages`; do
      mkdir -p `dirname $f`
      touch $f
  done
fi

mkdir -p /opt/data-reposado/{html,metadata}
. venv/bin/activate
# First, just fetch all the update info.
repo_sync --no-download
# Next, fetch just the update packages we're interested in.
repo_sync `python list-packages.py`
# Now scrape symbols out of anything that was downloaded.
mkdir {symbols,artifacts}
python PackageSymbolDumper.py --tracking-file=/home/worker/processed-packages --dmg=/home/worker/bin/dmg --dump_syms=/home/worker/bin/dump_syms /opt/data-reposado/html/content/downloads /home/worker/symbols

# Hand out artifacts
gzip -c processed-packages > artifacts/processed-packages.gz

cd symbols
zip -r9 /home/worker/artifacts/target.crashreporter-symbols.zip *
