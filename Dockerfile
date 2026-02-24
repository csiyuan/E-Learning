FROM python:3.12-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

# collect static files (using default settings, no env vars needed)
RUN python manage.py collectstatic --noinput

# make start script executable and run it
RUN chmod +x start.sh
CMD ["./start.sh"]
