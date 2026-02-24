FROM python:3.12-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

# collect static files (using default settings, no env vars needed)
RUN python manage.py collectstatic --noinput

# run migrations, seed demo data, and start server
CMD sh -c "python manage.py migrate && python manage.py seed_data && daphne -b 0.0.0.0 -p \$PORT elearning_platform.asgi:application"
