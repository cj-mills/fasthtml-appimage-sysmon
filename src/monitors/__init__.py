"""
System monitoring modules for the System Monitor Dashboard.
"""

from .system import get_static_system_info
from .cpu import get_cpu_info
from .memory import get_memory_info
from .disk import get_disk_info
from .network import get_network_info
from .process import get_process_info
from .gpu import check_gpu
from .sensors import get_temperature_info

__all__ = [
    'get_static_system_info',
    'get_cpu_info',
    'get_memory_info',
    'get_disk_info',
    'get_network_info',
    'get_process_info',
    'check_gpu',
    'get_temperature_info'
]