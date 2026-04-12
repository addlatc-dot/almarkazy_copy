# #!/bin/bash

# alembic upgrade head
# gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 main:app


#!/bin/bash
set -e  # يوقف لو حصل error

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
# gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 app:app

gunicorn --worker-class eventlet -w 2 --bind 0.0.0.0:${PORT:-8080} --timeout 600 app:app