# Job Queue with SSE Status Page Example - Cross-Tab Synchronized

> Demonstrates a real-time job queue management system with cancellable background jobs, live progress tracking via Server-Sent Events (SSE), granular UI updates using HTMX SSE extension with out-of-band swaps, and **cross-tab synchronization** that keeps all browser tabs in sync.

## Key Features:
- **Cross-Tab Synchronization**: All browser tabs stay synchronized via global SSE broadcasting
- **Job Running Check**: Prevents multiple concurrent jobs unless explicitly allowed
- **Client-Side Protection**: Double-submit protection on form submission
- **Real-time Updates**: Live progress bars and status badges via SSE
- **Connection Status Indicator**: Shows real-time connection status
- **Automatic Reconnection**: Handles tab visibility changes and reconnects SSE when needed
- **Broadcast Architecture**: Server broadcasts updates to all connected clients when actions occur


```python
from fasthtml.common import *
from fasthtml.common import sse_message
import uuid, time, threading
from datetime import datetime
from typing import Dict, Any
import asyncio
import random
import json

from cjm_tqdm_capture.progress_monitor import ProgressMonitor
from cjm_tqdm_capture.job_runner import JobRunner
from cjm_tqdm_capture.streaming import sse_stream_async
```


```python
# For Jupyter display
from fasthtml.jupyter import JupyUvi, HTMX
from cjm_fasthtml_daisyui.core.testing import create_test_app, create_test_page, start_test_server
from cjm_fasthtml_daisyui.core.themes import DaisyUITheme
from IPython.display import display

# Import DaisyUI factories
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes, btn_behaviors
from cjm_fasthtml_daisyui.components.actions.modal import modal, modal_box, modal_action
from cjm_fasthtml_daisyui.components.feedback.progress import progress, progress_colors
from cjm_fasthtml_daisyui.components.feedback.alert import alert, alert_colors
from cjm_fasthtml_daisyui.components.data_display.card import card
from cjm_fasthtml_daisyui.components.data_display.table import table, table_modifiers
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.stat import stat, stat_title, stat_value, stats
from cjm_fasthtml_daisyui.components.data_display.status import status, status_colors, status_sizes
from cjm_fasthtml_daisyui.components.data_input.text_input import text_input
from cjm_fasthtml_daisyui.components.data_input.select import select
from cjm_fasthtml_daisyui.components.data_input.checkbox import checkbox, checkbox_sizes
from cjm_fasthtml_daisyui.components.data_input.label import label, floating_label
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui

# Import Tailwind factories
from cjm_fasthtml_tailwind.utilities.spacing import p, m, space
from cjm_fasthtml_tailwind.utilities.typography import font_weight, font_size, text_color
from cjm_fasthtml_tailwind.utilities.sizing import w, max_w, max_h, container
from cjm_fasthtml_tailwind.utilities.layout import overflow, display_tw
from cjm_fasthtml_tailwind.utilities.borders import rounded
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import flex_display, gap
from cjm_fasthtml_tailwind.utilities.effects import shadow
from cjm_fasthtml_tailwind.core.base import combine_classes
```


```python
from cjm_fasthtml_sse.core import (
    SSEBroadcastManager
)
from cjm_fasthtml_sse.dispatcher import (
    SSEEvent,
    SSEEventDispatcher
)
from cjm_fasthtml_sse.helpers import (
    oob_swap,
    oob_element,
    sse_element,
    oob_update,
    cleanup_sse_on_unload,
    get_htmx_idx,
    insert_htmx_sse_ext
)
from cjm_fasthtml_sse.htmx import (
    HTMXSSEConnector
)
from cjm_fasthtml_sse.monitoring import (
    SSEMonitorConfig,
    create_sse_monitor
)
from cjm_fasthtml_sse.updater import (
    SSEElementUpdater
)
```


```python
# Create app
app, rt = create_test_app(theme=DaisyUITheme.BUSINESS)
app.hdrs.append(Link(rel='icon', type='image/svg+xml', href=f'https://api.dicebear.com/9.x/adventurer/svg?seed={random.random()}'))
insert_htmx_sse_ext(app.hdrs)

# Job metadata storage
job_metadata: Dict[str, Any] = {}
job_results: Dict[str, Any] = {}

# Initialize the SSE Broadcast Manager
sse_manager = SSEBroadcastManager(
    max_queue_size=100,
    history_size=50,
    default_timeout=0.1
)

# Initialize the HTMX SSE Connector
htmx_sse_connector = HTMXSSEConnector()
```


