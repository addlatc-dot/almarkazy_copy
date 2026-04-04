FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Railway will use Procfile if available, but Dockerfile CMD as fallback
CMD exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 main:app
