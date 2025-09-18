"""
Operating system and static system information monitoring.
"""

import platform
import sys
import socket
import psutil
from datetime import datetime
import config


def get_static_system_info():
    """Get system information that doesn't change during runtime."""
    if not config.STATIC_SYSTEM_INFO:
        try:
            hostname = socket.gethostname()
        except:
            hostname = "Unknown"

        config.STATIC_SYSTEM_INFO = {
            'os': platform.system(),
            'os_version': platform.version(),
            'os_release': platform.release(),
            'architecture': platform.machine(),
            'processor': platform.processor() or "Unknown",
            'hostname': hostname,
            'python_version': sys.version.split()[0],
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
        }
    return config.STATIC_SYSTEM_INFO