```python
# Initialize SSEElementUpdater, SSEEventDispatcher and register handlers
element_updater = SSEElementUpdater()
event_dispatcher = SSEEventDispatcher()

# Register namespaces for better organization
event_dispatcher.register_namespace("job")
event_dispatcher.register_namespace("queue")
event_dispatcher.register_namespace("ui")

# Add middleware to log all events (optional, for debugging)
@event_dispatcher.add_middleware
async def logging_middleware(event: SSEEvent, next_handler):
    if isinstance(event, SSEEvent):
        print(f"[Event] {event.full_type}: {event.data}")
    return await next_handler(event)

# Register handlers using the event dispatcher with namespace patterns
@event_dispatcher.on("job:created", priority=10)
def dispatch_job_created(event: SSEEvent):
    return element_updater.create_elements("job_created", event.data)

@event_dispatcher.on("job:cancelled", priority=10)
def dispatch_job_cancelled(event: SSEEvent):
    return element_updater.create_elements("job_cancelled", event.data)

@event_dispatcher.on("job:completed", priority=10)
def dispatch_job_completed(event: SSEEvent):
    return element_updater.create_elements("job_completed", event.data)

@event_dispatcher.on("queue:cleared", priority=10)
def dispatch_jobs_cleared(event: SSEEvent):
    return element_updater.create_elements("jobs_cleared", event.data)

@event_dispatcher.on("queue:refresh", priority=10)
def dispatch_queue_refresh(event: SSEEvent):
    return element_updater.create_elements("queue_refresh", event.data)

# Register element update handlers
@element_updater.register("job_created", priority=10)
def handle_job_created(data):
    elements = []
    # Update queue
    elements.append(oob_update(
        "job-queue",
        queue().children[-1] if queue().children else queue()
    ))
    # Disable submit button
    elements.append(render_submit_button(disabled=True, oob_swap=True))
    return elements

@element_updater.register("job_cancelled", priority=10)
def handle_job_cancelled(data):
    elements = []
    job_id = data.get("job_id")
    if job_id:
        snapshot = monitor.snapshot(job_id)
        meta = job_metadata.get(job_id, {})
        if snapshot:
            row = render_job_row(job_id, snapshot, meta)
            elements.append(oob_swap(row, swap_type="outerHTML"))
    
    # Re-enable submit button if no jobs running
    if not has_running_jobs():
        elements.append(render_submit_button(disabled=False, oob_swap=True))
    return elements

@element_updater.register("job_completed", priority=10)
def handle_job_completed(data):
    elements = []
    job_id = data.get("job_id")
    if job_id:
        snapshot = monitor.snapshot(job_id)
        meta = job_metadata.get(job_id, {})
        if snapshot:
            row = render_job_row(job_id, snapshot, meta)
            elements.append(oob_swap(row, swap_type="outerHTML"))
    
    # Re-enable submit button if no jobs running
    if not has_running_jobs():
        elements.append(render_submit_button(disabled=False, oob_swap=True))
    return elements

@element_updater.register("jobs_cleared", priority=10)
def handle_jobs_cleared(data):
    elements = []
    # Refresh entire queue
    queue_content = queue().children[-1] if queue().children else P("No jobs in queue", cls=str(text_color.gray(500)))
    elements.append(oob_update("job-queue", queue_content))
    # Enable submit button
    elements.append(render_submit_button(disabled=False, oob_swap=True))
    return elements

@element_updater.register("queue_refresh", priority=10)
def handle_queue_refresh(data):
    elements = []
    # Full queue refresh
    queue_content = queue().children[-1] if queue().children else queue()
    elements.append(oob_update("job-queue", queue_content))
    # Update button state
    elements.append(render_submit_button(disabled=has_running_jobs(), oob_swap=True))
    return elements

# Add postprocessor to always include stats updates
element_updater.add_postprocessor(lambda elements: elements + render_stats_updates())

# Enhanced broadcast function that uses event dispatcher
async def broadcast_update(update_type: str, data: Dict[str, Any], namespace: str = None):
    """
    Broadcast an update to all connected SSE clients using the event system.
    
    Args:
        update_type: Type of update (created, cancelled, cleared, etc.)
        data: Update data to send
        namespace: Optional namespace for the event
    """
    # Determine namespace from update_type if not provided
    if not namespace:
        if update_type.startswith("job"):
            namespace = "job"
            update_type = update_type.replace("job_", "").replace("job", "")
        elif update_type.startswith("queue"):
            namespace = "queue"
            update_type = update_type.replace("queue_", "").replace("queue", "")
        elif update_type == "jobs_cleared":
            namespace = "queue"
            update_type = "cleared"
    
    # Create SSE event
    event = SSEEvent(
        type=update_type,
        data=data,
        namespace=namespace,
        timestamp=datetime.now().isoformat()
    )
    
    # Broadcast via SSEBroadcastManager
    return await sse_manager.broadcast(event.full_type, data)

# Function to create broadcast elements using the event dispatcher
async def create_broadcast_elements(update_type: str, data: Dict[str, Any]):
    """
    Create HTML elements for broadcast updates using the event dispatcher.
    
    Args:
        update_type: Type of update
        data: Update data
        
    Returns:
        Div containing all OOB swap elements
    """
    # Parse namespace from update_type
    namespace = None
    event_type = update_type
    
    if ":" in update_type:
        namespace, event_type = update_type.split(":", 1)
    elif update_type.startswith("job"):
        namespace = "job"
        event_type = update_type.replace("job_", "").replace("job", "")
    elif update_type.startswith("queue"):
        namespace = "queue"
        event_type = update_type.replace("queue_", "").replace("queue", "")
    elif update_type == "jobs_cleared":
        namespace = "queue"
        event_type = "cleared"
    
    # Create event
    event = SSEEvent(
        type=event_type,
        data=data,
        namespace=namespace,
        timestamp=datetime.now().isoformat()
    )
    
    # Dispatch through event system
    results = await event_dispatcher.dispatch(event)
    
    # Flatten results (handlers return lists of elements)
    elements = []
    for result in results:
        if isinstance(result, list):
            elements.extend(result)
        elif result:
            elements.append(result)
    
    return Div(*elements) if elements else Div()
```


```python
# Cancellable job runner extension
class CancellableJobRunner(JobRunner):
    def __init__(self, monitor):
        super().__init__(monitor)
        self._stop_events = {}
    
    def start_cancellable(self, job_id, fn, *args, patch_kwargs=None, **kwargs):
        stop_event = threading.Event()
        self._stop_events[job_id] = stop_event
        
        def wrapper():
            try:
                result = fn(stop_event, *args, **kwargs)
                job_results[job_id] = {"status": "success", "data": result}
            except Exception as e:
                job_results[job_id] = {"status": "error", "error": str(e)}
            finally:
                # Clean up stop event when job finishes
                if job_id in self._stop_events:
                    del self._stop_events[job_id]
        
        return self.start(job_id, wrapper, patch_kwargs=patch_kwargs)
    
    def cancel(self, job_id):
        if job_id in self._stop_events:
            # Set the stop event to signal the job to stop
            self._stop_events[job_id].set()
            
            # Mark job as cancelled in metadata
            if job_id in job_metadata:
                job_metadata[job_id]["status"] = "cancelled"
            
            # Mark job as cancelled in results
            job_results[job_id] = {"status": "cancelled"}
            
            # Force mark as completed in monitor so it can be cleared
            snapshot = monitor.snapshot(job_id)
            if snapshot:
                # Update the monitor's internal state to mark as completed
                monitor._jobs[job_id]['completed'] = True
                monitor._jobs[job_id]['overall_progress'] = snapshot['overall_progress']
            
            return True
        return False
```


