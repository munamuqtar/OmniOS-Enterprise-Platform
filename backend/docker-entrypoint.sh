#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py seed_roles
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
  python manage.py create_admin --username "$ADMIN_USERNAME" --email "${ADMIN_EMAIL:-admin@example.com}" --password "$ADMIN_PASSWORD"
fi
exec "$@"
