#!/usr/bin/env python3
"""
System Information and Resource Monitoring Dashboard with real-time updates via SSE.
"""

from fasthtml.common import *
from fasthtml.common import sse_message
import os
import sys
import subprocess
import platform
import socket
import webbrowser
from contextlib import closing
from datetime import datetime
import tempfile
from pathlib import Path
import asyncio
import json
import threading
import time
import psutil

# SSE imports
from cjm_fasthtml_sse.core import SSEBroadcastManager
from cjm_fasthtml_sse.helpers import (
    oob_swap,
    oob_element,
    oob_update,
    insert_htmx_sse_ext
)
from cjm_fasthtml_sse.htmx import HTMXSSEConnector

# DaisyUI imports
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes, btn_styles, btn_modifiers
from cjm_fasthtml_daisyui.components.actions.modal import modal, modal_box, modal_action, modal_backdrop
from cjm_fasthtml_daisyui.components.data_display.card import card, card_body, card_title, card_actions
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.stat import stat, stat_title, stat_value, stat_desc, stats, stats_direction
from cjm_fasthtml_daisyui.components.data_display.status import status, status_colors, status_sizes
from cjm_fasthtml_daisyui.components.data_display.table import table, table_modifiers, table_sizes
from cjm_fasthtml_daisyui.components.data_input.range_slider import range_dui, range_colors, range_sizes
from cjm_fasthtml_daisyui.components.data_input.label import label
from cjm_fasthtml_daisyui.components.navigation.tabs import tabs, tab, tab_modifiers, tabs_styles
from cjm_fasthtml_daisyui.components.feedback.progress import progress, progress_colors
from cjm_fasthtml_daisyui.components.feedback.alert import alert, alert_colors
from cjm_fasthtml_daisyui.components.navigation.navbar import navbar, navbar_start, navbar_center, navbar_end
from cjm_fasthtml_daisyui.components.layout.divider import divider
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui, border_dui
from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
from cjm_fasthtml_daisyui.core.testing import create_theme_selector

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.spacing import p, m, space
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import flex_display, gap, grid_cols, items, justify, grid_display, flex
from cjm_fasthtml_tailwind.utilities.sizing import w, h, max_w, min_h, min_w
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, text_align, font_family, break_all, leading
from cjm_fasthtml_tailwind.utilities.borders import rounded, border, border_color
from cjm_fasthtml_tailwind.utilities.effects import shadow
from cjm_fasthtml_tailwind.utilities.layout import position, right, top
from cjm_fasthtml_tailwind.core.base import combine_classes

# Find an available port
def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

# Get port from environment or find a free one
PORT_ENV = os.environ.get('FASTHTML_PORT', '0')
PORT = int(PORT_ENV) if PORT_ENV != '0' else find_free_port()
HOST = os.environ.get('FASTHTML_HOST', '127.0.0.1')

# Setup writable directory for session keys and other files
if os.environ.get('APPIMAGE'):
    WORK_DIR = Path(tempfile.mkdtemp(prefix='fasthtml-app-'))
    os.chdir(WORK_DIR)
else:
    WORK_DIR = Path.cwd()

# Initialize SSE Broadcast Manager
sse_manager = SSEBroadcastManager(
    max_queue_size=100,
    history_size=50,
    default_timeout=0.1
)

# Initialize HTMX SSE Connector
htmx_sse_connector = HTMXSSEConnector()

# Create the FastHTML app with DaisyUI headers
app, rt = fast_app(
    pico=False,
    hdrs=[*get_daisyui_headers()],
    title="System Monitor Dashboard"
)

# Insert HTMX SSE extension
insert_htmx_sse_ext(app.hdrs)

MAX_CPU_CORES = 32

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

