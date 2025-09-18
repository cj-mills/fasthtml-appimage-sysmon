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
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, text_align, font_family, break_all, leading, break_all
from cjm_fasthtml_tailwind.utilities.borders import rounded, border, border_color
from cjm_fasthtml_tailwind.utilities.effects import shadow
from cjm_fasthtml_tailwind.utilities.layout import position, right, top, display_tw
from cjm_fasthtml_tailwind.core.base import combine_classes

from utils import (

    open_browser
)
import config
from monitors import (
    get_cpu_info, 
    get_static_system_info, 
    get_memory_info, 
    get_disk_info, 
    get_network_info,
    get_process_info,
    check_gpu,
    get_temperature_info
)
from components import (
    render_process_count,
    render_process_status,
    render_os_info_card,
    render_cpu_card,
    render_memory_card,
    render_disk_card,
    render_network_card,
    render_process_card,
    render_gpu_card,
    render_temperature_card,
    render_cpu_processes_table,
    render_memory_processes_table,
    render_settings_modal
)


# Initialize SSE Broadcast Manager
sse_manager = SSEBroadcastManager(**config.SSE_CONFIG)

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
        # Navbar with improved styling and mobile responsiveness
        Div(
            Div(
                Div(
                    H1("System Monitor Dashboard",
                       cls=combine_classes(
                           font_size.lg,          # Smaller on mobile
                           font_size.xl.sm,       # Medium on small screens
                           font_size._2xl.md,     # Large on medium+ screens
                           font_weight.bold,
                           text_dui.base_content
                       )),
                    cls=str(navbar_start)
                ),
                Div(
                    # Connection status indicator - hide text on mobile
                    Label(
                        Span(cls=combine_classes(status, status_colors.success, status_sizes.sm, m.r(1), m.r(2).sm)),
                        Span("Live", cls=combine_classes(
                            text_dui.success,
                            font_size.sm,
                            display_tw.hidden,          # Hide text on mobile
                            display_tw.inline.sm        # Show on small screens and up
                        )),
                        id="connection-status",
                        cls=combine_classes(flex_display, items.center)
                    ),
                    # Settings button - icon only on mobile
                    Button(
                        Span("⚙", cls=""),
                        Span(" Settings", cls=combine_classes(
                            display_tw.hidden,          # Hide text on mobile
                            display_tw.inline.sm        # Show on small screens and up
                        )),
                        cls=combine_classes(btn, btn_sizes.sm, btn_styles.ghost),
                        onclick="settings_modal.showModal()"
                    ),
                    create_theme_selector(),
                    cls=combine_classes(
                        flex_display,
                        justify.end,
                        items.center,
                        gap(2),               # Smaller gap on mobile
                        gap(4).sm,            # Normal gap on small+
                        navbar_end
                    )
                ),
                cls=combine_classes(
                    navbar,
                    bg_dui.base_100,
                    shadow.sm,
                    p(2),                     # Smaller padding on mobile
                    p(4).sm                   # Normal padding on small+
                )
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
                H2("System Overview", cls=combine_classes(
                    font_size.lg,              # Smaller on mobile
                    font_size.xl.sm,           # Medium on small
                    font_size._2xl.md,         # Large on medium+
                    font_weight.semibold,
                    text_dui.base_content,
                    m.b(4),                    # Less margin on mobile
                    m.b(6).sm                  # Normal margin on small+
                )),
                P(f"Monitoring {static_info['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                  cls=combine_classes(
                      text_dui.base_content,
                      font_size.xs,            # Extra small on mobile
                      font_size.sm.sm,         # Small on small screens+
                      break_all              # Allow line breaks for long hostnames
                  )),
                id="timestamp",
                cls=combine_classes(
                    m.b(4),                    # Less margin on mobile
                    m.b(6).sm                  # Normal margin on small+
                )
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

                cls=combine_classes(
                    grid_display,
                    grid_cols(1),          # Mobile: 1 column (default)
                    grid_cols(1).sm,       # Small: still 1 column (for better readability)
                    grid_cols(2).md,       # Medium: 2 columns
                    grid_cols(2).lg,       # Large: 2 columns (cards have good width)
                    grid_cols(3).xl,       # Extra large: 3 columns
                    grid_cols(4)._2xl,     # 2XL: 4 columns for ultra-wide screens
                    gap(4),                # Reduced gap for mobile
                    gap(6).md              # Larger gap for bigger screens
                )
            ),

            # Footer
            Div(
                P(f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
                  cls=combine_classes(text_dui.base_content, font_size.xs, text_align.center)),
                cls=str(m.t(8))
            ),

            cls=combine_classes(
                p(4),                    # Smaller padding on mobile
                p(6).sm,                 # Normal padding on small+
                p(8).lg,                 # Larger padding on desktop
                max_w.screen_2xl,
                m.auto
            )
        ),

        # Settings Modal
        render_settings_modal(),

        cls=combine_classes(min_h.screen, bg_dui.base_200)
    )

