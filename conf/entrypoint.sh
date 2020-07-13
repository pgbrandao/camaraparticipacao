#!/bin/sh

# python manage.py flush --no-input
python manage.py migrate
mkdir -p static
python manage.py collectstatic --no-input --clear

exec "$@"
