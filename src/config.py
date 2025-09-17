"""
Configuration and constants for the System Monitor Dashboard.
"""

import os
import tempfile
from pathlib import Path
from utils import find_free_port

# Port and host configuration
PORT_ENV = os.environ.get('FASTHTML_PORT', '0')
PORT = int(PORT_ENV) if PORT_ENV != '0' else find_free_port()
HOST = os.environ.get('FASTHTML_HOST', '127.0.0.1')

# Setup writable directory for session keys and other files
if os.environ.get('APPIMAGE'):
    WORK_DIR = Path(tempfile.mkdtemp(prefix='fasthtml-app-'))
    os.chdir(WORK_DIR)
else:
    WORK_DIR = Path.cwd()

# Maximum CPU cores to display in per-core view
MAX_CPU_CORES = 32

# Maximum processes to show in top lists
MAX_PROCESSES = 5

# Refresh intervals configuration (in seconds)
REFRESH_INTERVALS = {
    'cpu': 2,
    'memory': 2,
    'disk': 10,
    'network': 2,
    'process': 5,
    'gpu': 3,
    'temperature': 5
}

# Track last update times for each component
LAST_UPDATE_TIMES = {
    'cpu': 0,
    'memory': 0,
    'disk': 0,
    'network': 0,
    'process': 0,
    'gpu': 0,
    'temperature': 0
}

# Cache for system info that doesn't change
STATIC_SYSTEM_INFO = {}

# Network monitoring state for bandwidth calculation
NETWORK_STATS_CACHE = {}

# SSE Configuration
SSE_CONFIG = {
    'max_queue_size': 100,
    'history_size': 50,
    'default_timeout': 0.1
}