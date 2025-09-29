FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create required directories with proper permissions
RUN mkdir -p ScraperFunctions/data ScraperFunctions/downloaded_images ScraperFunctions/print_ready_images && \
    chmod -R 777 ScraperFunctions/data && \
    chmod -R 777 ScraperFunctions/downloaded_images

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "--log-level", "debug", "app:app"]