FROM python:3.12-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

# collect static files (using default settings, no env vars needed)
RUN python manage.py collectstatic --noinput

# run migrations and start server
CMD python manage.py migrate && daphne -b 0.0.0.0 -p ${PORT:-8000} elearning_platform.asgi:application
