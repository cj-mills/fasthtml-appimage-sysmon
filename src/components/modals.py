"""
Modal components (settings, dialogs, etc.).
"""

from fasthtml.common import *

# DaisyUI imports
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes, btn_styles, btn_modifiers
from cjm_fasthtml_daisyui.components.actions.modal import modal, modal_box, modal_action
from cjm_fasthtml_daisyui.components.data_input.range_slider import range_dui, range_colors
from cjm_fasthtml_daisyui.components.data_input.label import label
from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui

# Tailwind imports
from cjm_fasthtml_tailwind.utilities.spacing import m
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import flex_display, gap, justify
from cjm_fasthtml_tailwind.utilities.sizing import w, max_w
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
from cjm_fasthtml_tailwind.utilities.layout import position, right, top
from cjm_fasthtml_tailwind.core.base import combine_classes

import config


def render_settings_modal():
    """Render the settings modal for configuring refresh intervals."""
    return Dialog(
        Div(
            # Close button at corner
            Form(
                Button(
                    "✕",
                    cls=combine_classes(
                        btn,
                        btn_sizes.sm,
                        btn_modifiers.circle,
                        btn_styles.ghost,
                        position.absolute,
                        right._2,
                        top._2
                    )
                ),
                method="dialog"
            ),
            H3("Refresh Interval Settings", cls=combine_classes(font_size.lg, font_weight.bold, m.b(4))),
            P("Adjust the refresh intervals for each component (in seconds)",
              cls=combine_classes(text_dui.base_content, font_size.sm, m.b(6))),

            # Settings form
            Div(
                # CPU interval
                Div(
                    Label(
                        Span("CPU", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['cpu']}s", id="cpu-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(config.REFRESH_INTERVALS['cpu']),
                        id="cpu-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('cpu-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Memory interval
                Div(
                    Label(
                        Span("Memory", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['memory']}s", id="memory-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(config.REFRESH_INTERVALS['memory']),
                        id="memory-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('memory-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Disk interval
                Div(
                    Label(
                        Span("Disk", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['disk']}s", id="disk-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="5",
                        max="60",
                        value=str(config.REFRESH_INTERVALS['disk']),
                        id="disk-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('disk-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Network interval
                Div(
                    Label(
                        Span("Network", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['network']}s", id="network-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(config.REFRESH_INTERVALS['network']),
                        id="network-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('network-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Process interval
                Div(
                    Label(
                        Span("Processes", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['process']}s", id="process-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="2",
                        max="60",
                        value=str(config.REFRESH_INTERVALS['process']),
                        id="process-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('process-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # GPU interval
                Div(
                    Label(
                        Span("GPU", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['gpu']}s", id="gpu-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="1",
                        max="30",
                        value=str(config.REFRESH_INTERVALS['gpu']),
                        id="gpu-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('gpu-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),

                # Temperature interval
                Div(
                    Label(
                        Span("Temperature", cls=combine_classes(font_weight.medium)),
                        Span(f"{config.REFRESH_INTERVALS['temperature']}s", id="temperature-interval-value",
                             cls=combine_classes(text_dui.primary, font_weight.medium)),
                        cls=combine_classes(label, flex_display, justify.between, m.b(2))
                    ),
                    Input(
                        type="range",
                        min="2",
                        max="60",
                        value=str(config.REFRESH_INTERVALS['temperature']),
                        id="temperature-interval",
                        cls=combine_classes(range_dui, range_colors.primary, w.full),
                        oninput="document.getElementById('temperature-interval-value').textContent = this.value + 's'"
                    ),
                    cls=str(m.b(4))
                ),
                cls=str(m.b(6))
            ),

            # Action buttons
            Div(
                Button(
                    "Apply",
                    cls=combine_classes(btn, btn_colors.primary),
                    hx_post="/update_intervals",
                    hx_vals="js:{cpu: document.getElementById('cpu-interval').value, memory: document.getElementById('memory-interval').value, disk: document.getElementById('disk-interval').value, network: document.getElementById('network-interval').value, process: document.getElementById('process-interval').value, gpu: document.getElementById('gpu-interval').value, temperature: document.getElementById('temperature-interval').value}",
                    hx_swap="none"
                ),
                Form(
                    Button("Cancel", cls=combine_classes(btn, btn_styles.ghost)),
                    method="dialog",
                    cls="inline"
                ),
                cls=combine_classes(modal_action, gap(2))
            ),
            cls=combine_classes(modal_box, w("11/12"), max_w._2xl)
        ),
        id="settings_modal",
        cls=str(modal)
    )