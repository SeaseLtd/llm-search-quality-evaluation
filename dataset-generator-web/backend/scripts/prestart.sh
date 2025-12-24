#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Alembic migrations are disabled - using SQLModel.metadata.create_all() instead
# Run migrations
# alembic upgrade head

# Create initial data in DB
python app/initial_data.py
