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
from concurrent.futures import TimeoutError

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

from cjm_fasthtml_sysmon.core.utils import open_browser
from cjm_fasthtml_sysmon.core.html_ids import HtmlIds
import config
from cjm_fasthtml_sysmon.monitors.cpu import get_cpu_info
from cjm_fasthtml_sysmon.monitors.system import get_static_system_info
from cjm_fasthtml_sysmon.monitors.memory import get_memory_info
from cjm_fasthtml_sysmon.monitors.disk import get_disk_info
from cjm_fasthtml_sysmon.monitors.network import get_network_info
from cjm_fasthtml_sysmon.monitors.processes import get_process_info
from cjm_fasthtml_sysmon.monitors.gpu import get_gpu_info
from cjm_fasthtml_sysmon.monitors.sensors import get_temperature_info
from cjm_fasthtml_sysmon.components.base import render_process_count, render_process_status
from cjm_fasthtml_sysmon.components.cards import (
    render_os_info_card,
    render_cpu_card,
    render_memory_card,
    render_disk_card,
    render_network_card,
    render_process_card,
    render_gpu_card,
    render_temperature_card
)
from cjm_fasthtml_sysmon.components.tables import render_cpu_processes_table, render_memory_processes_table
from cjm_fasthtml_sysmon.components.modals import render_settings_modal

from uvicorn.main import Server

original_handler = Server.handle_exit

# Initialize SSE Broadcast Manager first (moved up)
sse_manager = SSEBroadcastManager(**config.SSE_CONFIG)

class SSEShutdownHandler:
    should_exit = False
    active_connections = set()
    shutdown_event = asyncio.Event()

    @staticmethod
    def handle_exit(*args, **kwargs):
        SSEShutdownHandler.should_exit = True

        # Signal shutdown to all waiting tasks
        SSEShutdownHandler.shutdown_event.set()

        # Send shutdown message directly to all SSE connection queues
        try:
            print(f"\nBroadcasting shutdown to {sse_manager.connection_count} connections...")

            # Create the shutdown message
            shutdown_message = {
                "type": "shutdown",
                "timestamp": datetime.now().isoformat(),
                "data": {"message": "Server shutting down"}
            }

            # Send directly to all connection queues (synchronously)
            for queue in list(sse_manager.connections):
                try:
                    # Use put_nowait to avoid blocking
                    queue.put_nowait(shutdown_message)
                except asyncio.QueueFull:
                    print("Queue full, couldn't send shutdown message")
                except Exception as e:
                    print(f"Error sending shutdown to queue: {e}")

            print(f"Sent shutdown message to {len(sse_manager.connections)} connections")

            # Give connections a moment to process the messages
            time.sleep(1.0)

        except Exception as e:
            print(f"Error during shutdown broadcast: {e}")

        # Now close all active SSE connections
        print(f"Closing {len(SSEShutdownHandler.active_connections)} active SSE connections...")
        for connection in list(SSEShutdownHandler.active_connections):
            try:
                connection.cancel()
            except Exception as e:
                print(f"Error closing connection: {e}")
        SSEShutdownHandler.active_connections.clear()

        original_handler(*args, **kwargs)

Server.handle_exit = SSEShutdownHandler.handle_exit

# Initialize HTMX SSE Connector
htmx_sse_connector = HTMXSSEConnector()

static_path = Path(__file__).absolute().parent

# Create the FastHTML app with DaisyUI headers
app, rt = fast_app(
    pico=False,
    hdrs=[*get_daisyui_headers()],
    title="System Monitor Dashboard",
    static_path=str(static_path)
)

app.hdrs.append(Link(rel='icon', type='image/png', href='/static/layout-dashboard.png'))  # for PNG

# Insert HTMX SSE extension
insert_htmx_sse_ext(app.hdrs)

