"""
Card components for displaying system metrics.
"""

from fasthtml.common import *

# DaisyUI imports
from cjm_fasthtml_daisyui.components.data_display.card import card, card_body, card_title, card_actions
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.stat import stat, stat_title, stat_value, stat_desc, stats, stats_direction
from cjm_fasthtml_daisyui.components.data_display.table import table, table_modifiers, table_sizes
from cjm_fasthtml_daisyui.components.navigation.tabs import tabs, tab, tab_modifiers, tabs_styles
from cjm_fasthtml_daisyui.components.feedback.progress import progress, progress_colors
from cjm_fasthtml_daisyui.components.feedback.alert import alert, alert_colors
from cjm_fasthtml_daisyui.components.layout.divider import divider
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui, border_dui

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.spacing import p, m, space
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import flex_display, gap, items, justify
from cjm_fasthtml_tailwind.utilities.sizing import w, h
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, text_align, font_family, break_all, leading
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
from cjm_fasthtml_tailwind.utilities.borders import rounded
from cjm_fasthtml_tailwind.core.base import combine_classes

from utils import (
    format_bytes, 
    format_bandwidth, 
    format_uptime, 
    get_temperature_color, 
    get_temperature_badge_color, 
)
import config
from monitors import (
    get_static_system_info, 
)
from components import (
    render_stat_card,
    render_progress_bar,
    render_process_count,
    render_process_status,
    render_cpu_processes_table,
    render_memory_processes_table
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
                     cls=combine_classes(text_dui.base_content, font_size.xs)),
                Span(f"Max: {cpu_info['frequency_max']:.0f} MHz",
                     cls=combine_classes(text_dui.base_content, font_size.xs)),
                cls=combine_classes(flex_display, justify.between, gap(2))
            ),
            cls=str(m.b(4))
        ),

        # Per-core usage (if not too many cores)
        Div(
            P("Per Core Usage", cls=combine_classes(font_size.sm, font_weight.medium, m.b(2))),
            Div(
                *[render_progress_bar(percent, label=f"Core {i}")
                  for i, percent in enumerate(cpu_info['percent_per_core'][:config.MAX_CPU_CORES])],
                cls=str(space.y(2))
            ),
            cls=str(m.t(2))
        ) if len(cpu_info['percent_per_core']) <= config.MAX_CPU_CORES else None,

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
              cls=combine_classes(font_size.xs, text_dui.base_content, m.t(1))),
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
                      cls=combine_classes(font_size.xs, text_dui.base_content)),
                    cls=str(m.b(2))
                ),
                render_progress_bar(disk['percent'],
                                  label=f"{format_bytes(disk['used'])} / {format_bytes(disk['total'])}"),
                P(f"Free: {format_bytes(disk['free'])}",
                  cls=combine_classes(font_size.xs, text_dui.base_content, m.t(1))),
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
                      cls=combine_classes(font_size.xs, text_dui.base_content)),
                    cls=str(m.b(2))
                ),

                # Bandwidth meters
                Div(
                    # Upload speed
                    Label(
                        Label(
                            Span("↑ Upload", cls=combine_classes(font_size.xs, text_dui.base_content)),
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
                            Span("↓ Download", cls=combine_classes(font_size.xs, text_dui.base_content)),
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
                             cls=combine_classes(font_size.xs, text_dui.base_content)),
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
            render_process_count(proc_info['total']),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),

        # Process status summary
        render_process_status(proc_info['status_counts']),

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
            render_cpu_processes_table(proc_info['top_cpu']),
            id="cpu-processes",
            style="display: block;"
        ),

        # Top Memory processes table
        Div(
            render_memory_processes_table(proc_info['top_memory']),
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
                        P("GPU Utilization", cls=combine_classes(font_size.xs, text_dui.base_content)),
                        render_progress_bar(details['utilization']),
                        cls=str(m.b(3))
                    ),

                    # GPU Memory
                    Label(
                        P("Memory", cls=combine_classes(font_size.xs, text_dui.base_content)),
                        render_progress_bar(
                            (details['memory_used'] / details['memory_total']) * 100 if details['memory_total'] > 0 else 0,
                            label=f"{details['memory_used']} MB / {details['memory_total']} MB"
                        ),
                        cls=str(m.b(3))
                    ),

                    # Temperature (if available)
                    Label(
                        P("Temperature", cls=combine_classes(font_size.xs, text_dui.base_content)),
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
                        P("Power", cls=combine_classes(font_size.xs, text_dui.base_content)),
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
                            cls=combine_classes(font_size.xs, text_dui.base_content)
                        ) if details.get('fan_speed') is not None else None,

                        # Encoder/Decoder utilization
                        Span(
                            f"Enc: {details.get('encoder_utilization', 0)}%",
                            cls=combine_classes(font_size.xs, text_dui.base_content, m.l(3))
                        ) if details.get('encoder_utilization') is not None else None,

                        Span(
                            f"Dec: {details.get('decoder_utilization', 0)}%",
                            cls=combine_classes(font_size.xs, text_dui.base_content, m.l(3))
                        ) if details.get('decoder_utilization') is not None else None,

                        # Process count
                        Span(
                            f"Processes: {details.get('compute_processes', 0)}",
                            cls=combine_classes(font_size.xs, text_dui.base_content, m.l(3))
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
                            Th("PID", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content)),
                            Th("Process", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content)),
                            Th("GPU Memory", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content)),
                            Th("GPU Usage", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content)),
                            Th("Device", cls=combine_classes(font_size.xs, font_weight.medium, text_dui.base_content)),
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(str(proc['pid']), cls=combine_classes(font_size.xs, text_dui.base_content)),
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
                                cls=combine_classes(font_size.xs, text_dui.base_content)
                            ),
                        ) for proc in sorted(gpu_info.get('processes', []), key=lambda x: x['gpu_memory_mb'], reverse=True)[:10]],  # Show top 10
                        cls=""
                    ),
                    cls=combine_classes(table, table_sizes.xs, w.full)
                ),
                cls=combine_classes("overflow-x-auto", bg_dui.base_200, rounded.lg, p(2))
            ) if gpu_info.get('processes') else Div(
                P("No active GPU processes", cls=combine_classes(font_size.sm, text_dui.base_content, text_align.center, p(4))),
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
                            Span(sensor['label'], cls=combine_classes(font_size.xs, text_dui.base_content)),
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