```python
# Initialize with history for job tracking
monitor = ProgressMonitor(keep_history=True, history_limit=200)
# Use cancellable runner
runner = CancellableJobRunner(monitor)
```


```python
# Helper functions for reducing code duplication

# Job status management
def get_job_status(job_id, job_snapshot=None, metadata=None):
    """
    Determine job status consistently across the application.
    Returns: (status_text, status_color, is_running)
    """
    if metadata is None:
        metadata = job_metadata.get(job_id, {})
    
    if metadata.get('status') == 'cancelled':
        return "Cancelled", badge_colors.error, False
    elif job_snapshot and job_snapshot['completed']:
        return "Complete", badge_colors.success, False
    else:
        return "Running", badge_colors.info, True

def has_running_jobs(exclude_job_id=None):
    """Check if any jobs are currently running (excluding specified job)"""
    all_jobs = monitor.all()
    return any(
        not job['completed'] and 
        job_metadata.get(jid, {}).get('status') != 'cancelled'
        for jid, job in all_jobs.items() 
        if jid != exclude_job_id
    )

def get_submit_button_state(exclude_job_id=None):
    """Determine if submit button should be disabled"""
    return has_running_jobs(exclude_job_id)

# Element ID generation
def job_element_id(element_type, job_id, suffix=""):
    """Generate consistent element IDs for job-related elements"""
    base_id = f"{element_type}-{job_id}"
    return f"{base_id}-{suffix}" if suffix else base_id

# Progress bar rendering helpers
def render_progress_oob(job_id, value, close_sse=True):
    """Render progress bar with optional OOB swap for SSE closing"""
    return Span(
        render_progress_bar(value, color=progress_colors.primary, width=w(20)),
        id=job_element_id("progress-span", job_id),
        hx_swap_oob="true" if close_sse else None
    )

def render_status_oob(job_id, status_text, status_color, close_sse=True):
    """Render status badge with optional OOB swap"""
    return Span(
        render_status_badge(status_text, status_color),
        id=job_element_id("status-span", job_id),
        hx_swap_oob="true" if close_sse else None
    )

def render_actions_oob(job_id, include_cancel=False):
    """Render action buttons with OOB swap"""
    buttons = [render_view_button(job_id)]
    if include_cancel:
        buttons.append(render_cancel_button(job_id))
    
    return Span(
        *buttons,
        id=job_element_id("actions-span", job_id),
        hx_swap_oob="true"
    )

# UI helper functions
def render_submit_button(disabled=False, oob_swap=False):
    """Render submit button with appropriate state"""
    btn_classes = combine_classes(
        btn,
        btn_colors.primary,
        btn_behaviors.disabled if disabled else ""
    )
    
    kwargs = {
        'type': 'submit',
        'id': 'submit-job-btn',
        'cls': btn_classes,
        'disabled': disabled
    }
    
    if oob_swap:
        kwargs['hx_swap_oob'] = 'true'
    
    return Button("Submit Job", **kwargs)
```


```python
# Job details content building
def build_job_details_content(job_id, snapshot, meta, result, include_sse=False):
    """Build the complete job details content (reusable for static and SSE)"""
    if not snapshot:
        return Div("Job not found", cls=combine_classes(alert, alert_colors.error))
    
    # Build progress bars dynamically
    bars = []
    for bar_id, bar in snapshot['bars'].items():
        bars.append(
            Div(
                P(f"{bar.description}: {bar.progress:.1f}% ({bar.current}/{bar.total})",
                  cls=str(font_size.sm)),
                render_progress_bar(bar.progress, color=progress_colors.accent, width=w.full),
                cls=str(m.b(3))
            )
        )
    
    content = Div(
        # Job info
        Div(
            P(f"ID: {job_id}", cls=combine_classes(font_size.xs, text_color.gray(500))),
            P(f"Name: {meta.get('name', 'Unknown')}", cls=str(font_weight.semibold)),
            P(f"Type: {meta.get('type', 'unknown').title()}"),
            P(f"Created: {meta.get('created_at', 'Unknown')}", cls=str(font_size.sm)),
            cls=str(m.b(4))
        ),
        
        # Overall progress
        Div(
            P(f"Overall Progress: {snapshot['overall_progress']:.1f}%",
              cls=combine_classes(font_weight.bold, m.b(2))),
            render_progress_bar(snapshot['overall_progress'], color=progress_colors.primary, width=w.full),
            cls=str(m.b(4))
        ),
        
        # Individual bars
        Div(
            H4("Task Progress:", cls=combine_classes(font_weight.semibold, m.b(2))),
            *bars
        ) if bars else "",
        
        # Results if available
        Div(
            H4("Results:", cls=combine_classes(font_weight.semibold, m.b(2))),
            Pre(
                json.dumps(result, indent=2),
                cls=combine_classes(
                    bg_dui.base_300, p(3), rounded(),
                    font_size.xs, overflow.auto, max_h(40)
                )
            ),
            cls=str(m.t(4))
        ) if result else "",
        
        # History if available
        Div(
            H4("History:", cls=combine_classes(font_weight.semibold, m.b(2))),
            P(f"{len(snapshot.get('history', []))} updates recorded", cls=str(font_size.sm)),
            cls=str(m.t(4))
        ) if snapshot.get('history') else "",
        
        id="job-details-inner"
    )
    
    # Add SSE connection if requested and job is still running
    if include_sse:
        status_text, _, is_running = get_job_status(job_id, snapshot, meta)
        if is_running:
            # Use HTMXSSEConnector to add SSE attributes
            htmx_sse_connector.add_sse_attrs(
                content,
                endpoint=f"/stream_job_details?job_id={job_id}",
                swap_type="message"
            )
    
    return content
```


