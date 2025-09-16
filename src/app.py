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
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes, btn_styles
from cjm_fasthtml_daisyui.components.data_display.card import card, card_body, card_title, card_actions
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.stat import stat, stat_title, stat_value, stat_desc, stats, stats_direction
from cjm_fasthtml_daisyui.components.data_display.status import status, status_colors, status_sizes
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

def check_gpu():
    """Check for GPU availability and get info."""
    gpu_info = {'available': False, 'type': 'None', 'details': {}}

    # Check for NVIDIA GPU
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu',
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
                        'memory_total': int(parts[1]),
                        'memory_used': int(parts[2]),
                        'memory_free': int(parts[3]),
                        'utilization': int(parts[4])
                    }
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return gpu_info

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

                # GPU Utilization
                Div(
                    P("Utilization", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                    render_progress_bar(details['utilization']),
                    cls=str(m.b(3))
                ),

                # GPU Memory
                Div(
                    P("Memory", cls=combine_classes(font_size.xs, text_dui.base_content.opacity(70))),
                    render_progress_bar(
                        (details['memory_used'] / details['memory_total']) * 100,
                        label=f"{details['memory_used']} MB / {details['memory_total']} MB"
                    ),
                    cls=""
                ),

                cls=combine_classes(p(3), bg_dui.base_200, rounded.lg, m.b(3))
            ) for gpu_id, details in gpu_info['details'].items()],
            cls=""
        ),

        cls=str(card_body),
        id="gpu-card-body"
    )

@rt('/')
def get():
    # Get initial system information
    static_info = get_static_system_info()
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    disk_info = get_disk_info()
    gpu_info = check_gpu()

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
                    Div(
                        Span(cls=combine_classes(status, status_colors.success, status_sizes.sm, m.r(2))),
                        Span("Live", cls=combine_classes(text_dui.success, font_size.sm)),
                        id="connection-status",
                        cls=combine_classes(flex_display, items.center)
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

                # GPU Information Card
                Div(
                    render_gpu_card(gpu_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id="gpu-card"
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
        cls=combine_classes(min_h.screen, bg_dui.base_200)
    )

@rt('/stream_updates')
async def stream_updates():
    """SSE endpoint for streaming system updates."""
    async def update_stream():
        try:
            while True:
                # Get current system stats
                cpu_info = get_cpu_info()
                mem_info = get_memory_info()
                disk_info = get_disk_info()
                gpu_info = check_gpu()

                # Create OOB swap elements for each card
                updates = []

                # Update CPU card
                updates.append(oob_swap(
                    render_cpu_card(cpu_info),
                    target_id="cpu-card-body",
                    swap_type="outerHTML"
                ))

                # Update Memory card
                updates.append(oob_swap(
                    render_memory_card(mem_info),
                    target_id="memory-card-body",
                    swap_type="outerHTML"
                ))

                # Update Disk card (less frequent updates needed)
                if int(time.time()) % 10 == 0:  # Every 10 seconds
                    updates.append(oob_swap(
                        render_disk_card(disk_info),
                        target_id="disk-card-body",
                        swap_type="outerHTML"
                    ))

                # Update GPU card if available
                if gpu_info['available']:
                    updates.append(oob_swap(
                        render_gpu_card(gpu_info),
                        target_id="gpu-card-body",
                        swap_type="outerHTML"
                    ))

                # Update timestamp
                updates.append(oob_swap(
                    P(f"Monitoring {get_static_system_info()['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                      cls=combine_classes(text_dui.base_content.opacity(60), font_size.sm)),
                    target_id="timestamp",
                    swap_type="innerHTML"
                ))

                # Send all updates
                yield sse_message(Div(*updates))

                # Wait before next update
                await asyncio.sleep(2)  # Update every 2 seconds

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