"""
Gunicorn configuration file for production deployment.

This file provides advanced configuration options for Gunicorn.
You can use this file by adding `--config gunicorn_config.py` to your gunicorn command.

For more information, see: https://docs.gunicorn.org/en/stable/settings.html
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
# Formula: (2 × CPU cores) + 1
# For production, you can override this with GUNICORN_WORKERS environment variable
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"  # Options: sync, gevent, eventlet, tornado, gthread
worker_connections = 1000  # For async workers (gevent, eventlet)
timeout = 120  # Seconds before a worker is killed and restarted
keepalive = 5  # Seconds to wait for requests on Keep-Alive connections

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50  # Randomize max_requests to prevent all workers restarting at once

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info").lower()

# Process naming
proc_name = "SVEX_Project"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None  # Set in Dockerfile with USER app
group = None

# SSL (if needed directly, though nginx handles this for us)
# keyfile = None
# certfile = None

# Performance tuning
worker_tmp_dir = "/dev/shm"  # Use shared memory for faster worker restarts (Linux only)

# Graceful timeout
graceful_timeout = 30  # Time to wait for workers to finish requests before killing them

