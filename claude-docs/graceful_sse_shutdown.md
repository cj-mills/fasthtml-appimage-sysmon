# Graceful SSE Shutdown in FastHTML Applications

> A robust pattern for properly closing Server-Sent Events (SSE) connections when a FastHTML/Uvicorn application shuts down, preventing client reconnection attempts and ensuring clean termination.

## Problem

When a FastHTML application with SSE connections shuts down (e.g., via Ctrl+C), clients typically:
- Continue trying to reconnect to the closed server
- Show connection errors in the browser console
- May not realize the server has intentionally shut down

## Solution Overview

This pattern combines server-side connection management with client-side JavaScript to:
1. Track all active SSE connections
2. Send shutdown notifications before the server exits
3. Remove SSE elements via out-of-band (OOB) swaps
4. Prevent client reconnection attempts

## Implementation

### 1. Server-Side Shutdown Handler

```python
from uvicorn.main import Server
from datetime import datetime
import asyncio
import time

# Store the original handler
original_handler = Server.handle_exit

# Initialize SSE Broadcast Manager (must be before the handler class)
sse_manager = SSEBroadcastManager(**config.SSE_CONFIG)

class SSEShutdownHandler:
    """Handles graceful SSE connection shutdown"""
    should_exit = False
    active_connections = set()
    shutdown_event = asyncio.Event()

    @staticmethod
    def handle_exit(*args, **kwargs):
        """Custom exit handler that notifies SSE clients before shutdown"""
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
            # This bypasses async issues during shutdown
            for queue in list(sse_manager.connections):
                try:
                    # Use put_nowait to avoid blocking
                    queue.put_nowait(shutdown_message)
                except asyncio.QueueFull:
                    print("Queue full, couldn't send shutdown message")
                except Exception as e:
                    print(f"Error sending shutdown to queue: {e}")

            print(f"Sent shutdown message to {len(sse_manager.connections)} connections")

            # Give connections time to process the messages
            time.sleep(1.0)

        except Exception as e:
            print(f"Error during shutdown broadcast: {e}")

        # Close any remaining active connections
        print(f"Closing {len(SSEShutdownHandler.active_connections)} active SSE connections...")
        for connection in list(SSEShutdownHandler.active_connections):
            try:
                connection.cancel()
            except Exception as e:
                print(f"Error closing connection: {e}")
        SSEShutdownHandler.active_connections.clear()

        # Call the original handler
        original_handler(*args, **kwargs)

# Replace the default handler
Server.handle_exit = SSEShutdownHandler.handle_exit
```

### 2. SSE Endpoint with Shutdown Handling

```python
@rt('/stream_updates')
async def stream_updates():
    """SSE endpoint with graceful shutdown support"""
    async def update_stream():
        # Track this connection
        current_task = asyncio.current_task()

        # Register with SSEBroadcastManager
        queue = await sse_manager.register_connection()

        # Track in shutdown handler
        SSEShutdownHandler.active_connections.add(current_task)

        try:
            # Send initial connection confirmation
            yield f": Connected to updates (active connections: {sse_manager.connection_count})\n\n"

            # Main message loop
            while not SSEShutdownHandler.should_exit:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Check for shutdown message
                    if message.get("type") == "shutdown":
                        print(f"Received shutdown message, closing SSE connection")

                        # Send OOB swap to remove the SSE element
                        # This prevents HTMX from trying to reconnect
                        close_element = Div(
                            id="sse-connection",
                            hx_swap_oob="true",
                            style="display: none;"
                        )
                        yield sse_message(close_element)

                        # Send close event for JavaScript handling
                        yield f"event: close\ndata: {json.dumps({'message': 'Server shutting down'})}\n\n"
                        break

                    # Handle normal updates
                    if message.get("type") == "system_update":
                        updates = message.get("data", {}).get("updates", [])
                        if updates:
                            yield sse_message(Div(*updates))

                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f": heartbeat {datetime.now().isoformat()}\n\n"

                except asyncio.CancelledError:
                    # Connection cancelled
                    print(f"SSE connection cancelled")
                    yield f"event: close\ndata: {json.dumps({'message': 'Connection cancelled'})}\n\n"
                    break

                except Exception as e:
                    print(f"Error in update stream: {e}")
                    break

            # Notify client if we exit due to shutdown
            if SSEShutdownHandler.should_exit:
                yield f"event: close\ndata: {json.dumps({'message': 'Server shutting down'})}\n\n"

        finally:
            # Cleanup
            await sse_manager.unregister_connection(queue)
            SSEShutdownHandler.active_connections.discard(current_task)

    return EventStream(update_stream())
```

### 3. Client-Side JavaScript Monitor

