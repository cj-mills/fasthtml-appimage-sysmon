"""
UI components for the System Monitor Dashboard.
"""

# Re-export commonly used components
from .common import render_stat_card, render_progress_bar
from .base import (
    render_process_count,
    render_process_status
)
from .tables import (
    render_cpu_processes_table,
    render_memory_processes_table
)

from .modals import (
    render_settings_modal
)
from .cards import (
    render_os_info_card,
    render_cpu_card,
    render_memory_card,
    render_disk_card,
    render_network_card,
    render_process_card,
    render_gpu_card,
    render_temperature_card

)


__all__ = [
    'render_stat_card', 
    'render_progress_bar',
    'render_process_count',
    'render_process_status',
    'render_temperature_card',
    'render_cpu_processes_table',
    'render_memory_processes_table',
    'render_settings_modal',
    'render_os_info_card',
    'render_cpu_card',
    'render_memory_card',
    'render_disk_card',
    'render_network_card',
    'render_process_card',
    'render_gpu_card',
    ]