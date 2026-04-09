#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Run migrations on every deploy.
# This is the correct workaround for Render Free plan,
# which does not support Pre-Deploy Commands or shell access.
python manage.py migrate --no-input

python manage.py collectstatic --no-input
