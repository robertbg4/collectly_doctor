#!/usr/bin/env bash

set -e

exec gunicorn --timeout 1800 -c gunicorn.conf.py app
