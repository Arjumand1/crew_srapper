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

# Copy project
COPY . .

# Create a script to run migrations and start the server
RUN echo '#!/bin/sh\n\
# Wait for the database to be ready\nif [ "$DATABASE" = "postgres" ]\nthen\n    echo "Waiting for PostgreSQL..."\n    while ! nc -z $DB_HOST $DB_PORT; do\n        sleep 0.1\n    done\n    echo "PostgreSQL is ready"\nfi\n\n# Run migrations and collect static files\npython manage.py migrate --noinput\npython manage.py collectstatic --noinput\n\n# Start the server\nexec "$@"' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Expose port for the Django app
EXPOSE 8000

# Command to run when container starts
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "crew_scraper.wsgi:application"]