# Helper functions for connection status indicators
def create_connection_status_indicators():
    """Create status indicator elements for different connection states"""
    return {
        'active': Span(
            Span(cls=combine_classes(status, status_colors.success, status_sizes.sm, m.r(1), m.r(2).sm)),
            Span("Live", cls=combine_classes(
                text_dui.success,
                font_size.sm,
                display_tw.hidden,          # Hide text on mobile
                display_tw.inline.sm        # Show on small screens and up
            )),
        ),
        'disconnected': Span(
            Span(cls=combine_classes(status, status_colors.warning, status_sizes.sm, m.r(1), m.r(2).sm)),
            Span("Disconnected", cls=combine_classes(
                text_dui.warning,
                font_size.sm,
                display_tw.hidden,
                display_tw.inline.sm
            )),
        ),
        'error': Span(
            Span(cls=combine_classes(status, status_colors.error, status_sizes.sm, m.r(1), m.r(2).sm)),
            Span("Error", cls=combine_classes(
                text_dui.error,
                font_size.sm,
                display_tw.hidden,
                display_tw.inline.sm
            )),
        ),
        'reconnecting': Span(
            Span(cls=combine_classes(status, status_colors.info, status_sizes.sm, m.r(1), m.r(2).sm)),
            Span("Reconnecting...", cls=combine_classes(
                text_dui.info,
                font_size.sm,
                display_tw.hidden,
                display_tw.inline.sm
            )),
        )
    }

def render_sse_connection_monitor():
    """Create a Script element that monitors SSE connection status"""
    indicators = create_connection_status_indicators()

    # Convert indicators to HTML strings for JavaScript
    status_html = {
        'active': str(indicators['active']),
        'disconnected': str(indicators['disconnected']),
        'error': str(indicators['error']),
        'reconnecting': str(indicators['reconnecting'])
    }

    monitor_script = f"""
    // SSE Connection Monitor
    (function() {{
        let reconnectAttempts = 0;
        let maxReconnectAttempts = 10;
        let reconnectDelay = 1000;
        let isShuttingDown = false;
        let statusElement = document.getElementById('{HtmlIds.CONNECTION_STATUS}');
        let sseElement = document.getElementById('{HtmlIds.SSE_CONNECTION}');

        const statusIndicators = {{
            active: `{status_html['active']}`,
            disconnected: `{status_html['disconnected']}`,
            error: `{status_html['error']}`,
            reconnecting: `{status_html['reconnecting']}`
        }};

        function updateStatus(state) {{
            if (statusElement && statusIndicators[state]) {{
                statusElement.innerHTML = statusIndicators[state];
            }}
        }}

        // Monitor HTMX SSE events
        document.body.addEventListener('htmx:sseOpen', function(evt) {{
            if (evt.detail.elt === sseElement) {{
                console.log('SSE connection opened');
                updateStatus('active');
                reconnectAttempts = 0;
            }}
        }});

        document.body.addEventListener('htmx:sseError', function(evt) {{
            if (evt.detail.elt === sseElement) {{
                console.log('SSE connection error');

                // Don't try to reconnect if shutting down
                if (isShuttingDown) {{
                    console.log('Server is shutting down, not attempting reconnection');
                    updateStatus('disconnected');
                    return;
                }}

                updateStatus('error');

                // Attempt to reconnect
                if (reconnectAttempts < maxReconnectAttempts) {{
                    setTimeout(function() {{
                        reconnectAttempts++;
                        console.log('Attempting to reconnect... (attempt ' + reconnectAttempts + ')');
                        updateStatus('reconnecting');
                        htmx.trigger(sseElement, 'htmx:sseReconnect');
                    }}, reconnectDelay * Math.min(reconnectAttempts + 1, 5));
                }} else {{
                    updateStatus('disconnected');
                }}
            }}
        }});

        document.body.addEventListener('htmx:sseClose', function(evt) {{
            if (evt.detail.elt === sseElement) {{
                console.log('SSE connection closed');
                updateStatus('disconnected');
            }}
        }});

        // Listen for custom close events from the server
        document.body.addEventListener('htmx:sseMessage', function(evt) {{
            if (evt.detail.elt === sseElement && evt.detail.event === 'close') {{
                console.log('Server requested connection close:', evt.detail.data);
                isShuttingDown = true;
                updateStatus('disconnected');
                // Stop trying to reconnect if server is shutting down
                reconnectAttempts = maxReconnectAttempts;
                // Close the EventSource
                if (sseElement._sseEventSource) {{
                    sseElement._sseEventSource.close();
                    delete sseElement._sseEventSource;
                }}
            }}
        }});

        // Also listen for when the SSE element is removed via OOB swap
        document.body.addEventListener('htmx:oobAfterSwap', function(evt) {{
            if (evt.detail.target && evt.detail.target.id === '{HtmlIds.SSE_CONNECTION}') {{
                console.log('SSE element removed via OOB swap - server shutting down');
                isShuttingDown = true;
                updateStatus('disconnected');
            }}
        }});

        // Handle page visibility changes
        document.addEventListener('visibilitychange', function() {{
            if (!document.hidden && sseElement && !isShuttingDown) {{
                // Check connection state when page becomes visible
                let evtSource = sseElement._sseEventSource;
                if (!evtSource || evtSource.readyState === EventSource.CLOSED) {{
                    console.log('Page became visible, reconnecting SSE...');
                    updateStatus('reconnecting');
                    htmx.trigger(sseElement, 'htmx:sseReconnect');
                }}
            }}
        }});

        // Initial status check
        updateStatus('reconnecting');
    }})();
    """

    return Script(monitor_script)

