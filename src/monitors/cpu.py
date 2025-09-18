"""
CPU monitoring module.
"""

import psutil


def get_cpu_info():
    """Get current CPU usage information."""
    cpu_percent = psutil.cpu_percent(interval=0.1, percpu=False)
    cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    cpu_freq = psutil.cpu_freq()

    return {
        'percent': cpu_percent,
        'percent_per_core': cpu_percent_per_core,
        'frequency_current': cpu_freq.current if cpu_freq else 0,
        'frequency_min': cpu_freq.min if cpu_freq else 0,
        'frequency_max': cpu_freq.max if cpu_freq else 0,
    }