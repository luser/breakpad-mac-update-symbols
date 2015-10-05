#!/bin/sh
set -e

mkdir -p /opt/data-reposado/{html,metadata}
cd /
repo_sync