```python
def render_view_button(job_id):
    """Render view button for job details"""
    return Button(
        "View",
        hx_get=f"/job_details?job_id={job_id}",
        hx_target="#job-details-content",
        hx_swap="innerHTML",
        onclick="document.getElementById('job-modal').showModal()",
        cls=combine_classes(btn, btn_sizes.xs, btn_colors.primary)
    )
```


```python
def render_cancel_button(job_id):
    """Render a cancel button for a job"""
    return Button(
        "Cancel",
        hx_post=f"/cancel_job?job_id={job_id}",
        hx_target="body",
        hx_swap="none",
        cls=combine_classes(btn, btn_sizes.xs, btn_colors.error, m.l(1)),
        id=f"cancel-btn-{job_id}"
    )
```


```python
def render_progress_bar(value, max_value="100", color=None, width=None):
    """Render a progress bar element"""
    classes = [progress]
    if color:
        classes.append(color)
    if width:
        classes.append(width)
    
    return Progress(
        value=str(value),
        max=max_value,
        cls=combine_classes(*classes)
    )
```


```python
def render_status_badge(text, color):
    """Render a status badge"""
    return Span(
        text,
        cls=combine_classes(badge, color)
    )
```


```python
def render_section_header(text):
    """Render a section header (H2)"""
    return H2(text, cls=combine_classes(font_size.xl, font_weight.semibold, m.b(4)))
```


```python
def render_card_container(*children, extra_classes=None):
    """Render a card container"""
    classes = [card, bg_dui.base_200, p(6), m.b(6)]
    if extra_classes:
        classes.extend(extra_classes if isinstance(extra_classes, list) else [extra_classes])
    
    return Div(*children, cls=combine_classes(*classes))

def render_stats_updates():
    """Render statistics updates as OOB swaps"""
    jobs = monitor.all()
    
    # Calculate current stats
    total = len(jobs)
    running = sum(
        1 for job_id, job in jobs.items()
        if not job['completed'] and job_metadata.get(job_id, {}).get('status') != 'cancelled'
    )
    completed = sum(
        1 for job_id, job in jobs.items()
        if job['completed'] and job_metadata.get(job_id, {}).get('status') != 'cancelled'
    )
    cancelled = sum(
        1 for job_id in job_metadata
        if job_metadata[job_id].get('status') == 'cancelled'
    )
    
    # Return OOB swap elements for all stats
    return [
        Div(str(total), id="stat-total", hx_swap_oob="true", cls=str(stat_value)),
        Div(str(running), id="stat-running", hx_swap_oob="true", cls=combine_classes(stat_value, text_dui.primary)),
        Div(str(completed), id="stat-completed", hx_swap_oob="true", cls=combine_classes(stat_value, text_dui.success)),
        Div(str(cancelled), id="stat-cancelled", hx_swap_oob="true", cls=combine_classes(stat_value, text_dui.error))
    ]
```


```python
# SSE connection monitoring helpers using HTMXSSEConnector
def create_connection_status_indicators():
    """Create status indicator elements for different connection states"""
    return {
        'active': Span(
            Span(cls=combine_classes(status, status_colors.success, status_sizes.md, m.r(2))),
            Span("Real-time updates active", cls=combine_classes(text_dui.success))
        ),
        'disconnected': Span(
            Span(cls=combine_classes(status, status_colors.warning, status_sizes.md, m.r(2))),
            Span("Real-time updates disconnected", cls=combine_classes(text_dui.error))
        ),
        'error': Span(
            Span(cls=combine_classes(status, status_colors.error, status_sizes.md, m.r(2))),
            Span("Connection error - retrying...", cls=combine_classes(text_dui.warning))
        ),
        'reconnecting': Span(
            Span(cls=combine_classes(status, status_colors.info, status_sizes.md, m.r(2))),
            Span("Reconnecting...", cls=combine_classes(text_dui.info))
        )
    }

def render_sse_connection_monitor(
    sse_element_id="global-sse-connection",
    status_element_id="connection-status",
    auto_reconnect_on_visibility=True,
    debug_logging=True
):
    """
    Create a Script element that monitors SSE connection status using HTMXSSEConnector.
    
    Args:
        sse_element_id: ID of the SSE connection element to monitor
        status_element_id: ID of the element to update with connection status
        auto_reconnect_on_visibility: Whether to reconnect when tab becomes visible
        debug_logging: Whether to log connection events to console
        
    Returns:
        Script element with connection monitoring code
    """
    # Get the status indicators as HTML strings
    indicators = create_connection_status_indicators()
    
    # Convert indicators to HTML strings for JavaScript
    status_indicator_html = {
        'active': str(indicators['active']),
        'disconnected': str(indicators['disconnected']),
        'error': str(indicators['error']),
        'reconnecting': str(indicators['reconnecting'])
    }
    
    # Use HTMXSSEConnector to create the monitoring script
    return htmx_sse_connector.create_sse_monitor_script({
        'sse_element_id': sse_element_id,
        'status_element_id': status_element_id,
        'auto_reconnect': auto_reconnect_on_visibility,
        'debug': debug_logging,
        'status_indicators': status_indicator_html
    })

def render_global_sse_connection(
    endpoint="/stream_global_updates",
    element_id="global-sse-connection",
    hidden=True
):
    """
    Create the global SSE connection element using HTMXSSEConnector.
    
    Args:
        endpoint: The SSE endpoint to connect to
        element_id: ID for the connection element
        hidden: Whether to hide the element
        
    Returns:
        Div element configured for SSE connection
    """
    return htmx_sse_connector.create_sse_element(
        element_type=Div,
        endpoint=endpoint,
        element_id=element_id,
        hidden=hidden
    )

def render_connection_status_display(
    initial_connections=0,
    element_id="connection-status",
    show_count=True
):
    """
    Create the connection status display element.
    
    Args:
        initial_connections: Initial number of connected tabs
        element_id: ID for the status element
        show_count: Whether to show the connection count
        
    Returns:
        Div element for displaying connection status
    """
    indicators = create_connection_status_indicators()
    
    content = [indicators['active']]
    
    if show_count:
        content.append(
            Span(
                f" ({initial_connections} tabs connected)",
                cls=str(font_size.xs)
            )
        )
    
    return Div(
        *content,
        cls=combine_classes(text_dui.success, m.b(4)),
        id=element_id
    )
```


