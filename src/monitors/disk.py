"""
Disk monitoring module.
"""

import psutil


def get_disk_info():
    """Get disk usage information."""
    partitions = psutil.disk_partitions()
    disk_info = []

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            })
        except PermissionError:
            continue

    return disk_info