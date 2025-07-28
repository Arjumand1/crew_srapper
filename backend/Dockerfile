FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code into container
COPY . .

# Expose port for Django app
EXPOSE 8000

# Create entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint to manage DB readiness + migrations
ENTRYPOINT ["/entrypoint.sh"]

# Default command can be overridden by Compose or Render
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "crew_scraper.wsgi:application"]