```python
def render_job_row(job_id, job, meta):
    """Render a complete job row with SSE streaming for active jobs using HTMXSSEConnector"""
    
    # Use centralized status determination
    status_text, status_color, is_running = get_job_status(job_id, job, meta)
    
    if is_running:
        # Active job - use SSE for real-time updates with HTMXSSEConnector
        return Tr(
            Td(job_id[:8] + "...", id=job_element_id("job-id", job_id)),
            Td(meta.get('name', 'Unknown'), id=job_element_id("job-name", job_id)),
            Td(meta.get('type', 'unknown').title(), id=job_element_id("job-type", job_id)),
            Td(
                htmx_sse_connector.sse_progress_element(
                    job_id,
                    initial_content=render_progress_bar(job['overall_progress'], color=progress_colors.primary, width=w(20))
                ),
                id=job_element_id("job-progress", job_id)
            ),
            Td(
                htmx_sse_connector.sse_status_element(
                    job_id,
                    initial_content=render_status_badge(status_text, status_color)
                ),
                id=job_element_id("job-status", job_id)
            ),
            Td(
                Span(
                    render_view_button(job_id),
                    render_cancel_button(job_id),
                    id=job_element_id("actions-span", job_id)
                ),
                id=job_element_id("job-actions", job_id)
            ),
            id=job_element_id("job-row", job_id)
        )
    else:
        # Completed/cancelled job - static display
        return Tr(
            Td(job_id[:8] + "...", id=job_element_id("job-id", job_id)),
            Td(meta.get('name', 'Unknown'), id=job_element_id("job-name", job_id)),
            Td(meta.get('type', 'unknown').title(), id=job_element_id("job-type", job_id)),
            Td(
                render_progress_bar(job['overall_progress'], color=progress_colors.primary, width=w(20)),
                id=job_element_id("job-progress", job_id)
            ),
            Td(
                render_status_badge(status_text, status_color),
                id=job_element_id("job-status", job_id)
            ),
            Td(
                Span(
                    render_view_button(job_id),
                    id=job_element_id("actions-span", job_id)
                ),
                id=job_element_id("job-actions", job_id)
            ),
            id=job_element_id("job-row", job_id)
        )
```


```python
# Various job types
def batch_processing_job(stop_event, batch_size=1000, delay=0.01):
    from tqdm import tqdm
    import time
    
    results = []
    
    # Process in batches
    for batch in range(3):
        desc = f"Batch {batch + 1}/3"
        for i in tqdm(range(batch_size), desc=desc):
            if stop_event.is_set():
                return {"status": "cancelled", "processed": results}
            time.sleep(delay)
            results.append(f"item_{batch}_{i}")
    
    return {"status": "complete", "processed": results}
```


```python
def data_export_job(stop_event, format_type="csv", records=200):
    from tqdm import tqdm
    import time
    
    # Fetch data
    for _ in tqdm(range(records // 2), desc="Fetching data"):
        if stop_event.is_set():
            return {"status": "cancelled"}
        time.sleep(0.01)
    
    # Format data
    for _ in tqdm(range(records // 4), desc=f"Formatting as {format_type}"):
        if stop_event.is_set():
            return {"status": "cancelled"}
        time.sleep(0.02)
    
    # Write to file
    for _ in tqdm(range(records // 4), desc="Writing to file"):
        if stop_event.is_set():
            return {"status": "cancelled"}
        time.sleep(0.01)
    
    return {"status": "complete", "file": f"export_{format_type}_{records}.{format_type}"}
```


```python
def model_training_job(stop_event, epochs=10, batch_size=32):
    from tqdm import tqdm
    import time
    import random
    
    metrics = []
    
    for epoch in range(epochs):
        # Training
        for _ in tqdm(range(1000), desc=f"Epoch {epoch+1}/{epochs} - Training"):
            if stop_event.is_set():
                return {"status": "cancelled", "metrics": metrics}
            time.sleep(0.005)
        
        # Validation
        for _ in tqdm(range(200), desc=f"Epoch {epoch+1}/{epochs} - Validation"):
            if stop_event.is_set():
                return {"status": "cancelled", "metrics": metrics}
            time.sleep(0.01)
        
        # Record metrics
        metrics.append({
            "epoch": epoch + 1,
            "loss": random.uniform(0.1, 1.0),
            "accuracy": random.uniform(0.7, 0.99)
        })
    
    return {"status": "complete", "metrics": metrics}
```


