#!/usr/bin/env bash
# build.sh — runs on every Render deploy
# ORDER MATTERS:
#   1. pip install      — packages must exist before anything else runs
#   2. collectstatic    — builds the static file manifest BEFORE the app starts
#   3. migrate          — applies DB migrations after static files are ready
set -o errexit   # abort immediately if any command returns a non-zero exit code

pip install -r requirements.txt

# --clear deletes everything in STATIC_ROOT before collecting.
# This prevents stale files from a previous build remaining in the manifest,
# which is another cause of the CompressedManifestStaticFilesStorage 500 error.
python manage.py collectstatic --no-input --clear

python manage.py migrate --no-input
