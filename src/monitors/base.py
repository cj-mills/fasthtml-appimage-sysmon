"""
Base monitor class/interface for system monitors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseMonitor(ABC):
    """Base class for all system monitors."""

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get current monitoring information.

        Returns:
            Dict containing the current state information
        """
        pass

    @staticmethod
    def get_static_info() -> Dict[str, Any]:
        """Get static information that doesn't change during runtime.

        Returns:
            Dict containing static system information
        """
        return {}