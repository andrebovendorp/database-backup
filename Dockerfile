# Use Python 3.11 slim base image for smaller size
FROM python:3.14.0rc3-alpine3.21

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for database clients
RUN apk update; apk add --no-cache postgresql-client mongodb-tools

# Copy requirements first for better Docker layer caching
COPY . .

RUN pip install --no-cache-dir -r requirements.txt 

# Default command - run the backup system
CMD ["python", "main.py", "--help"]