```javascript
// SSE Connection Monitor with Shutdown Handling
(function() {
    let reconnectAttempts = 0;
    let maxReconnectAttempts = 10;
    let reconnectDelay = 1000;
    let isShuttingDown = false;  // Prevents reconnection during shutdown
    let statusElement = document.getElementById('connection-status');
    let sseElement = document.getElementById('sse-connection');

    // Monitor HTMX SSE events
    document.body.addEventListener('htmx:sseError', function(evt) {
        if (evt.detail.elt === sseElement) {
            console.log('SSE connection error');

            // Don't try to reconnect if shutting down
            if (isShuttingDown) {
                console.log('Server is shutting down, not attempting reconnection');
                updateStatus('disconnected');
                return;
            }

            // Normal reconnection logic
            if (reconnectAttempts < maxReconnectAttempts) {
                setTimeout(function() {
                    reconnectAttempts++;
                    console.log('Attempting to reconnect... (attempt ' + reconnectAttempts + ')');
                    updateStatus('reconnecting');
                    htmx.trigger(sseElement, 'htmx:sseReconnect');
                }, reconnectDelay * Math.min(reconnectAttempts + 1, 5));
            } else {
                updateStatus('disconnected');
            }
        }
    });

    // Listen for server shutdown events
    document.body.addEventListener('htmx:sseMessage', function(evt) {
        if (evt.detail.elt === sseElement && evt.detail.event === 'close') {
            console.log('Server requested connection close:', evt.detail.data);
            isShuttingDown = true;  // Set flag to prevent reconnection
            updateStatus('disconnected');

            // Stop reconnection attempts
            reconnectAttempts = maxReconnectAttempts;

            // Close the EventSource
            if (sseElement._sseEventSource) {
                sseElement._sseEventSource.close();
                delete sseElement._sseEventSource;
            }
        }
    });

    // Listen for OOB swap removal of SSE element
    document.body.addEventListener('htmx:oobAfterSwap', function(evt) {
        if (evt.detail.target && evt.detail.target.id === 'sse-connection') {
            console.log('SSE element removed via OOB swap - server shutting down');
            isShuttingDown = true;
            updateStatus('disconnected');
        }
    });

    // Handle page visibility changes (don't reconnect if shutting down)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && sseElement && !isShuttingDown) {
            let evtSource = sseElement._sseEventSource;
            if (!evtSource || evtSource.readyState === EventSource.CLOSED) {
                console.log('Page became visible, reconnecting SSE...');
                updateStatus('reconnecting');
                htmx.trigger(sseElement, 'htmx:sseReconnect');
            }
        }
    });
})();
```

### 4. Background Tasks with Shutdown Check

```python
async def generate_system_updates():
    """Background task that respects shutdown signal"""
    while not SSEShutdownHandler.should_exit:
        try:
            # Generate and broadcast updates
            updates = await collect_updates()
            if updates:
                await sse_manager.broadcast("system_update", {"updates": updates})

            # Wait before next iteration
            await asyncio.sleep(1)

        except Exception as e:
            print(f"Error generating updates: {e}")
            await asyncio.sleep(1)
```

## Key Concepts

### Why Synchronous Queue Access?

During shutdown, the async event loop may be blocked or not processing tasks properly. Using `queue.put_nowait()` directly on the connection queues ensures messages are delivered immediately without relying on async execution.

### OOB Swap for Element Removal

Sending an out-of-band swap that replaces the SSE element with an empty div effectively removes HTMX's ability to reconnect:

```python
close_element = Div(
    id="sse-connection",
    hx_swap_oob="true",
    style="display: none;"
)
yield sse_message(close_element)
```

### Client-Side Shutdown Flag

The JavaScript `isShuttingDown` flag prevents all reconnection attempts once a shutdown is detected, including:
- Error-triggered reconnections
- Visibility change reconnections
- Manual reconnection attempts

## Usage Example

```python
from fasthtml.common import *
from cjm_fasthtml_sse.core import SSEBroadcastManager
import config

# Initialize SSE manager before shutdown handler
sse_manager = SSEBroadcastManager(**config.SSE_CONFIG)

# Set up shutdown handler
class SSEShutdownHandler:
    # ... (implementation as shown above)

Server.handle_exit = SSEShutdownHandler.handle_exit

# Create app
app, rt = fast_app()

# Add SSE endpoint with shutdown handling
@rt('/stream_updates')
async def stream_updates():
    # ... (implementation as shown above)

# HTML with SSE connection
@rt('/')
def index():
    return Div(
        # SSE connection element
        Div(
            id="sse-connection",
            hx_ext="sse",
            sse_connect="/stream_updates",
            sse_swap="message",
            style="display: none;"
        ),
        # Connection status display
        Div(id="connection-status"),
        # Include the JavaScript monitor
        Script(monitor_script)
    )
```

## Benefits

1. **Clean Shutdown**: Clients receive proper notification and stop reconnecting
2. **No Console Errors**: Prevents "connection failed" errors after shutdown
3. **User Feedback**: Status indicators show "Disconnected" instead of errors
4. **Reliable Delivery**: Synchronous message delivery works even during shutdown
5. **Complete Cleanup**: Both server and client resources are properly released

## Testing

To test the shutdown behavior:

1. Start the application
2. Open browser developer console
3. Press Ctrl+C to shutdown
4. Observe:
   - "Server requested connection close" in browser console
   - No reconnection attempts
   - Status changes to "Disconnected"
   - No error messages

## Notes

- The 1-second delay in `handle_exit` gives clients time to process shutdown messages
- The shutdown handler must be installed after initializing `sse_manager`
- All background tasks should check `SSEShutdownHandler.should_exit`
- Consider adjusting the delay based on your network conditions