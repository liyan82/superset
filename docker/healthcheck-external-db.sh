#!/bin/sh
set -e

# Install PostgreSQL client if not already installed
if ! command -v psql > /dev/null; then
  echo "Installing PostgreSQL client..."
  apk update && apk add --no-cache postgresql-client
fi

# Use environment variables from the container
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=superset
DB_PASSWORD=yeef2FATH4tiff
DB_NAME=superset

# Export password for psql
export PGPASSWORD=yeef2FATH4tiff

echo "Checking connection to external database at $DB_HOST:$DB_PORT..."

# Check connection to external database
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
  echo "Cannot connect to external database"
  exit 1
fi

echo "Connection successful, checking if Superset tables exist..."

# Check if Superset tables already exist
TABLE_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ab_user')" 2>/dev/null | tr -d ' ')

if [ "$TABLE_EXISTS" = "t" ]; then
  echo "Superset tables already exist, initialization not needed"
  exit 0
else
  echo "Superset tables don't exist, initialization needed"
  exit 1
fi