@rt('/update_intervals', methods=['POST'])
async def update_intervals(cpu: int, memory: int, disk: int, network: int, process: int, gpu: int, temperature: int):
    """Update the refresh intervals for each component."""
    config.REFRESH_INTERVALS['cpu'] = int(cpu)
    config.REFRESH_INTERVALS['memory'] = int(memory)
    config.REFRESH_INTERVALS['disk'] = int(disk)
    config.REFRESH_INTERVALS['network'] = int(network)
    config.REFRESH_INTERVALS['process'] = int(process)
    config.REFRESH_INTERVALS['gpu'] = int(gpu)
    config.REFRESH_INTERVALS['temperature'] = int(temperature)

    # Reset last update times to apply changes immediately
    for key in config.LAST_UPDATE_TIMES:
        config.LAST_UPDATE_TIMES[key] = 0

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
                if current_time - config.LAST_UPDATE_TIMES['cpu'] >= config.REFRESH_INTERVALS['cpu']:
                    cpu_info = get_cpu_info()
                    updates.append(oob_swap(
                        render_cpu_card(cpu_info),
                        target_id="cpu-card-body",
                        swap_type="outerHTML"
                    ))
                    config.LAST_UPDATE_TIMES['cpu'] = current_time

                # Check and update Memory if interval has passed
                if current_time - config.LAST_UPDATE_TIMES['memory'] >= config.REFRESH_INTERVALS['memory']:
                    mem_info = get_memory_info()
                    updates.append(oob_swap(
                        render_memory_card(mem_info),
                        target_id="memory-card-body",
                        swap_type="outerHTML"
                    ))
                    config.LAST_UPDATE_TIMES['memory'] = current_time

                # Check and update Disk if interval has passed
                if current_time - config.LAST_UPDATE_TIMES['disk'] >= config.REFRESH_INTERVALS['disk']:
                    disk_info = get_disk_info()
                    updates.append(oob_swap(
                        render_disk_card(disk_info),
                        target_id="disk-card-body",
                        swap_type="outerHTML"
                    ))
                    config.LAST_UPDATE_TIMES['disk'] = current_time

                # Check and update Network if interval has passed
                if current_time - config.LAST_UPDATE_TIMES['network'] >= config.REFRESH_INTERVALS['network']:
                    net_info = get_network_info()
                    updates.append(oob_swap(
                        render_network_card(net_info),
                        target_id="network-card-body",
                        swap_type="outerHTML"
                    ))
                    config.LAST_UPDATE_TIMES['network'] = current_time

                # Check and update Process if interval has passed
                if current_time - config.LAST_UPDATE_TIMES['process'] >= config.REFRESH_INTERVALS['process']:
                    proc_info = get_process_info()
                    # Use fine-grained updates for process card
                    updates.extend([
                        oob_swap(
                            render_process_count(proc_info['total']),
                            target_id="process-count",
                            swap_type="outerHTML"
                        ),
                        oob_swap(
                            render_process_status(proc_info['status_counts']),
                            target_id="process-status",
                            swap_type="outerHTML"
                        ),
                        oob_swap(
                            render_cpu_processes_table(proc_info['top_cpu']),
                            target_id="cpu-processes-table",
                            swap_type="outerHTML"
                        ),
                        oob_swap(
                            render_memory_processes_table(proc_info['top_memory']),
                            target_id="memory-processes-table",
                            swap_type="outerHTML"
                        )
                    ])
                    config.LAST_UPDATE_TIMES['process'] = current_time

                # Check and update GPU if interval has passed and available
                if current_time - config.LAST_UPDATE_TIMES['gpu'] >= config.REFRESH_INTERVALS['gpu']:
                    gpu_info = check_gpu()
                    if gpu_info['available']:
                        updates.append(oob_swap(
                            render_gpu_card(gpu_info),
                            target_id="gpu-card-body",
                            swap_type="outerHTML"
                        ))
                    config.LAST_UPDATE_TIMES['gpu'] = current_time

                # Check and update Temperature if interval has passed
                if current_time - config.LAST_UPDATE_TIMES['temperature'] >= config.REFRESH_INTERVALS['temperature']:
                    temp_info = get_temperature_info()
                    updates.append(oob_swap(
                        render_temperature_card(temp_info),
                        target_id="temperature-card-body",
                        swap_type="outerHTML"
                    ))
                    config.LAST_UPDATE_TIMES['temperature'] = current_time

                # Always update timestamp
                if updates:  # Only add timestamp if there are other updates
                    updates.append(oob_swap(
                        P(f"Monitoring {get_static_system_info()['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                          cls=combine_classes(text_dui.base_content, font_size.sm)),
                        target_id="timestamp",
                        swap_type="innerHTML"
                    ))

                # Send updates only if there are any
                if updates:
                    yield sse_message(Div(*updates))

                # Wait before next check - use minimum interval for responsiveness
                min_interval = min(config.REFRESH_INTERVALS.values())
                await asyncio.sleep(min(1, min_interval))  # At least 1 second

        except Exception as e:
            print(f"Error in update stream: {e}")

    return EventStream(update_stream())

if __name__ == '__main__':
    import uvicorn
    import threading
    import time

    url = f"http://{config.HOST}:{config.PORT}"

    # Open browser after a short delay
    timer = threading.Timer(1.5, lambda: open_browser(url))
    timer.daemon = True
    timer.start()

    print(f"Starting System Monitor Dashboard on {url}")

    # Run the server
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")