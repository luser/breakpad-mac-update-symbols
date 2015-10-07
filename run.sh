#!/bin/sh
set -e

mkdir -p /opt/data-reposado/{html,metadata}
. venv/bin/activate
# First, just fetch all the update info.
repo_sync --no-download
# Next, fetch just the update packages we're interested in.
repo_sync `python list-packages.py`
# Now scrape symbols out of anything that was downloaded.
# TODO
