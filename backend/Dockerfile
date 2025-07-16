FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port for the Django app
EXPOSE 8000

# Command to run when container starts
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "crew_scraper.wsgi:application"]