def get_static_system_info():
    """Get system information that doesn't change during runtime."""
    global STATIC_SYSTEM_INFO
    if not STATIC_SYSTEM_INFO:
        try:
            import socket
            hostname = socket.gethostname()
        except:
            hostname = "Unknown"

        STATIC_SYSTEM_INFO = {
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
    return STATIC_SYSTEM_INFO

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

# Network monitoring state for bandwidth calculation
NETWORK_STATS_CACHE = {}

def get_network_info():
    """Get network interface information and statistics."""
    global NETWORK_STATS_CACHE

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

        if interface in NETWORK_STATS_CACHE:
            prev_stats = NETWORK_STATS_CACHE[interface]
            time_diff = current_time - prev_stats['time']

            if time_diff > 0:
                bytes_sent_per_sec = (io_stats.bytes_sent - prev_stats['bytes_sent']) / time_diff
                bytes_recv_per_sec = (io_stats.bytes_recv - prev_stats['bytes_recv']) / time_diff

        # Update cache
        NETWORK_STATS_CACHE[interface] = {
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

def format_bandwidth(bytes_per_sec):
    """Format bandwidth to human readable string."""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 * 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"

def get_process_info(top_n=5):
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

def check_gpu():
    """Check for GPU availability and get info using nvitop."""
    gpu_info = {'available': False, 'type': 'None', 'details': {}, 'processes': []}

    try:
        import nvitop
        from nvitop import Device, GpuProcess, NA

        devices = Device.all()  # Get all NVIDIA devices
        if devices:
            gpu_info['available'] = True
            gpu_info['type'] = 'NVIDIA'

            for i, device in enumerate(devices):
                # Get memory in MB for consistency, with NA checks
                mem_total = device.memory_total()
                mem_used = device.memory_used()
                mem_free = device.memory_free()

                memory_total_mb = mem_total // (1024 * 1024) if mem_total and mem_total != NA else 0
                memory_used_mb = mem_used // (1024 * 1024) if mem_used and mem_used != NA else 0
                memory_free_mb = mem_free // (1024 * 1024) if mem_free and mem_free != NA else 0

                # Get power values and convert from milliwatts to watts
                power_usage_mw = device.power_usage()
                power_limit_mw = device.power_limit()
                power_usage_w = power_usage_mw / 1000.0 if power_usage_mw and power_usage_mw != NA else None
                power_limit_w = power_limit_mw / 1000.0 if power_limit_mw and power_limit_mw != NA else None

                # Get other metrics with NA checks
                gpu_util = device.gpu_utilization()
                temp = device.temperature()
                fan = device.fan_speed()
                enc_util = device.encoder_utilization()
                dec_util = device.decoder_utilization()

                gpu_info['details'][f'gpu_{i}'] = {
                    'name': device.name(),
                    'memory_total': memory_total_mb,
                    'memory_used': memory_used_mb,
                    'memory_free': memory_free_mb,
                    'utilization': gpu_util if gpu_util != NA else 0,
                    'temperature': temp if temp != NA else None,
                    'power_usage': power_usage_w,  # Now in watts
                    'power_limit': power_limit_w,  # Now in watts
                    'fan_speed': fan if fan != NA else None,
                    'compute_processes': len(device.processes()),
                    'encoder_utilization': enc_util if enc_util != NA else 0,
                    'decoder_utilization': dec_util if dec_util != NA else 0,
                }

                # Get process information for this GPU
                processes = device.processes()
                if processes:
                    try:
                        # Take snapshots of processes for detailed info
                        process_snapshots = GpuProcess.take_snapshots(processes.values(), failsafe=True)
                        for snapshot in process_snapshots:
                            # In snapshots, gpu_memory() is still a method according to the docs
                            # But let's try accessing it as a property first, then as a method
                            try:
                                # Try as a method first (according to docs)
                                gpu_mem = snapshot.gpu_memory() if callable(getattr(snapshot, 'gpu_memory', None)) else snapshot.gpu_memory
                            except:
                                # Fallback to property access
                                gpu_mem = getattr(snapshot, 'gpu_memory', NA)

                            gpu_memory_mb = gpu_mem // (1024 * 1024) if gpu_mem and gpu_mem != NA else 0

                            # Get the process name - try different attributes
                            proc_name = None
                            if hasattr(snapshot, 'name') and callable(snapshot.name):
                                try:
                                    proc_name = snapshot.name()
                                except:
                                    pass
                            if not proc_name and hasattr(snapshot, 'command'):
                                proc_name = snapshot.command
                            if not proc_name and hasattr(snapshot, 'username'):
                                proc_name = f"{snapshot.username} (PID {snapshot.pid})"
                            if not proc_name:
                                proc_name = f"PID {snapshot.pid}"

                            if proc_name and len(str(proc_name)) > 50:
                                proc_name = str(proc_name)[:47] + "..."

                            gpu_info['processes'].append({
                                'pid': snapshot.pid,  # pid is a property on snapshot
                                'name': str(proc_name),
                                'gpu_memory_mb': gpu_memory_mb,
                                'gpu_utilization': getattr(snapshot, 'gpu_sm_utilization', 0) if getattr(snapshot, 'gpu_sm_utilization', 0) != NA else 0,
                                'device_id': i,
                                'device_name': device.name()
                            })
                    except Exception as e:
                        print(f"Error processing GPU processes: {e}, type: {type(e).__name__}, details: {str(e)}")

    except ImportError:
        # nvitop not available, fallback to nvidia-smi
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,power.limit',
                                   '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        gpu_info['available'] = True
                        gpu_info['type'] = 'NVIDIA'
                        gpu_info['details'][f'gpu_{i}'] = {
                            'name': parts[0],
                            'memory_total': int(float(parts[1])) if parts[1] and parts[1] != 'N/A' else 0,
                            'memory_used': int(float(parts[2])) if parts[2] and parts[2] != 'N/A' else 0,
                            'memory_free': int(float(parts[3])) if parts[3] and parts[3] != 'N/A' else 0,
                            'utilization': int(float(parts[4])) if parts[4] and parts[4] != 'N/A' else 0,
                            'temperature': float(parts[5]) if len(parts) > 5 and parts[5] and parts[5] != 'N/A' else None,
                            'power_usage': float(parts[6]) if len(parts) > 6 and parts[6] and parts[6] != 'N/A' else None,  # nvidia-smi returns watts directly
                            'power_limit': float(parts[7]) if len(parts) > 7 and parts[7] and parts[7] != 'N/A' else None,  # nvidia-smi returns watts directly
                        }
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
    except Exception as e:
        print(f"Error checking GPU: {e}")

    return gpu_info

def get_temperature_info():
    """Get temperature sensor information."""
    temps = []

    try:
        # Get temperature sensors using psutil
        if hasattr(psutil, 'sensors_temperatures'):
            temp_sensors = psutil.sensors_temperatures()

            # Process each sensor type
            for sensor_type, sensors in temp_sensors.items():
                for sensor in sensors:
                    # Filter out sensors with invalid readings
                    if sensor.current is not None and sensor.current > 0:
                        temp_info = {
                            'type': sensor_type,
                            'label': sensor.label or sensor_type,
                            'current': sensor.current,
                            'high': sensor.high,
                            'critical': sensor.critical
                        }
                        temps.append(temp_info)
    except Exception as e:
        print(f"Error getting temperature sensors: {e}")

    # If psutil doesn't provide temps, try alternative methods
    if not temps:
        # Try reading from thermal zones (Linux)
        try:
            import glob
            thermal_zones = glob.glob('/sys/class/thermal/thermal_zone*/temp')
            for i, zone_path in enumerate(thermal_zones):
                try:
                    with open(zone_path, 'r') as f:
                        temp_millidegree = int(f.read().strip())
                        temp_celsius = temp_millidegree / 1000.0

                        # Try to get the type
                        type_path = zone_path.replace('/temp', '/type')
                        sensor_type = f"thermal_zone{i}"
                        try:
                            with open(type_path, 'r') as f:
                                sensor_type = f.read().strip()
                        except:
                            pass

                        temps.append({
                            'type': 'thermal',
                            'label': sensor_type,
                            'current': temp_celsius,
                            'high': 85.0,  # Default high threshold
                            'critical': 95.0  # Default critical threshold
                        })
                except Exception:
                    continue
        except Exception:
            pass

    # Try to get NVIDIA GPU temperature (only if nvitop isn't available)
    try:
        import nvitop
        # If nvitop is available, GPU temps are handled in check_gpu()
        # so we skip adding them here to avoid duplication
    except ImportError:
        # nvitop not available, try nvidia-smi
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                gpu_temps = result.stdout.strip().split('\n')
                for i, temp in enumerate(gpu_temps):
                    if temp:
                        temps.append({
                            'type': 'gpu',
                            'label': f'NVIDIA GPU {i}',
                            'current': float(temp),
                            'high': 80.0,
                            'critical': 90.0
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

    return temps

def format_bytes(bytes_value):
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def format_uptime(boot_time_str):
    """Format uptime from boot time string."""
    boot_time = datetime.strptime(boot_time_str, '%Y-%m-%d %H:%M:%S')
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def get_progress_color(percent):
    """Get progress bar color based on percentage."""
    if percent < 50:
        return progress_colors.success
    elif percent < 80:
        return progress_colors.warning
    else:
        return progress_colors.error

def get_temperature_color(temp_celsius, high=85, critical=95):
    """Get color for temperature display."""
    if temp_celsius < 50:
        return text_dui.success
    elif temp_celsius < 70:
        return text_dui.primary
    elif temp_celsius < high:
        return text_dui.warning
    else:
        return text_dui.error

def get_temperature_badge_color(temp_celsius, high=85, critical=95):
    """Get badge color for temperature."""
    if temp_celsius < 50:
        return badge_colors.success
    elif temp_celsius < 70:
        return badge_colors.primary
    elif temp_celsius < high:
        return badge_colors.warning
    else:
        return badge_colors.error

def render_stat_card(title_text, value_text, desc_text=None, value_color=None):
    """Render a stat card with consistent styling."""
    value_classes = [stat_value]
    if value_color:
        value_classes.append(value_color)

    return Div(
        Div(title_text, cls=combine_classes(stat_title, text_dui.base_content.opacity(70))),
        Div(value_text, cls=combine_classes(*value_classes)),
        Div(desc_text, cls=str(stat_desc)) if desc_text else None,
        cls=str(stat)
    )

def render_progress_bar(value, max_value=100, label=None):
    """Render a progress bar with label."""
    color = get_progress_color(value)

    return Div(
        Div(
            Span(label or f"{value:.1f}%", cls=combine_classes(font_size.xs, text_dui.base_content)),
            Span(f"{value:.1f}%", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60))),
            cls=combine_classes(flex_display, justify.between, m.b(1))
        ) if label else None,
        Progress(
            value=str(value),
            max=str(max_value),
            cls=combine_classes(progress, color, w.full)
        )
    )

def render_os_info_card():
    """Render the OS information card."""
    info = get_static_system_info()

    return Div(
        Div(
            H3("Operating System", cls=combine_classes(card_title, text_dui.base_content)),
            cls=str(m.b(4))
        ),
        Div(
            render_stat_card("System", f"{info['os']} {info['os_release']}", info['architecture']),
            render_stat_card("Hostname", info['hostname'], f"Python {info['python_version']}"),
            render_stat_card("Boot Time", info['boot_time'], f"Uptime: {format_uptime(info['boot_time'])}"),
            render_stat_card("CPU Cores", f"{info['cpu_count']} Physical", f"{info['cpu_count_logical']} Logical"),
            cls=combine_classes(stats, stats_direction.vertical.lg, bg_dui.base_200, rounded.lg, p(4))
        ),
        cls=str(card_body)
    )

def render_cpu_card(cpu_info):
    """Render the CPU usage card."""
    return Div(
        Div(
            H3("CPU Usage", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                f"{cpu_info['percent']:.1f}%",
                cls=combine_classes(
                    badge,
                    badge_colors.primary if cpu_info['percent'] < 80 else badge_colors.error,
                    badge_sizes.lg
                )
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        # Overall CPU usage
        Div(
            render_progress_bar(cpu_info['percent'], label="Overall Usage"),
            cls=str(m.b(4))
        ),

        # CPU Frequency
        Div(
            P("CPU Frequency", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            Div(
                Span(f"Current: {cpu_info['frequency_current']:.0f} MHz",
                     cls=combine_classes(text_dui.primary, font_size.sm)),
                Span(f"Min: {cpu_info['frequency_min']:.0f} MHz",
                     cls=combine_classes(text_dui.base_content.opacity(60), font_size.xs)),
                Span(f"Max: {cpu_info['frequency_max']:.0f} MHz",
                     cls=combine_classes(text_dui.base_content.opacity(60), font_size.xs)),
                cls=combine_classes(flex_display, justify.between, gap(2))
            ),
            cls=str(m.b(4))
        ),

        # Per-core usage (if not too many cores)
        Div(
            P("Per Core Usage", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            Div(
                *[render_progress_bar(percent, label=f"Core {i}")
                  for i, percent in enumerate(cpu_info['percent_per_core'][:MAX_CPU_CORES])],
                cls=str(space.y(2))
            ),
            cls=str(m.t(2))
        ) if len(cpu_info['percent_per_core']) <= MAX_CPU_CORES else None,

        cls=str(card_body),
        id="cpu-card-body"
    )

def render_memory_card(mem_info):
    """Render the memory usage card."""
    return Div(
        Div(
            H3("Memory Usage", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                f"{mem_info['percent']:.1f}%",
                cls=combine_classes(
                    badge,
                    badge_colors.primary if mem_info['percent'] < 80 else badge_colors.error,
                    badge_sizes.lg
                )
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        # RAM Usage
        Div(
            P("RAM", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            render_progress_bar(mem_info['percent'],
                              label=f"{format_bytes(mem_info['used'])} / {format_bytes(mem_info['total'])}"),
            P(f"Available: {format_bytes(mem_info['available'])}",
              cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60), m.t(1))),
            cls=str(m.b(4))
        ),

        # Swap Usage
        Div(
            P("Swap", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            render_progress_bar(mem_info['swap_percent'],
                              label=f"{format_bytes(mem_info['swap_used'])} / {format_bytes(mem_info['swap_total'])}"),
            cls=str(m.t(4))
        ) if mem_info['swap_total'] > 0 else None,

        cls=str(card_body),
        id="memory-card-body"
    )

def render_disk_card(disk_info):
    """Render the disk usage card."""
    return Div(
        Div(
            H3("Disk Usage", cls=combine_classes(card_title, text_dui.base_content)),
            cls=str(m.b(4))
        ),

        Div(
            *[Div(
                Div(
                    P(disk['device'], cls=combine_classes(font_size.sm, font_weight.medium)),
                    P(f"{disk['mountpoint']} ({disk['fstype']})",
                      cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60))),
                    cls=str(m.b(2))
                ),
                render_progress_bar(disk['percent'],
                                  label=f"{format_bytes(disk['used'])} / {format_bytes(disk['total'])}"),
                P(f"Free: {format_bytes(disk['free'])}",
                  cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60), m.t(1))),
                cls=combine_classes(p(3), bg_dui.base_200, rounded.lg, m.b(3))
            ) for disk in disk_info[:5]],  # Limit to 5 disks for UI clarity
            cls=""
        ),

        cls=str(card_body),
        id="disk-card-body"
    )

def render_network_card(net_info):
    """Render the network monitoring card."""
    interfaces = net_info['interfaces']
    connections = net_info['connections']

    if not interfaces:
        return Div(
            Div(
                H3("Network", cls=combine_classes(card_title, text_dui.base_content)),
                cls=str(m.b(4))
            ),
            Div(
                "No active network interfaces detected",
                cls=combine_classes(alert, alert_colors.info)
            ),
            cls=str(card_body)
        )

    return Div(
        Div(
            H3("Network", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                f"{len(interfaces)} Active",
                cls=combine_classes(badge, badge_colors.info, badge_sizes.lg)
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        # Network interfaces
        Div(
            *[Div(
                # Interface header
                Div(
                    P(interface['name'], cls=combine_classes(font_size.sm, font_weight.medium)),
                    P(', '.join(interface['ip_addresses']) if interface['ip_addresses'] else 'No IP',
                      cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60))),
                    cls=str(m.b(2))
                ),

                # Bandwidth meters
                Div(
                    # Upload speed
                    Label(
                        Label(
                            Span("↑ Upload", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                            Span(format_bandwidth(interface['bytes_sent_per_sec']),
                                 cls=combine_classes(font_size.xs, text_dui.info, font_weight.medium)),
                            cls=combine_classes(flex_display, justify.between)
                        ),
                        Progress(
                            value=str(min(100, interface['bytes_sent_per_sec'] / 1024 / 1024 * 10)),  # Scale to MB/s
                            max="100",
                            cls=combine_classes(progress, progress_colors.info, w.full, h(1))
                        ),
                        cls=str(m.b(2))
                    ),

                    # Download speed
                    Label(
                        Label(
                            Span("↓ Download", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                            Span(format_bandwidth(interface['bytes_recv_per_sec']),
                                 cls=combine_classes(font_size.xs, text_dui.success, font_weight.medium)),
                            cls=combine_classes(flex_display, justify.between)
                        ),
                        Progress(
                            value=str(min(100, interface['bytes_recv_per_sec'] / 1024 / 1024 * 10)),  # Scale to MB/s
                            max="100",
                            cls=combine_classes(progress, progress_colors.success, w.full, h(1))
                        ),
                        cls=str(m.b(2))
                    ),

                    # Statistics
                    Label(
                        Span(f"Total: ↑{format_bytes(interface['bytes_sent'])} ↓{format_bytes(interface['bytes_recv'])}",
                             cls=combine_classes(font_size.xs, text_dui.base_content.opacity(50))),
                        cls=str(m.t(1))
                    ),
                ),

                cls=combine_classes(p(3), bg_dui.base_200, rounded.lg, m.b(3))
            ) for interface in interfaces[:3]],  # Limit to 3 interfaces for UI clarity
            cls=""
        ),

        # Connection statistics
        Div(
            P("Connections", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            Div(
                render_stat_card("Total", str(connections['total'])),
                render_stat_card("Established", str(connections['established'])),
                render_stat_card("Listening", str(connections['listen'])),
                render_stat_card("Time Wait", str(connections['time_wait'])),
                cls=combine_classes(stats, bg_dui.base_200, rounded.lg, p(2), font_size.xs)
            ),
            cls=str(m.t(3))
        ),

        cls=str(card_body),
        id="network-card-body"
    )

def render_process_card(proc_info):
    """Render the process monitoring card."""
    return Div(
        # Header with process count
        Div(
            H3("Process Monitor", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                f"{proc_info['total']} processes",
                cls=combine_classes(badge, badge_colors.primary, badge_sizes.lg)
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        # Process status summary
        Div(
            *[Span(
                f"{status}: {count}",
                cls=combine_classes(
                    badge,
                    badge_colors.info if status == 'running' else badge_colors.neutral,
                    badge_sizes.sm,
                    m.r(2)
                )
            ) for status, count in proc_info['status_counts'].items()],
            cls=combine_classes(flex_display, flex.wrap, gap(1), m.b(4))
        ),

        # Tabs for CPU vs Memory view
        Div(
            # Tab buttons
            Div(
                Button("Top CPU",
                       cls=combine_classes(tab, tab_modifiers.active),
                       id="cpu-tab",
                       onclick="document.getElementById('cpu-processes').style.display='block'; document.getElementById('memory-processes').style.display='none'; this.classList.add('tab-active'); document.getElementById('mem-tab').classList.remove('tab-active')"),
                Button("Top Memory",
                       cls=str(tab),
                       id="mem-tab",
                       onclick="document.getElementById('memory-processes').style.display='block'; document.getElementById('cpu-processes').style.display='none'; this.classList.add('tab-active'); document.getElementById('cpu-tab').classList.remove('tab-active')"),
                role="tablist",
                cls=combine_classes(tabs, tabs_styles.box)
            ),
            cls=str(m.b(4))
        ),

        # Top CPU processes table
        Div(
            Table(
                Thead(
                    Tr(
                        Th("PID", cls=combine_classes(font_size.xs, w(16))),
                        Th("Name", cls=str(font_size.xs)),
                        Th("CPU %", cls=combine_classes(font_size.xs, w(20))),
                        Th("Memory", cls=combine_classes(font_size.xs, w(24))),
                        Th("User", cls=str(font_size.xs))
                    )
                ),
                Tbody(
                    *[Tr(
                        Td(str(proc['pid']), cls=str(font_size.xs)),
                        Td(
                            proc['name'],
                            cls=combine_classes(font_size.xs, font_weight.medium)
                        ),
                        Td(
                            Label(
                                f"{proc['cpu_percent']:.1f}%",
                                cls=combine_classes(
                                    badge,
                                    badge_colors.error if proc['cpu_percent'] > 50 else
                                    badge_colors.warning if proc['cpu_percent'] > 25 else
                                    badge_colors.info,
                                    badge_sizes.sm
                                )
                            )
                        ),
                        Td(f"{proc['memory_mb']:.0f} MB", cls=str(font_size.xs)),
                        Td(proc['username'], cls=str(font_size.xs))
                    ) for proc in proc_info['top_cpu']],
                ),
                cls=combine_classes(table, table_modifiers.zebra, table_sizes.xs, w.full)
            ),
            id="cpu-processes",
            style="display: block;"
        ),

        # Top Memory processes table
        Div(
            Table(
                Thead(
                    Tr(
                        Th("PID", cls=combine_classes(font_size.xs, w(16))),
                        Th("Name", cls=str(font_size.xs)),
                        Th("Memory %", cls=combine_classes(font_size.xs, w(20))),
                        Th("Memory", cls=combine_classes(font_size.xs, w(24))),
                        Th("User", cls=str(font_size.xs))
                    )
                ),
                Tbody(
                    *[Tr(
                        Td(str(proc['pid']), cls=str(font_size.xs)),
                        Td(
                            proc['name'],
                            cls=combine_classes(font_size.xs, font_weight.medium)
                        ),
                        Td(
                            Label(
                                f"{proc['memory_percent']:.1f}%",
                                cls=combine_classes(
                                    badge,
                                    badge_colors.error if proc['memory_percent'] > 50 else
                                    badge_colors.warning if proc['memory_percent'] > 25 else
                                    badge_colors.info,
                                    badge_sizes.sm
                                )
                            )
                        ),
                        Td(f"{proc['memory_mb']:.0f} MB", cls=str(font_size.xs)),
                        Td(proc['username'], cls=str(font_size.xs))
                    ) for proc in proc_info['top_memory']],
                ),
                cls=combine_classes(table, table_modifiers.zebra, table_sizes.xs, w.full)
            ),
            id="memory-processes",
            style="display: none;"
        ),

        cls=str(card_body),
        id="process-card-body"
    )

def render_gpu_card(gpu_info):
    """Render the GPU information card."""
    if not gpu_info['available']:
        return Div(
            Div(
                H3("GPU Information", cls=combine_classes(card_title, text_dui.base_content)),
                cls=str(m.b(4))
            ),
            Div(
                "No GPU detected or GPU monitoring not available",
                cls=combine_classes(alert, alert_colors.info)
            ),
            cls=str(card_body)
        )

    return Div(
        Div(
            H3("GPU Information", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                gpu_info['type'],
                cls=combine_classes(badge, badge_colors.success, badge_sizes.lg)
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        Div(
            *[Div(
                P(details['name'], cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),

                # Main metrics in grid
                Div(
                    # GPU Utilization
                    Label(
                        P("GPU Utilization", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                        render_progress_bar(details['utilization']),
                        cls=str(m.b(3))
                    ),

                    # GPU Memory
                    Label(
                        P("Memory", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                        render_progress_bar(
                            (details['memory_used'] / details['memory_total']) * 100 if details['memory_total'] > 0 else 0,
                            label=f"{details['memory_used']} MB / {details['memory_total']} MB"
                        ),
                        cls=str(m.b(3))
                    ),

                    # Temperature (if available)
                    Label(
                        P("Temperature", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                        Label(
                            Span(
                                f"{details.get('temperature', 'N/A')}°C" if details.get('temperature') else "N/A",
                                cls=combine_classes(
                                    font_weight.medium,
                                    get_temperature_color(details.get('temperature', 0), 80, 90) if details.get('temperature') else text_dui.base_content
                                )
                            ),
                            cls=str(m.t(1))
                        ),
                        cls=str(m.b(3))
                    ) if details.get('temperature') is not None else None,

                    # Power Usage (if available)
                    Label(
                        P("Power", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                        Label(
                            Span(
                                f"{details.get('power_usage', 0):.1f}W / {details.get('power_limit', 0):.1f}W"
                                if details.get('power_usage') is not None else "N/A",
                                cls=combine_classes(font_size.sm, text_dui.base_content)
                            ),
                            render_progress_bar(
                                (details.get('power_usage', 0) / details.get('power_limit', 1)) * 100
                                if details.get('power_limit') and details.get('power_limit') > 0 else 0,
                                label=None
                            ) if details.get('power_usage') is not None and details.get('power_limit') else None,
                            cls=""
                        ),
                        cls=str(m.b(3))
                    ) if details.get('power_usage') is not None else None,

                    # Additional metrics in a row
                    Label(
                        # Fan Speed
                        Span(
                            f"Fan: {details.get('fan_speed', 'N/A')}%" if details.get('fan_speed') is not None else "",
                            cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60))
                        ) if details.get('fan_speed') is not None else None,

                        # Encoder/Decoder utilization
                        Span(
                            f"Enc: {details.get('encoder_utilization', 0)}%",
                            cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60), m.l(3))
                        ) if details.get('encoder_utilization') is not None else None,

                        Span(
                            f"Dec: {details.get('decoder_utilization', 0)}%",
                            cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60), m.l(3))
                        ) if details.get('decoder_utilization') is not None else None,

                        # Process count
                        Span(
                            f"Processes: {details.get('compute_processes', 0)}",
                            cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60), m.l(3))
                        ) if details.get('compute_processes') is not None else None,

                        cls=combine_classes(flex_display, items.center)
                    ) if any([details.get('fan_speed'), details.get('encoder_utilization'),
                             details.get('decoder_utilization'), details.get('compute_processes')]) else None,

                    cls=""
                ),

                cls=combine_classes(p(3), bg_dui.base_200, rounded.lg, m.b(3))
            ) for gpu_id, details in gpu_info['details'].items()],
            cls=""
        ),

        # GPU Processes section (if any)
        Div(
            Div(cls=combine_classes(divider, m.y(3))),
            P("GPU Processes", cls=combine_classes(font_size.sm, font_weight.semibold, m.b(3), text_dui.base_content)),

            # Process table
            Div(
                Table(
                    Thead(
                        Tr(
                            Th("PID", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content.opacity(70))),
                            Th("Process", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content.opacity(70))),
                            Th("GPU Memory", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content.opacity(70))),
                            Th("GPU Usage", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content.opacity(70))),
                            Th("Device", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content.opacity(70))),
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(str(proc['pid']), cls=combine_classes(font_size.xs, text_dui.base_content.opacity(80))),
                            Td(
                                proc['name'][:40] + "..." if len(proc['name']) > 40 else proc['name'],
                                cls=combine_classes(font_size.xs, font_weight.medium)
                            ),
                            Td(
                                Span(
                                    f"{proc['gpu_memory_mb']} MB",
                                    cls=combine_classes(
                                        badge,
                                        badge_colors.primary if proc['gpu_memory_mb'] < 4096 else badge_colors.warning if proc['gpu_memory_mb'] < 8192 else badge_colors.error,
                                        badge_sizes.xs
                                    )
                                ),
                                cls=""
                            ),
                            Td(
                                f"{proc.get('gpu_utilization', 0)}%",
                                cls=combine_classes(
                                    font_size.xs,
                                    text_dui.success if proc.get('gpu_utilization', 0) < 50 else text_dui.warning if proc.get('gpu_utilization', 0) < 80 else text_dui.error
                                )
                            ),
                            Td(
                                f"GPU {proc['device_id']}",
                                cls=combine_classes(font_size.xs, text_dui.base_content.opacity(60))
                            ),
                        ) for proc in sorted(gpu_info.get('processes', []), key=lambda x: x['gpu_memory_mb'], reverse=True)[:10]],  # Show top 10
                        cls=""
                    ),
                    cls=combine_classes(table, table_sizes.xs, w.full)
                ),
                cls=combine_classes("overflow-x-auto", bg_dui.base_200, rounded.lg, p(2))
            ) if gpu_info.get('processes') else Div(
                P("No active GPU processes", cls=combine_classes(font_size.sm, text_dui.base_content.opacity(50), text_align.center, p(4))),
                cls=combine_classes(bg_dui.base_200, rounded.lg)
            ),
            cls=""
        ) if gpu_info.get('processes') is not None else None,

        cls=str(card_body),
        id="gpu-card-body"
    )

def render_temperature_card(temp_info):
    """Render the temperature sensors card."""
    if not temp_info:
        return Div(
            Div(
                H3("Temperature Sensors", cls=combine_classes(card_title, text_dui.base_content)),
                cls=str(m.b(4))
            ),
            Div(
                "No temperature sensors detected",
                cls=combine_classes(alert, alert_colors.info)
            ),
            cls=str(card_body)
        )

    # Group temperatures by type
    grouped_temps = {}
    for temp in temp_info:
        temp_type = temp['type']
        if temp_type not in grouped_temps:
            grouped_temps[temp_type] = []
        grouped_temps[temp_type].append(temp)

    # Find the highest temperature for the header badge
    max_temp = max((t['current'] for t in temp_info), default=0)

    return Div(
        Div(
            H3("Temperature Sensors", cls=combine_classes(card_title, text_dui.base_content)),
            Span(
                f"{max_temp:.1f}°C",
                cls=combine_classes(
                    badge,
                    get_temperature_badge_color(max_temp),
                    badge_sizes.lg
                )
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        Div(
            *[Div(
                # Sensor type header
                P(temp_type.replace('_', ' ').title(),
                  cls=combine_classes(font_size.sm, font_weight.semibold, m.b(2), text_dui.base_content)),

                # Individual sensors
                Div(
                    *[Div(
                        Label(
                            Span(sensor['label'], cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                            Label(
                                Span(
                                    f"{sensor['current']:.1f}°C",
                                    cls=combine_classes(
                                        font_weight.medium,
                                        get_temperature_color(
                                            sensor['current'],
                                            sensor['high'] or 85,
                                            sensor['critical'] or 95
                                        )
                                    )
                                ),
                                Span(
                                    f"H: {sensor['high']:.0f}°C" if sensor['high'] else "",
                                    cls=combine_classes(font_size.xs, text_dui.base_content.opacity(50), m.l(2))
                                ) if sensor['high'] else None,
                                Span(
                                    f"C: {sensor['critical']:.0f}°C" if sensor['critical'] else "",
                                    cls=combine_classes(font_size.xs, text_dui.error.opacity(50), m.l(2))
                                ) if sensor['critical'] else None,
                                cls=combine_classes(flex_display, items.center)
                            ),
                            cls=combine_classes(flex_display, justify.between, items.center)
                        ),

                        # Temperature bar visualization
                        Label(
                            Label(
                                cls=combine_classes(
                                    h(2),
                                    rounded.full,
                                    bg_dui.base_300,
                                    "relative",
                                    "overflow-hidden"
                                ),
                                style=f"background: linear-gradient(to right, {self._get_temp_gradient(sensor['current'], sensor['high'] or 85, sensor['critical'] or 95)})"
                            ) if False else None,  # Disabled gradient for now, using color text instead
                            cls=str(m.t(1))
                        ) if False else None,

                        cls=combine_classes(p(2), bg_dui.base_200, rounded.md, m.b(2))
                    ) for sensor in sensors],
                    cls=""
                ),
                cls=str(m.b(3))
            ) for temp_type, sensors in grouped_temps.items()],
            cls=""
        ),

        cls=str(card_body),
        id="temperature-card-body"
    )

def render_settings_modal():
    """Render the settings modal for configuring refresh intervals."""
    return Dialog(
        Div(
            # Close button at corner
            Form(
                Button(
                    "✕",
                    cls=combine_classes(
                        btn,
                        btn_sizes.sm,
                        btn_modifiers.circle,
                        btn_styles.ghost,
                        position.absolute,
                        right._2,
                        top._2
                    )
                ),
                method="dialog"
            ),
            H3("Refresh Interval Settings", cls=combine_classes(font_size.lg, font_weight.bold, m.b(4))),
            P("Adjust the refresh intervals for each component (in seconds)",
              cls=combine_classes(text_dui.base_content.opacity(70), font_size.sm, m.b(6))),

            # Settings form
            Div(
                # CPU interval
                Div(
                    Label(
                        Span("CPU", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['cpu']}s", id="cpu-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(REFRESH_INTERVALS['cpu']),
                        id="cpu-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('cpu-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Memory interval
                Div(
                    Label(
                        Span("Memory", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['memory']}s", id="memory-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(REFRESH_INTERVALS['memory']),
                        id="memory-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('memory-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Disk interval
                Div(
                    Label(
                        Span("Disk", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['disk']}s", id="disk-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="5",
                        max="60",
                        value=str(REFRESH_INTERVALS['disk']),
                        id="disk-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('disk-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Network interval
                Div(
                    Label(
                        Span("Network", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['network']}s", id="network-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(REFRESH_INTERVALS['network']),
                        id="network-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('network-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Process interval
                Div(
                    Label(
                        Span("Processes", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['process']}s", id="process-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="2",
                        max="60",
                        value=str(REFRESH_INTERVALS['process']),
                        id="process-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('process-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # GPU interval
                Div(
                    Label(
                        Span("GPU", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['gpu']}s", id="gpu-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(REFRESH_INTERVALS['gpu']),
                        id="gpu-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('gpu-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Temperature interval
                Div(
                    Label(
                        Span("Temperature", cls=combine_classes(font_weight.medium)),
                        Span(f"{REFRESH_INTERVALS['temperature']}s", id="temperature-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="2",
                        max="60",
                        value=str(REFRESH_INTERVALS['temperature']),
                        id="temperature-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('temperature-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),
                cls=str(m.b(6))
            ),

            # Action buttons
            Div(
                Button(
                    "Apply",
                    cls=combine_classes(btn, btn_colors.primary),
                    onclick="updateRefreshIntervals()",
                    hx_post="/update_intervals",
                    hx_vals="js:{cpu: document.getElementById('cpu-interval').value, memory: document.getElementById('memory-interval').value, disk: document.getElementById('disk-interval').value, network: document.getElementById('network-interval').value, process: document.getElementById('process-interval').value, gpu: document.getElementById('gpu-interval').value, temperature: document.getElementById('temperature-interval').value}",
                    hx_swap="none"
                ),
                Form(
                    Button("Cancel", cls=combine_classes(btn, btn_styles.ghost)),
                    method="dialog",
                    cls="inline"
                ),
                cls=combine_classes(modal_action, gap(2))
            ),
            cls=combine_classes(modal_box, w("11/12"), max_w._2xl)
        ),
        id="settings_modal",
        cls=str(modal)
    )

@rt('/')
def get():
    # Get initial system information
    static_info = get_static_system_info()
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    disk_info = get_disk_info()
    net_info = get_network_info()
    proc_info = get_process_info()
    gpu_info = check_gpu()
    temp_info = get_temperature_info()

    return Div(
        # Navbar with improved styling
        Div(
            Div(
                Div(
                    H1("System Monitor Dashboard",
                       cls=combine_classes(font_size._2xl, font_weight.bold, text_dui.base_content)),
                    cls=str(navbar_start)
                ),
                Div(
                    # Connection status indicator
                    Label(
                        Span(cls=combine_classes(status, status_colors.success, status_sizes.sm, m.r(2))),
                        Span("Live", cls=combine_classes(text_dui.success, font_size.sm)),
                        id="connection-status",
                        cls=combine_classes(flex_display, items.center)
                    ),
                    # Settings button
                    Button(
                        "⚙ Settings",
                        cls=combine_classes(btn, btn_sizes.sm, btn_styles.ghost),
                        onclick="settings_modal.showModal()"
                    ),
                    create_theme_selector(),
                    cls=combine_classes(flex_display, justify.end, items.center, gap(4), navbar_end)
                ),
                cls=combine_classes(navbar, bg_dui.base_100, shadow.sm, p(4))
            )
        ),

        # SSE connection for real-time updates
        Div(
            id="sse-connection",
            hx_ext="sse",
            sse_connect="/stream_updates",
            sse_swap="message",
            style="display: none;"
        ),

        # Main content container
        Div(
            # System Overview Header
            Div(
                H2("System Overview", cls=combine_classes(font_size.xl, font_weight.semibold, text_dui.base_content, m.b(6))),
                P(f"Monitoring {static_info['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                  cls=combine_classes(text_dui.base_content.opacity(60), font_size.sm)),
                id="timestamp",
                cls=str(m.b(6))
            ),

            # Grid layout for cards
            Div(
                # OS Information Card
                Div(
                    render_os_info_card(),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md)
                ),

                # CPU Usage Card
                Div(
                    render_cpu_card(cpu_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="cpu-card"
                ),

                # Memory Usage Card
                Div(
                    render_memory_card(mem_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="memory-card"
                ),

                # Disk Usage Card
                Div(
                    render_disk_card(disk_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="disk-card"
                ),

                # Network Monitoring Card
                Div(
                    render_network_card(net_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="network-card"
                ),

                # Process Monitoring Card
                Div(
                    render_process_card(proc_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="process-card"
                ),

                # GPU Information Card
                Div(
                    render_gpu_card(gpu_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="gpu-card"
                ),

                # Temperature Sensors Card
                Div(
                    render_temperature_card(temp_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="temperature-card"
                ),

                cls=combine_classes(grid_display, grid_cols(1).md, grid_cols(2).lg, grid_cols(3).xl, gap(6))
            ),

            # Footer
            Div(
                P(f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
                  cls=combine_classes(text_dui.base_content.opacity(50), font_size.xs, text_align.center)),
                cls=str(m.t(8))
            ),

            cls=combine_classes(p(6), max_w.screen_2xl, m.auto)
        ),

        # Settings Modal
        render_settings_modal(),

        cls=combine_classes(min_h.screen, bg_dui.base_200)
    )

@rt('/update_intervals', methods=['POST'])
async def update_intervals(cpu: int, memory: int, disk: int, network: int, process: int, gpu: int, temperature: int):
    """Update the refresh intervals for each component."""
    global REFRESH_INTERVALS
    REFRESH_INTERVALS['cpu'] = int(cpu)
    REFRESH_INTERVALS['memory'] = int(memory)
    REFRESH_INTERVALS['disk'] = int(disk)
    REFRESH_INTERVALS['network'] = int(network)
    REFRESH_INTERVALS['process'] = int(process)
    REFRESH_INTERVALS['gpu'] = int(gpu)
    REFRESH_INTERVALS['temperature'] = int(temperature)

    # Reset last update times to apply changes immediately
    for key in LAST_UPDATE_TIMES:
        LAST_UPDATE_TIMES[key] = 0

    return ""  # Empty response for HTMX

@rt('/stream_updates')
async def stream_updates():
    """SSE endpoint for streaming system updates."""
    async def update_stream():
        try:
            while True:
                current_time = time.time()
                updates = []

                # Check and update CPU if interval has passed
                if current_time - LAST_UPDATE_TIMES['cpu'] >= REFRESH_INTERVALS['cpu']:
                    cpu_info = get_cpu_info()
                    updates.append(oob_swap(
                        render_cpu_card(cpu_info),
                        target_id="cpu-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['cpu'] = current_time

                # Check and update Memory if interval has passed
                if current_time - LAST_UPDATE_TIMES['memory'] >= REFRESH_INTERVALS['memory']:
                    mem_info = get_memory_info()
                    updates.append(oob_swap(
                        render_memory_card(mem_info),
                        target_id="memory-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['memory'] = current_time

                # Check and update Disk if interval has passed
                if current_time - LAST_UPDATE_TIMES['disk'] >= REFRESH_INTERVALS['disk']:
                    disk_info = get_disk_info()
                    updates.append(oob_swap(
                        render_disk_card(disk_info),
                        target_id="disk-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['disk'] = current_time

                # Check and update Network if interval has passed
                if current_time - LAST_UPDATE_TIMES['network'] >= REFRESH_INTERVALS['network']:
                    net_info = get_network_info()
                    updates.append(oob_swap(
                        render_network_card(net_info),
                        target_id="network-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['network'] = current_time

                # Check and update Process if interval has passed
                if current_time - LAST_UPDATE_TIMES['process'] >= REFRESH_INTERVALS['process']:
                    proc_info = get_process_info()
                    updates.append(oob_swap(
                        render_process_card(proc_info),
                        target_id="process-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['process'] = current_time

                # Check and update GPU if interval has passed and available
                if current_time - LAST_UPDATE_TIMES['gpu'] >= REFRESH_INTERVALS['gpu']:
                    gpu_info = check_gpu()
                    if gpu_info['available']:
                        updates.append(oob_swap(
                            render_gpu_card(gpu_info),
                            target_id="gpu-card-body",
                            swap_type="outerHTML"
                        ))
                    LAST_UPDATE_TIMES['gpu'] = current_time

                # Check and update Temperature if interval has passed
                if current_time - LAST_UPDATE_TIMES['temperature'] >= REFRESH_INTERVALS['temperature']:
                    temp_info = get_temperature_info()
                    updates.append(oob_swap(
                        render_temperature_card(temp_info),
                        target_id="temperature-card-body",
                        swap_type="outerHTML"
                    ))
                    LAST_UPDATE_TIMES['temperature'] = current_time

                # Always update timestamp
                if updates:  # Only add timestamp if there are other updates
                    updates.append(oob_swap(
                        P(f"Monitoring {get_static_system_info()['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                          cls=combine_classes(text_dui.base_content.opacity(60), font_size.sm)),
                        target_id="timestamp",
                        swap_type="innerHTML"
                    ))

                # Send updates only if there are any
                if updates:
                    yield sse_message(Div(*updates))

                # Wait before next check - use minimum interval for responsiveness
                min_interval = min(REFRESH_INTERVALS.values())
                await asyncio.sleep(min(1, min_interval))  # At least 1 second

        except Exception as e:
            print(f"Error in update stream: {e}")

    return EventStream(update_stream())

def open_browser(url):
    """Open browser based on environment settings."""
    browser_mode = os.environ.get('FASTHTML_BROWSER', 'default').lower()

    if browser_mode == 'none':
        print(f"Server running at {url}")
        print("Browser auto-open disabled. Please open manually.")
        return

    if browser_mode == 'app':
        print(f"Opening in app mode at {url}")

        if sys.platform == 'linux':
            browsers = [
                ['google-chrome', '--app=' + url],
                ['chromium', '--app=' + url],
                ['firefox', '--new-window', url],
            ]

            for browser_cmd in browsers:
                try:
                    subprocess.Popen(browser_cmd,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    continue

    print(f"Opening in browser at {url}")
    webbrowser.open(url)

if __name__ == '__main__':
    import uvicorn
    import threading
    import time

    url = f"http://{HOST}:{PORT}"

    # Open browser after a short delay
    timer = threading.Timer(1.5, lambda: open_browser(url))
    timer.daemon = True
    timer.start()

    print(f"Starting System Monitor Dashboard on {url}")

    # Run the server
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")