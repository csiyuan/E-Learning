#!/bin/sh
echo "Running migrations..."
python manage.py migrate
echo "Seeding demo data..."
python manage.py seed_data
echo "Starting Daphne on port $PORT..."
daphne -b 0.0.0.0 -p $PORT elearning_platform.asgi:application
