"""
Process monitoring module.
"""

import psutil
from config import MAX_PROCESSES


def get_process_info(top_n=MAX_PROCESSES):
    """Get top processes by CPU and memory usage."""
    processes = []

    # Get all processes with their info
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'username', 'status']):
        try:
            pinfo = proc.info
            # Skip kernel threads and processes with 0% CPU and memory
            if pinfo['cpu_percent'] is not None and (pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 0):
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'][:30],  # Truncate long names
                    'cpu_percent': pinfo['cpu_percent'] or 0,
                    'memory_percent': pinfo['memory_percent'] or 0,
                    'memory_mb': pinfo['memory_info'].rss / (1024 * 1024) if pinfo['memory_info'] else 0,
                    'username': pinfo['username'][:15] if pinfo['username'] else 'N/A',
                    'status': pinfo['status'] if pinfo['status'] else 'unknown'
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort by CPU usage and get top N
    top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:top_n]

    # Sort by memory usage and get top N
    top_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:top_n]

    # Get total process count
    total_processes = len(processes)

    # Get process status counts
    status_counts = {}
    for proc in processes:
        status = proc['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        'top_cpu': top_cpu,
        'top_memory': top_memory,
        'total': total_processes,
        'status_counts': status_counts
    }