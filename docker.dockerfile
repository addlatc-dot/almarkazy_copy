FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Render uses PORT environment variable
CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "--bind", "0.0.0.0:${PORT:-5000}", "--timeout", "60", "app:app"]

FLASK_ENV=production
DATABASE_URL=mysql+pymysql://user:password@host/dbname
REDIS_URL=redis://user:password@host:port
SECRET_KEY=your_secure_random_key_here