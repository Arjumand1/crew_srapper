FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create entrypoint script
RUN echo '#!/bin/bash\
set -e\
\
# Wait for the database to be ready\
if [ "$DATABASE" = "postgres" ]\
then\
    echo "Waiting for PostgreSQL..."\
    while ! nc -z "$DB_HOST" "$DB_PORT"; do\
        sleep 0.1\
    done\
    echo "PostgreSQL is ready"\
fi\
\
# Run migrations and collect static files\
python manage.py migrate --noinput\
python manage.py collectstatic --noinput\n\
# Start the server\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Copy project
COPY . .

# Expose port for the Django app
EXPOSE 8000

# Command to run when container starts
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "crew_scraper.wsgi:application"]
