"""
Base component helpers and utilities.
"""

from fasthtml.common import *

# DaisyUI imports
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.spacing import m
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import flex_display, gap, flex
from cjm_fasthtml_tailwind.core.base import combine_classes

def render_process_count(total):
    """Render just the process count badge."""
    return Span(
        f"{total} processes",
        cls=combine_classes(badge, badge_colors.primary, badge_sizes.lg),
        id="process-count"
    )

def render_process_status(status_counts):
    """Render just the process status badges."""
    return Div(
        *[Span(
            f"{status}: {count}",
            cls=combine_classes(
                badge,
                badge_colors.info if status == 'running' else badge_colors.neutral,
                badge_sizes.sm,
                m.r(2)
            )
        ) for status, count in status_counts.items()],
        cls=combine_classes(flex_display, flex.wrap, gap(1), m.b(4)),
        id="process-status"
    )