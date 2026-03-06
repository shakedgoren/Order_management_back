import json
import time
import threading
from queue import Queue, Empty
from django.http import StreamingHttpResponse

# Thread-safe list of connected SSE clients
_clients = []
_clients_lock = threading.Lock()


def broadcast_event(data: dict):
    """Send an event to all connected SSE clients."""
    message = json.dumps(data, ensure_ascii=False)
    with _clients_lock:
        for q in _clients:
            q.put(message)


def event_stream():
    """Generator that yields SSE events."""
    queue = Queue()
    with _clients_lock:
        _clients.append(queue)
    try:
        while True:
            try:
                message = queue.get(timeout=30)
                yield f"data: {message}\n\n"
            except Empty:
                # Send keepalive ping
                yield ": ping\n\n"
    except GeneratorExit:
        pass
    finally:
        with _clients_lock:
            if queue in _clients:
                _clients.remove(queue)


def sse_view(request):
    """Django view that streams SSE events."""
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
