"""List every draw / dispatch in a .wpix capture with its PIX event breadcrumb.

Usage:
    python list_draws.py path/to/capture.wpix
"""

import ctypes
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

os.add_dll_directory(os.path.join(THIS_DIR, "extern", "bin"))
sys.path.insert(0, os.path.join(THIS_DIR, "extern", "python"))

import Microsoft.Pix
import Microsoft.Pix.Api as Api


DRAW_DISPATCH_KEYWORDS = (
    "Draw",
    "Dispatch",
    "ExecuteIndirect",
)

QUEUE_TYPE_NAMES = {
    Api.PIX_QUEUE_TYPE_GRAPHICS: "GRAPHICS",
    Api.PIX_QUEUE_TYPE_COMPUTE: "COMPUTE",
    Api.PIX_QUEUE_TYPE_COPY: "COPY",
    Api.PIX_QUEUE_TYPE_GPU_OTHER: "GPU_OTHER",
    Api.PIX_QUEUE_TYPE_CPU: "CPU",
    Api.PIX_QUEUE_TYPE_SCHEDULER: "SCHEDULER",
    Api.PIX_QUEUE_TYPE_UNKNOWN: "UNKNOWN",
}


def is_draw_or_dispatch(event_info: Api.PIX_EVENT_INFO) -> bool:
    api_call = str(event_info.ApiCallData or "")
    if not api_call:
        return False
    return any(kw in api_call for kw in DRAW_DISPATCH_KEYWORDS)


def collect_events(queue_info: Api.IPixGpuCaptureQueueInfo) -> list[Api.PIX_EVENT_INFO]:
    count = queue_info.GetEventCount()
    events: list[Api.PIX_EVENT_INFO] = []
    for i in range(count):
        info = Api.PIX_EVENT_INFO()
        queue_info.GetEvent(i, ctypes.byref(info))
        events.append(info)
    return events


def build_breadcrumb(events: list[Api.PIX_EVENT_INFO], index: int) -> str:
    """Walk ParentIndex up to a root and return a '/'-joined path of names."""
    path: list[str] = []
    seen: set[int] = set()
    cur = index
    while True:
        if cur in seen or cur >= len(events):
            break
        seen.add(cur)
        ev = events[cur]
        name = str(ev.Name or "")
        if name:
            path.append(name)
        parent = int(ev.ParentIndex)
        # Root sentinels we might encounter: self-reference, 0xFFFFFFFF,
        # or parent == index 0 of a root we've already visited.
        if parent == cur or parent == 0xFFFFFFFF:
            break
        cur = parent
    path.reverse()
    return "/".join(path) if path else "<root>"


def process_capture(path: str) -> None:
    factory = Microsoft.Pix.PixCreateFactory()
    doc = factory.OpenGpuCaptureDocument(path)
    queues = doc.GetQueues()

    total = 0
    for q in range(queues.GetCount()):
        queue = queues.GetQueue(q)
        qtype = QUEUE_TYPE_NAMES.get(queue.GetType(), str(queue.GetType()))
        qname = str(queue.GetName() or "")
        print(f"\n=== Queue {q}: {qname!r} ({qtype}) ===")

        events = collect_events(queue)
        for i, ev in enumerate(events):
            if not is_draw_or_dispatch(ev):
                continue
            breadcrumb = build_breadcrumb(events, i)
            api_call = str(ev.ApiCallData or "")
            print(f"  [{i:6d}] {breadcrumb}  ::  {api_call}")
            total += 1

    print(f"\nTotal draw/dispatch events: {total}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    capture_path = sys.argv[1]
    if not os.path.exists(capture_path):
        print(f"Capture not found: {capture_path}")
        return 1
    process_capture(capture_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