```python
# Main page with SSE support and cross-tab synchronization
@rt("/")
def index():
    # Configure SSE monitoring
    monitor_config = SSEMonitorConfig(
        sse_element_id="global-sse-connection",
        status_element_id="connection-status",
        auto_reconnect=True,
        debug=True,  # Set to False in production
        status_indicators={
            'active': str(create_connection_status_indicators()['active']),
            'disconnected': str(create_connection_status_indicators()['disconnected']),
            'error': str(create_connection_status_indicators()['error']),
            'reconnecting': str(create_connection_status_indicators()['reconnecting'])
        }
    )
    
    return create_test_page(
        "Job Queue Manager - SSE with Cross-Tab Sync",
        Div(
            H1("Job Queue Management System (SSE + Cross-Tab Sync)", 
               cls=combine_classes(font_size._3xl, font_weight.bold, m.b(6))),
            
            # Global SSE connection for cross-tab synchronization
            render_global_sse_connection(
                endpoint="/stream_global_updates",
                element_id="global-sse-connection",
                hidden=True
            ),
            
            # Connection status indicator
            render_connection_status_display(
                initial_connections=sse_manager.connection_count,
                element_id="connection-status",
                show_count=True
            ),
            
            # Job creation panel
            render_card_container(
                render_section_header("Create New Job"),
                Form(
                    Select(
                        Option("Batch Processing", value="batch"),
                        Option("Data Export", value="export"),
                        Option("Model Training", value="training"),
                        name="type",
                        cls=combine_classes(select, w.full, m.b(3))
                    ),
                    Label(
                        Span("Job name"),
                        Input(
                            name="name",
                            type="text",
                            placeholder="Job name (optional)",
                            cls=combine_classes(text_input, w.full, m.b(3))
                        ),
                        cls=combine_classes(floating_label, w.full, m.b(3))
                    ),
                    # Checkbox for allowing concurrent jobs (optional)
                    Label(
                        Input(
                            type="checkbox",
                            name="allow_concurrent",
                            value="true",
                            cls=combine_classes(checkbox, checkbox_sizes.sm)
                        ),
                        " Allow concurrent jobs (override single job limit)",
                        cls=combine_classes(label, m.b(3), font_size.sm)
                    ),
                    Div(
                        render_submit_button(disabled=False),
                        Button(
                            "Clear Finished",
                            title="Clear completed and cancelled jobs",
                            hx_post="/clear_completed",
                            hx_target="#job-queue",
                            hx_swap="innerHTML",
                            cls=combine_classes(btn, btn_colors.warning, m.l(2))
                        ),
                        cls=combine_classes(flex_display, gap(2))
                    ),
                    hx_post="/create_job",
                    hx_target="#job-queue",
                    hx_swap="innerHTML",
                    hx_on_after_request="this.reset()",
                    # Client-side protection against double-submit
                    hx_on_before_request="""
                        // Disable submit button immediately on click
                        document.getElementById('submit-job-btn').disabled = true;
                        document.getElementById('submit-job-btn').classList.add('btn-disabled');
                        
                        // Re-enable after response (success or error)
                        htmx.on('htmx:afterRequest', function(evt) {
                            if (evt.detail.elt === evt.currentTarget) {
                                var btn = document.getElementById('submit-job-btn');
                                // Only re-enable if no jobs are running (server will send appropriate state)
                                // The server response will include the correct button state via OOB swap
                            }
                        });
                    """,
                ),
            ),
            
            # Statistics - no SSE connections, will be updated via OOB swaps
            Div(
                render_section_header("Queue Statistics"),
                Div(
                    Div(
                        Div("Total Jobs", cls=str(stat_title)),
                        Div(
                            "0",
                            id="stat-total",
                            cls=str(stat_value)
                        ),
                        cls=str(stat)
                    ),
                    Div(
                        Div("Running", cls=str(stat_title)),
                        Div(
                            "0",
                            id="stat-running",
                            cls=combine_classes(stat_value, text_dui.primary)
                        ),
                        cls=str(stat)
                    ),
                    Div(
                        Div("Completed", cls=str(stat_title)),
                        Div(
                            "0",
                            id="stat-completed",
                            cls=combine_classes(stat_value, text_dui.success)
                        ),
                        cls=str(stat)
                    ),
                    Div(
                        Div("Cancelled", cls=str(stat_title)),
                        Div(
                            "0",
                            id="stat-cancelled",
                            cls=combine_classes(stat_value, text_dui.error)
                        ),
                        cls=str(stat)
                    ),
                    id="queue-stats",
                    cls=combine_classes(stats, shadow(), w.full)
                ),
                cls=str(m.b(6))
            ),
            
            # Job queue table
            render_card_container(
                render_section_header("Job Queue"),
                Div(
                    hx_get="/queue",
                    hx_trigger="load",
                    hx_swap="innerHTML",
                    id="job-queue",
                    cls=str(overflow.x.auto)
                ),
            ),
            
            # Job details modal
            Dialog(
                Div(
                    H3("Job Details", cls=combine_classes(font_weight.bold, font_size.lg, m.b(4))),
                    Div(id="job-details-content"),
                    Div(
                        Button(
                            "Close",
                            onclick="this.closest('dialog').close()",
                            cls=combine_classes(btn, btn_sizes.sm)
                        ),
                        cls=str(modal_action)
                    ),
                    cls=combine_classes(modal_box, max_w._4xl)
                ),
                id="job-modal",
                cls=str(modal)
            ),
            
            # Use the configured SSE monitor
            create_sse_monitor(htmx_sse_connector, monitor_config),
            
            cls=combine_classes(container, m.x.auto, p(8))
        )
    )
```


```python
# API endpoints
@rt("/create_job")
async def create_job(request):
    form = await request.form()
    job_type = form.get('type', 'batch')
    job_name = form.get('name', '')
    allow_concurrent = form.get('allow_concurrent', 'false') == 'true'
    
    # Check if a job is already running (unless concurrent jobs are allowed)
    if not allow_concurrent and has_running_jobs():
        # Return warning message with current queue state
        return Div(
            Div(
                "A job is already running. Please wait for it to complete or cancel it.",
                cls=combine_classes(alert, alert_colors.warning, m.b(4))
            ),
            queue(),
            render_submit_button(disabled=True, oob_swap=True)
        )
    
    job_id = str(uuid.uuid4())
    
    # Select job function with appropriate parameters
    job_configs = {
        'batch': (batch_processing_job, {'batch_size': 50, 'delay': 0.005}),
        'export': (data_export_job, {'format_type': 'csv', 'records': 100}),
        'training': (model_training_job, {'epochs': 3, 'batch_size': 32})
    }
    
    job_fn, kwargs = job_configs.get(job_type, (batch_processing_job, {}))
    
    # Store metadata
    job_metadata[job_id] = {
        'id': job_id,
        'name': job_name or f"{job_type.title()} Job",
        'type': job_type,
        'status': 'running',
        'created_at': datetime.now().isoformat(),
        'params': kwargs
    }
    
    # Start job with appropriate throttling
    runner.start_cancellable(
        job_id,
        job_fn,
        **kwargs,
        patch_kwargs={
            "min_delta_pct": 5,
            "min_update_interval": 0.05,
            "emit_initial": True
        }
    )
    
    # Small delay to allow monitor to register the job
    await asyncio.sleep(0.1)
    
    # Broadcast the job creation to all connected clients with explicit namespace
    await broadcast_update("created", {
        "job_id": job_id,
        "name": job_metadata[job_id]['name'],
        "type": job_type
    }, namespace="job")
    
    # Return response for the initiating client
    # The broadcast will update other tabs
    queue_content = queue()
    button_update = render_submit_button(disabled=True, oob_swap=True)
    stats_updates = render_stats_updates()
    
    return Div(
        queue_content,
        button_update,
        *stats_updates
    )
```


