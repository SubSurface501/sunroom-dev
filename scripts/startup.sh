#!/bin/bash

# Start the health check server in the background
python healthcheck_server.py &

# Start the Celery worker
PYTHONPATH=. celery -A agents.tasks worker -l info
