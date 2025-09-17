"""
Table components for data visualization.
"""

from fasthtml.common import *

# DaisyUI imports
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.table import table, table_modifiers, table_sizes

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.sizing import w
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
from cjm_fasthtml_tailwind.core.base import combine_classes


def render_cpu_processes_table(top_cpu):
    """Render the CPU processes table."""
    return Div(
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
                ) for proc in top_cpu]
            ),
            cls=combine_classes(table, table_modifiers.zebra, table_sizes.xs, w.full)
        ),
        id="cpu-processes-table"
    )

def render_memory_processes_table(top_memory):
    """Render the memory processes table."""
    return Div(
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
                ) for proc in top_memory]
            ),
            cls=combine_classes(table, table_modifiers.zebra, table_sizes.xs, w.full)
        ),
        id="memory-processes-table"
    )