"""
Memory monitoring module.
"""

import psutil


def get_memory_info():
    """Get current memory usage information."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        'total': mem.total,
        'available': mem.available,
        'used': mem.used,
        'percent': mem.percent,
        'swap_total': swap.total,
        'swap_used': swap.used,
        'swap_percent': swap.percent
    }