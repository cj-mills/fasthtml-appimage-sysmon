"""
Common UI elements (progress bars, badges, stats, etc.).
"""

from fasthtml.common import Div, Span, Progress
from utils import get_progress_color

# DaisyUI imports
from cjm_fasthtml_daisyui.components.data_display.stat import stat, stat_title, stat_value, stat_desc
from cjm_fasthtml_daisyui.components.feedback.progress import progress
from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.spacing import m
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import justify
from cjm_fasthtml_tailwind.utilities.sizing import w
from cjm_fasthtml_tailwind.utilities.typography import font_size
from cjm_fasthtml_tailwind.core.base import combine_classes


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
            cls=combine_classes(justify.between, m.b(1), "flex")
        ) if label else None,
        Progress(
            value=str(value),
            max=str(max_value),
            cls=combine_classes(progress, color, w.full)
        )
    )