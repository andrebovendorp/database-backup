# Use Python 3.11 slim base image for smaller size
FROM python:3.14.1-alpine3.21

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for database clients
# - postgresql-client provides pg_dump/psql
# - mongodb-tools provides mongodump/mongorestore
# - mariadb-client provides mysql/mysqldump compatible binaries
RUN apk update; apk add --no-cache postgresql-client mongodb-tools mariadb-client

# MYSQL_PWD is consumed at runtime by the app when MySQL credentials are configured.
# Do not set secrets in the image; pass them through config/env at deploy time.

# smbprotocol is pure Python and is installed with the application dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command - run the backup system
CMD ["python", "main.py", "--help"]