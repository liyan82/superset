#!/bin/bash
set -e

# Install PostgreSQL client if not already installed
if ! command -v psql > /dev/null; then
  echo "Installing PostgreSQL client..."
  apt-get update && apt-get install -y postgresql-client
fi

# Use environment variables from the container, falling back to the
# docker-compose defaults. Override any of these in docker/.env-local.
DB_HOST=${DATABASE_HOST:-172.18.0.1}
DB_PORT=${DATABASE_PORT:-5432}
DB_USER=${DATABASE_USER:-superset}
DB_PASSWORD=${DATABASE_PASSWORD:?DATABASE_PASSWORD must be set}
DB_NAME=${DATABASE_DB:-superset}

# Export password for psql
export PGPASSWORD="$DB_PASSWORD"

echo "Checking connection to database at $DB_HOST:$DB_PORT..."

# Retry logic for database connection
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "Database connection successful!"
    break
  else
    echo "Cannot connect to database, retrying in 5 seconds..."
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
  fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "Could not connect to database after $MAX_RETRIES attempts, aborting"
  exit 1
fi

echo "Checking if Superset tables already exist..."

# Check if Superset tables already exist
TABLE_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ab_user')" 2>/dev/null | tr -d ' ')

if [ "$TABLE_EXISTS" = "t" ]; then
  echo "Superset tables already exist, skipping initialization"
  exit 0
else
  echo "Superset tables don't exist, proceeding with initialization"
  # Run the normal initialization script
  exec /app/docker/docker-init.sh
fi
