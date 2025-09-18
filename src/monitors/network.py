"""
Network monitoring module.
"""

import time
import socket
import psutil
import config


def get_network_info():
    """Get network interface information and statistics."""
    interfaces = []
    stats = psutil.net_io_counters(pernic=True)
    addrs = psutil.net_if_addrs()

    current_time = time.time()

    for interface, io_stats in stats.items():
        # Skip loopback interface
        if interface == 'lo' or interface.startswith('veth'):
            continue

        # Get IP addresses for this interface
        ip_addrs = []
        if interface in addrs:
            for addr in addrs[interface]:
                if addr.family == socket.AF_INET:  # IPv4
                    ip_addrs.append(addr.address)

        # Calculate bandwidth (bytes per second)
        bytes_sent_per_sec = 0
        bytes_recv_per_sec = 0

        if interface in config.NETWORK_STATS_CACHE:
            prev_stats = config.NETWORK_STATS_CACHE[interface]
            time_diff = current_time - prev_stats['time']

            if time_diff > 0:
                bytes_sent_per_sec = (io_stats.bytes_sent - prev_stats['bytes_sent']) / time_diff
                bytes_recv_per_sec = (io_stats.bytes_recv - prev_stats['bytes_recv']) / time_diff

        # Update cache
        config.NETWORK_STATS_CACHE[interface] = {
            'bytes_sent': io_stats.bytes_sent,
            'bytes_recv': io_stats.bytes_recv,
            'time': current_time
        }

        interfaces.append({
            'name': interface,
            'ip_addresses': ip_addrs,
            'bytes_sent': io_stats.bytes_sent,
            'bytes_recv': io_stats.bytes_recv,
            'packets_sent': io_stats.packets_sent,
            'packets_recv': io_stats.packets_recv,
            'bytes_sent_per_sec': max(0, bytes_sent_per_sec),  # Ensure non-negative
            'bytes_recv_per_sec': max(0, bytes_recv_per_sec),
            'errors_in': io_stats.errin,
            'errors_out': io_stats.errout,
            'drops_in': io_stats.dropin,
            'drops_out': io_stats.dropout
        })

    # Get connection statistics
    connections = psutil.net_connections(kind='inet')
    conn_stats = {
        'total': len(connections),
        'established': sum(1 for conn in connections if conn.status == 'ESTABLISHED'),
        'listen': sum(1 for conn in connections if conn.status == 'LISTEN'),
        'time_wait': sum(1 for conn in connections if conn.status == 'TIME_WAIT'),
        'close_wait': sum(1 for conn in connections if conn.status == 'CLOSE_WAIT')
    }

    return {
        'interfaces': interfaces,
        'connections': conn_stats
    }