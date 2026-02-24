FROM python:3.12-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

# collect static files
RUN python manage.py collectstatic --noinput

# use python startup script (avoids shell $PORT expansion issues)
CMD ["python", "start.py"]