```python
@rt("/queue")
def queue():
    jobs = monitor.all()
    
    if not jobs:
        button_update = render_submit_button(disabled=False, oob_swap=True)
        stats_updates = render_stats_updates()
        result = P("No jobs in queue", cls=str(text_color.gray(500)))
        return Div(button_update, *stats_updates, result)
    
    # Use centralized check for running jobs
    has_running = has_running_jobs()
    
    rows = []
    for job_id, job in jobs.items():
        meta = job_metadata.get(job_id, {})
        rows.append(render_job_row(job_id, job, meta))
    
    # Update button state using helper
    button_update = render_submit_button(disabled=has_running, oob_swap=True)
    
    # Get stats updates
    stats_updates = render_stats_updates()
    
    # Build the table
    table_content = Table(
        Thead(
            Tr(
                Th("ID"),
                Th("Name"),
                Th("Type"),
                Th("Progress"),
                Th("Status"),
                Th("Actions")
            )
        ),
        Tbody(*rows),
        cls=combine_classes(table, table_modifiers.zebra, w.full)
    )
    
    return Div(button_update, *stats_updates, table_content)
```


```python
# SSE streaming endpoints for job progress
@rt("/stream_job_progress")
def stream_job_progress(job_id: str):
    """SSE endpoint for streaming job progress bar updates"""
    
    async def progress_stream():
        try:
            # Check if job exists before starting stream
            snapshot = monitor.snapshot(job_id)
            meta = job_metadata.get(job_id, {})
            status_text, _, is_running = get_job_status(job_id, snapshot, meta)
            
            if not snapshot or not is_running:
                # Send final static progress bar
                progress_value = snapshot['overall_progress'] if snapshot else 0
                yield sse_message(render_progress_oob(job_id, progress_value, close_sse=True))
                return
            
            async for data in sse_stream_async(
                monitor,
                job_id,
                interval=0.5,
                heartbeat=30.0,
                wait_for_start=False,
                start_timeout=5.0
            ):
                if data.startswith('data: '):
                    try:
                        json_str = data[6:].strip()
                        if json_str and json_str != '{}':
                            progress_data = json.loads(json_str)
                            
                            # Check if job was cancelled
                            meta = job_metadata.get(job_id, {})
                            if meta.get('status') == 'cancelled':
                                # Send final progress and close SSE
                                yield sse_message(render_progress_oob(
                                    job_id, 
                                    progress_data.get('progress', 0), 
                                    close_sse=True
                                ))
                                break
                            
                            if progress_data.get('completed'):
                                # Send final progress bar with OOB swap to close SSE
                                yield sse_message(render_progress_oob(job_id, 100, close_sse=True))
                                break
                            else:
                                # Send progress update
                                progress_value = progress_data.get('progress', 0)
                                yield sse_message(
                                    render_progress_bar(progress_value, color=progress_colors.primary, width=w(20))
                                )
                    except json.JSONDecodeError:
                        pass
                elif data.startswith('event: end'):
                    # Job not found or error
                    yield sse_message(render_progress_oob(job_id, 0, close_sse=True))
                    break
                elif data.startswith(': '):
                    yield data  # Heartbeat
        except Exception as e:
            print(f"Error in progress stream for {job_id}: {e}")
            yield sse_message(render_progress_oob(job_id, 0, close_sse=True))
    
    return EventStream(progress_stream())
```


```python
@rt("/stream_job_status")
def stream_job_status(job_id: str):
    """SSE endpoint for streaming job status updates"""
    
    async def status_stream():
        try:
            # Check initial status
            snapshot = monitor.snapshot(job_id)
            meta = job_metadata.get(job_id, {})
            status_text, status_color, is_running = get_job_status(job_id, snapshot, meta)
            
            if not snapshot or not is_running:
                # Send final status
                stats_updates = render_stats_updates()
                yield sse_message(
                    Div(
                        render_status_oob(job_id, status_text, status_color, close_sse=True),
                        render_actions_oob(job_id, include_cancel=False),
                        *stats_updates
                    )
                )
                return
            
            async for data in sse_stream_async(
                monitor,
                job_id,
                interval=0.5,
                heartbeat=30.0,
                wait_for_start=False,
                start_timeout=5.0
            ):
                if data.startswith('data: '):
                    try:
                        json_str = data[6:].strip()
                        if json_str and json_str != '{}':
                            progress_data = json.loads(json_str)
                            
                            # Check if job was cancelled
                            meta = job_metadata.get(job_id, {})
                            if meta.get('status') == 'cancelled':
                                # Check if any other jobs are running for submit button state
                                button_disabled = has_running_jobs(exclude_job_id=job_id)
                                stats_updates = render_stats_updates()
                                
                                # Build the list of OOB elements
                                oob_elements = [
                                    render_status_oob(job_id, "Cancelled", badge_colors.error, close_sse=True),
                                    render_actions_oob(job_id, include_cancel=False),
                                    *stats_updates
                                ]
                                
                                # Add submit button update if no other jobs are running
                                if not button_disabled:
                                    oob_elements.append(render_submit_button(disabled=False, oob_swap=True))
                                
                                yield sse_message(Div(*oob_elements))
                                break
                            
                            if progress_data.get('completed'):
                                # Broadcast job completion to all clients with explicit namespace
                                await broadcast_update("completed", {
                                    "job_id": job_id,
                                    "name": meta.get('name', 'Unknown')
                                }, namespace="job")
                                
                                # Check if any other jobs are running
                                button_disabled = has_running_jobs(exclude_job_id=job_id)
                                stats_updates = render_stats_updates()
                                
                                # Build the list of OOB elements
                                oob_elements = [
                                    render_status_oob(job_id, "Complete", badge_colors.success, close_sse=True),
                                    render_actions_oob(job_id, include_cancel=False),
                                    *stats_updates
                                ]
                                
                                # Add submit button update if no other jobs are running
                                if not button_disabled:
                                    oob_elements.append(render_submit_button(disabled=False, oob_swap=True))
                                
                                yield sse_message(Div(*oob_elements))
                                break
                            else:
                                # Still running - send status update
                                yield sse_message(
                                    render_status_badge("Running", badge_colors.info)
                                )
                    except json.JSONDecodeError:
                        pass
                elif data.startswith('event: end'):
                    yield sse_message(render_status_oob(job_id, "Error", badge_colors.error, close_sse=True))
                    break
                elif data.startswith(': '):
                    yield data  # Heartbeat
        except Exception as e:
            print(f"Error in status stream for {job_id}: {e}")
            yield sse_message(render_status_oob(job_id, "Error", badge_colors.error, close_sse=True))
    
    return EventStream(status_stream())
```