@rt('/')
def get():
    # Get initial system information
    static_info = get_static_system_info()
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    disk_info = get_disk_info()
    net_info = get_network_info()
    proc_info = get_process_info()
    gpu_info = get_gpu_info()
    temp_info = get_temperature_info()

    # Get initial connection status indicator
    indicators = create_connection_status_indicators()

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
                    # Connection status indicator - dynamically updated
                    Label(
                        indicators['reconnecting'],  # Start with reconnecting status
                        id=HtmlIds.CONNECTION_STATUS,
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
            id=HtmlIds.SSE_CONNECTION,
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
                id=HtmlIds.TIMESTAMP,
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
                    id=HtmlIds.CPU_CARD
                ),

                # Memory Usage Card
                Div(
                    render_memory_card(mem_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.MEMORY_CARD
                ),

                # Disk Usage Card
                Div(
                    render_disk_card(disk_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.DISK_CARD
                ),

                # Network Monitoring Card
                Div(
                    render_network_card(net_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.NETWORK_CARD
                ),

                # Process Monitoring Card
                Div(
                    render_process_card(proc_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.PROCESS_CARD
                ),

                # GPU Information Card
                Div(
                    render_gpu_card(gpu_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.GPU_CARD
                ),

                # Temperature Sensors Card
                Div(
                    render_temperature_card(temp_info),
                    cls=combine_classes(card, bg_dui.base_100, shadow.md),
                    id=HtmlIds.TEMPERATURE_CARD
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
        render_settings_modal(config.REFRESH_INTERVALS),

        # SSE Connection Monitor Script
        render_sse_connection_monitor(),

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

# Background task for generating system updates
async def generate_system_updates():
    """Background task that generates system updates and broadcasts them to all clients."""
    while not SSEShutdownHandler.should_exit:
        try:
            current_time = time.time()
            updates = []

            # Check and update CPU if interval has passed
            if current_time - config.LAST_UPDATE_TIMES['cpu'] >= config.REFRESH_INTERVALS['cpu']:
                cpu_info = get_cpu_info()
                updates.append(oob_swap(
                    render_cpu_card(cpu_info),
                    target_id=HtmlIds.CPU_CARD_BODY,
                    swap_type="outerHTML"
                ))
                config.LAST_UPDATE_TIMES['cpu'] = current_time

            # Check and update Memory if interval has passed
            if current_time - config.LAST_UPDATE_TIMES['memory'] >= config.REFRESH_INTERVALS['memory']:
                mem_info = get_memory_info()
                updates.append(oob_swap(
                    render_memory_card(mem_info),
                    target_id=HtmlIds.MEMORY_CARD_BODY,
                    swap_type="outerHTML"
                ))
                config.LAST_UPDATE_TIMES['memory'] = current_time

            # Check and update Disk if interval has passed
            if current_time - config.LAST_UPDATE_TIMES['disk'] >= config.REFRESH_INTERVALS['disk']:
                disk_info = get_disk_info()
                updates.append(oob_swap(
                    render_disk_card(disk_info),
                    target_id=HtmlIds.DISK_CARD_BODY,
                    swap_type="outerHTML"
                ))
                config.LAST_UPDATE_TIMES['disk'] = current_time

            # Check and update Network if interval has passed
            if current_time - config.LAST_UPDATE_TIMES['network'] >= config.REFRESH_INTERVALS['network']:
                net_info = get_network_info()
                updates.append(oob_swap(
                    render_network_card(net_info),
                    target_id=HtmlIds.NETWORK_CARD_BODY,
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
                        target_id=HtmlIds.PROCESS_COUNT,
                        swap_type="outerHTML"
                    ),
                    oob_swap(
                        render_process_status(proc_info['status_counts']),
                        target_id=HtmlIds.PROCESS_STATUS,
                        swap_type="outerHTML"
                    ),
                    oob_swap(
                        render_cpu_processes_table(proc_info['top_cpu']),
                        target_id=HtmlIds.CPU_PROCESSES_TABLE,
                        swap_type="outerHTML"
                    ),
                    oob_swap(
                        render_memory_processes_table(proc_info['top_memory']),
                        target_id=HtmlIds.MEMORY_PROCESSES_TABLE,
                        swap_type="outerHTML"
                    )
                ])
                config.LAST_UPDATE_TIMES['process'] = current_time

            # Check and update GPU if interval has passed and available
            if current_time - config.LAST_UPDATE_TIMES['gpu'] >= config.REFRESH_INTERVALS['gpu']:
                gpu_info = get_gpu_info()
                if gpu_info['available']:
                    updates.append(oob_swap(
                        render_gpu_card(gpu_info),
                        target_id=HtmlIds.GPU_CARD_BODY,
                        swap_type="outerHTML"
                    ))
                config.LAST_UPDATE_TIMES['gpu'] = current_time

            # Check and update Temperature if interval has passed
            if current_time - config.LAST_UPDATE_TIMES['temperature'] >= config.REFRESH_INTERVALS['temperature']:
                temp_info = get_temperature_info()
                updates.append(oob_swap(
                    render_temperature_card(temp_info),
                    target_id=HtmlIds.TEMPERATURE_CARD_BODY,
                    swap_type="outerHTML"
                ))
                config.LAST_UPDATE_TIMES['temperature'] = current_time

            # Always update timestamp
            if updates:  # Only add timestamp if there are other updates
                updates.append(oob_swap(
                    P(f"Monitoring {get_static_system_info()['hostname']} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                      cls=combine_classes(text_dui.base_content, font_size.sm)),
                    target_id=HtmlIds.TIMESTAMP,
                    swap_type="innerHTML"
                ))

            # Broadcast updates to all connected clients if there are any
            if updates:
                await sse_manager.broadcast("system_update", {"updates": updates})

            # Wait before next check - use minimum interval for responsiveness
            min_interval = min(config.REFRESH_INTERVALS.values())
            await asyncio.sleep(min(1, min_interval))  # At least 1 second

        except Exception as e:
            print(f"Error generating updates: {e}")
            await asyncio.sleep(1)  # Wait before retrying

# Start the background task when the module loads
import asyncio
update_task = None

def start_update_task():
    """Start the background update task."""
    global update_task
    if update_task is None or update_task.done():
        update_task = asyncio.create_task(generate_system_updates())

@rt('/stream_updates')
async def stream_updates():
    """SSE endpoint for streaming system updates to connected clients."""
    async def update_stream():
        # Create a task for this connection stream
        current_task = asyncio.current_task()

        # Register this connection with SSEBroadcastManager
        queue = await sse_manager.register_connection()

        # Track this connection in SSEShutdownHandler
        SSEShutdownHandler.active_connections.add(current_task)

        try:
            # Send initial connection confirmation
            yield f": Connected to system updates (active connections: {sse_manager.connection_count})\n\n"

            # Start the background task if not already running
            start_update_task()

            # Send updates and heartbeats
            while not SSEShutdownHandler.should_exit:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Check for shutdown message
                    if message.get("type") == "shutdown":
                        print(f"Received shutdown message, closing SSE connection")
                        # Send an OOB swap to remove the SSE element entirely
                        # This stops HTMX from trying to reconnect
                        close_element = Div(
                            id=HtmlIds.SSE_CONNECTION,
                            hx_swap_oob="true",
                            style="display: none;"
                        )
                        yield sse_message(close_element)
                        # Also send close event
                        yield f"event: close\ndata: {json.dumps({'message': 'Server shutting down'})}\n\n"
                        break

                    # Extract updates from the message
                    if message.get("type") == "system_update":
                        updates = message.get("data", {}).get("updates", [])
                        if updates:
                            # Send as SSE message
                            yield sse_message(Div(*updates))

                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat {datetime.now().isoformat()}\n\n"

                except asyncio.CancelledError:
                    # Connection is being closed
                    print(f"SSE connection cancelled")
                    yield f"event: close\ndata: {json.dumps({'message': 'Connection cancelled'})}\n\n"
                    break

                except Exception as e:
                    print(f"Error in update stream: {e}")
                    break

            # If we exit due to app shutdown, notify client
            if SSEShutdownHandler.should_exit:
                yield f"event: close\ndata: {json.dumps({'message': 'Server shutting down'})}\n\n"

        finally:
            # Unregister this connection
            await sse_manager.unregister_connection(queue)

            # Remove from active connections
            SSEShutdownHandler.active_connections.discard(current_task)

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