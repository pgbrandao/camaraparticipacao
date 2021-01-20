#!/bin/sh

# python manage.py flush --no-input
python manage.py migrate
mkdir -p static
python manage.py collectstatic --no-input --clear --verbosity 0
python manage.py rebuild_cache

exec "$@"
