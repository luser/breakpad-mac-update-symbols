#!/bin/sh
set -e

cd /
repo_sync
./branch.py
repo_sync
