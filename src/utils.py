"""
Utility functions for the System Monitor Dashboard.
"""

import socket
import webbrowser
import subprocess
import sys
from contextlib import closing
from datetime import datetime

# DaisyUI imports
from cjm_fasthtml_daisyui.components.data_display.badge import badge_colors
from cjm_fasthtml_daisyui.components.feedback.progress import progress_colors
from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui


def find_free_port():
    """Find an available port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def format_bytes(bytes_value):
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


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


def open_browser(url):
    """Open browser based on environment settings."""
    import os

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