```python
@rt("/cancel_job")
async def cancel_job(job_id: str):
    """Cancel a job and broadcast the update to all connected clients"""
    success = runner.cancel(job_id)
    
    if success:
        # Broadcast the cancellation to all connected clients with explicit namespace
        await broadcast_update("cancelled", {
            "job_id": job_id,
            "name": job_metadata.get(job_id, {}).get('name', 'Unknown')
        }, namespace="job")
        
        # Return empty response - the broadcast handles UI updates
        return ""
    else:
        print(f"[DEBUG cancel_job] Failed to cancel job {job_id[:8]}")
        return Div(
            "Failed to cancel job",
            cls=combine_classes(alert, alert_colors.error),
            hx_swap_oob="true"
        )
```


```python
@rt("/job_details")
def job_details(job_id: str):
    """Job details with SSE auto-refresh while running"""
    snapshot = monitor.snapshot(job_id)
    meta = job_metadata.get(job_id, {})
    result = job_results.get(job_id)
    
    # Use the new centralized helper with SSE support
    return build_job_details_content(job_id, snapshot, meta, result, include_sse=True)
```


```python
@rt("/stream_job_details")
def stream_job_details(job_id: str):
    """SSE endpoint for streaming job details updates"""
    
    async def details_stream():
        try:
            while True:
                snapshot = monitor.snapshot(job_id)
                meta = job_metadata.get(job_id, {})
                status_text, _, is_running = get_job_status(job_id, snapshot, meta)
                
                if not snapshot or not is_running:
                    # Send final update and close
                    result = job_results.get(job_id)
                    
                    # Build final content using the helper, but with OOB swap
                    final_content = build_job_details_content(job_id, snapshot, meta, result, include_sse=False)
                    final_content.attrs['hx-swap-oob'] = 'true'
                    
                    yield sse_message(final_content)
                    break
                
                # Send update using the helper
                yield sse_message(build_job_details_content(job_id, snapshot, meta, job_results.get(job_id), include_sse=False))
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"Error in job details stream for {job_id}: {e}")
    
    return EventStream(details_stream())
```


```python
@rt("/clear_completed")
async def clear_completed():
    """Clear completed and cancelled jobs, broadcast to all clients"""
    # Get all jobs before clearing
    all_jobs = monitor.all()
    cleared_jobs = []
    
    # Clear completed jobs from monitor
    monitor.clear_completed(older_than_seconds=0)
    
    # Also manually remove cancelled jobs
    for job_id in list(all_jobs.keys()):
        meta = job_metadata.get(job_id, {})
        job = all_jobs.get(job_id, {})
        
        # Use helper to determine status
        status_text, _, is_running = get_job_status(job_id, job, meta)
        
        # Remove if not running (completed or cancelled)
        if not is_running:
            cleared_jobs.append({
                "job_id": job_id,
                "name": meta.get('name', 'Unknown')
            })
            
            # Remove from monitor if still there
            if job_id in monitor._jobs:
                del monitor._jobs[job_id]
            
            # Clean up metadata
            if job_id in job_metadata:
                del job_metadata[job_id]
            
            # Clean up results
            if job_id in job_results:
                del job_results[job_id]
    
    # Broadcast the clearing to all connected clients with explicit namespace
    await broadcast_update("cleared", {
        "cleared_count": len(cleared_jobs),
        "cleared_jobs": cleared_jobs
    }, namespace="queue")
    
    # Return updated queue for the initiating client
    queue_content = queue()
    stats_updates = render_stats_updates()
    
    return Div(
        queue_content,
        *stats_updates
    )
```


```python
# Global SSE endpoint for cross-tab synchronization
@rt("/stream_global_updates")
async def stream_global_updates():
    """
    SSE endpoint for broadcasting updates to all connected clients.
    This enables cross-tab synchronization of job queue state.
    """
    async def global_stream():
        # Register this connection with SSEBroadcastManager
        queue = await sse_manager.register_connection()
        
        try:
            # Send initial connection confirmation
            yield f": Connected to global updates (active connections: {sse_manager.connection_count})\n\n"
            
            # Send heartbeat and updates
            while True:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Create OOB elements based on message type using the event dispatcher
                    elements = await create_broadcast_elements(message["type"], message.get("data", {}))
                    
                    # Send as SSE message
                    yield sse_message(elements)
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat {datetime.now().isoformat()}\n\n"
                    
                except Exception as e:
                    print(f"Error in global stream: {e}")
                    break
                    
        finally:
            # Unregister this connection
            await sse_manager.unregister_connection(queue)
    
    return EventStream(global_stream())
```


```python
# Start server for Jupyter
server = start_test_server(app, port=8000)
display(HTMX(port=server.port))
```


```python
# Stop server when done
server.stop()
```


```python

```
