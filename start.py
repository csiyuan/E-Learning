#!/usr/bin/env python
"""Startup script for Railway deployment.
Uses Python to read PORT env var directly, avoiding shell expansion issues."""
import os
import subprocess
import sys

port = os.environ.get('PORT', '8000')
print(f"Starting EduStream on port {port}...")

# run migrations
print("Running migrations...")
subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)

# seed demo data
print("Seeding demo data...")
subprocess.run([sys.executable, 'manage.py', 'seed_data'], check=True)

# start daphne - replace this process with daphne
print(f"Launching Daphne on 0.0.0.0:{port}...")
os.execvp('daphne', ['daphne', '-b', '0.0.0.0', '-p', port, 'elearning_platform.asgi:application'])
