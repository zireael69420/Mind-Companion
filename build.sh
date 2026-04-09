#!/usr/bin/env bash
# build.sh — runs on every Render deploy
set -o errexit

pip install -r requirements.txt

# Apply any pending database migrations
python manage.py migrate --no-input

# Collect all static files (Django admin CSS/JS, app static files)
# into the STATIC_ROOT directory so WhiteNoise can serve them.
# This MUST run after migrate and after pip install.
python manage.py collectstatic --no-input --clear
