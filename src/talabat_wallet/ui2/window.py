from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static
from textual import events
from textual.message import Message


# ================= CLOSE BUTTON ================= #

class CloseButton(Static):
    """Custom close button - no Textual Button default blue focus border."""

    can_focus = False

    DEFAULT_CSS = """
    CloseButton {
        width: 3;
        height: 1;
        min-width: 3;
        max-width: 3;
        background: #c0392b;
        color: #ffffff;
        content-align: center middle;
        text-style: bold;
    }

    CloseButton:hover {
        background: #e53935;
        color: #ffffff;
    }
    """

    def __init__(self):
        super().__init__("✕", id="close_btn")

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        self.styles.background = "#8b0000"  # Dark Red
        self.styles.color = "#000000"       # Black X

    def on_mouse_up(self, event: events.MouseUp) -> None:
        event.stop()
        self.styles.background = "#c0392b"
        self.styles.color = "#ffffff"
        if isinstance(self.parent, WindowHeader):
            if isinstance(self.parent.parent, DraggableWindow):
                self.parent.parent.close()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()


def log_debug(message: str) -> None:
    """Helper to write debug logs to a file in the project root."""
    import os
    try:
        # Save to the root of the project (~/work) using an absolute path
        # This ensures it's created even if the relative CWD is weird.
        project_root = os.getcwd()
        if "src" in project_root:
            project_root = os.path.dirname(project_root.split("src")[0])
        
        log_path = os.path.join(project_root, "debug_touch.log")
        with open(log_path, "a", encoding="utf-8") as f:
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{ts}] {message}\n")
    except:
        pass

# ================= HEADER ================= #

class WindowHeader(Horizontal):

    DEFAULT_CSS = """
    WindowHeader {
        dock: top;
        width: 100%;
        height: 3; /* Increased for finger comfort */
        background: #1c2228; /* Unified Navy */
        color: #c9d1d9;
        layout: horizontal;
        padding: 0 1;
        margin: 0;
        border-bottom: solid #1a2030;
        content-align: left middle;
    }

    WindowHeader .window-title {
        width: 1fr;
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: #dce6f0;
    }
    """

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title

    def compose(self) -> ComposeResult:
        yield Static(self.title_text, classes="window-title")
        yield CloseButton()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        # Visual feedback for debugging
        self.styles.background = "#2a3441"
        log_debug(f"Header: mouse_down at {event.screen_x}, {event.screen_y}")

        # Check if hitting the close button area
        widget, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
        if widget and (widget.id == "close_btn" or isinstance(widget, CloseButton)):
            log_debug("Header: Close button detected area, ignoring drag")
            return

        event.stop()
        # event.prevent_default() # Removed to see if it helps Termux pass the move

        if isinstance(self.parent, DraggableWindow):
            log_debug("Header: Starting drag via Parent")
            self.parent.start_dragging(event)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        # Reset visual feedback
        self.styles.background = "#1c2228"
        log_debug(f"Header: mouse_up at {event.screen_x}, {event.screen_y}")


# ================= WINDOW ================= #

class DraggableWindow(Vertical):

    DEFAULT_CSS = """
    DraggableWindow {
        width: 60%;
        height: auto;
        max-height: 85vh;
        min-height: 15%;

        background: #1c2228; /* Unified Navy Background */
        /* External-feeling border - heavy and wrapping */
        border: heavy #1a2030;

        padding: 0;
        margin: 0;
        display: block;
        position: absolute;
        box-sizing: border-box;

        layer: overlay;
    }

    DraggableWindow:focus-within, DraggableWindow.is-dragging {
        border: heavy #00d2ff; /* Ultra-Radiant glowing cyan */
    }

    .window-content {
        width: 100%;
        max-height: 80vh;
        padding: 1;
        overflow-y: auto;
        background: transparent;
        /* Subtle sectional outlining (Takh-teet) */
        border: solid #ffffff 5%; 
    }

    /* ===== TABLE HEADER (Unified) ===== */
    .table-header {
        height: 1;
        background: transparent;
        color: #9ed0ff;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #00d2ff 20%;
        content-align: left middle;
    }

    .table-header Static {
        height: 1;
        content-align: left middle;
        color: #9ed0ff;
        text-style: bold;
    }

    .no-data-msg {
        width: 100%;
        content-align: center middle;
        padding: 2;
        color: #2e3d4f;
    }

    /* ===== TABLE ROWS (Unified) ===== */
    .table-row {
        height: 1;
        padding: 0 1;
        background: transparent;
        color: #c0cdd8;
        border-bottom: solid #ffffff 5%;
    }

    .table-row:hover {
        background: #2a3441; /* Slightly lighter navy hover */
        color: #ffffff;
    }

    .table-row-alt {
        background: rgba(0, 0, 0, 0.05); /* Very subtle alt */
    }
    """

    class Closed(Message):
        pass

    def __init__(self, title="Window", id=None, classes=None):
        super().__init__(id=id, classes=classes)
        self.can_focus = True
        self.window_title = title
        self.drag_start = None
        self.start_offset = None
        self._last_grab_time = 0  # Cooldown for touch toggling

    def compose(self) -> ComposeResult:
        yield WindowHeader(self.window_title)
        with Vertical(classes="window-content"):
            yield from self.compose_content()

    def compose_content(self) -> ComposeResult:
        yield Static("No data found", classes="no-data-msg")

    def close(self) -> None:
        if self.drag_start:
            self.stop_dragging()
        self.post_message(self.Closed())
        self.remove()

    # ---------- DRAG ---------- #

    def force_mouse_tracking(self, enable: bool = True):
        """Force Termux/Terminal to send all motion events."""
        import sys
        code = "\033[?1003h" if enable else "\033[?1003l"
        sys.stdout.write(code)
        sys.stdout.flush()

    def start_dragging(self, event: events.MouseDown) -> None:
        import time
        now = time.time()
        
        # Toggle logic with cooldown to handle rapid Touch Down/Up
        if self._dragging:
            if now - self._last_grab_time > 0.4:
                log_debug("Window: Toggle-Stop Drag")
                self.stop_dragging()
            return

        log_debug(f"Window: Toggle-Start Drag at {event.screen_x}, {event.screen_y}")
        self.drag_start = (event.screen_x, event.screen_y)
        self.start_offset = (
            self.styles.offset.x.value,
            self.styles.offset.y.value,
        )
        self._last_grab_time = now
        self.add_class("is-dragging")
        self.capture_mouse()
        self.force_mouse_tracking(True)

        if self.parent:
            self.parent.move_child(self, after=self.parent.children[-1])
        self.focus()

    def handle_dragging(self, event: events.MouseMove) -> None:
        if self.drag_start and self.start_offset:
            dx = event.screen_x - self.drag_start[0]
            dy = event.screen_y - self.drag_start[1]
            # log_debug(f"Window: Moving by {dx}, {dy}")
            self.styles.offset = (
                int(self.start_offset[0] + dx),
                int(self.start_offset[1] + dy),
            )

    @property
    def _dragging(self) -> bool:
        return self.drag_start is not None

    def stop_dragging(self) -> None:
        log_debug("Window: Drag/Grab Stopped")
        self.drag_start = None
        self.start_offset = None
        self.remove_class("is-dragging")
        self.release_mouse()
        self.force_mouse_tracking(False)

    # ---------- MOUSE EVENTS ---------- #

    def on_mouse_down(self, event: events.MouseDown) -> None:
        log_debug(f"Window: mouse_down at {event.screen_x}, {event.screen_y} (Offset: {self.styles.offset.x}, {self.styles.offset.y})")
        
        # Fallback: If clicked in the top 4 lines of the window, allow dragging
        # Relative Y to window
        rel_y = event.screen_y - self.region.y
        if rel_y <= 4:
            log_debug(f"Window: Fallback drag started (rel_y: {rel_y})")
            self.start_dragging(event)
        
        event.stop()
        event.prevent_default()

        if self.parent and self.parent.children[-1] != self:
            self.parent.move_child(self, after=self.parent.children[-1])

        self.focus()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        log_debug(f"Window: on_mouse_down at {event.screen_x}, {event.screen_y} (Dragging: {self._dragging})")
        
        # Toggle Logic: Start or Stop
        rel_y = event.screen_y - self.region.y
        if rel_y <= 4 or self._dragging:
            self.start_dragging(event)
        
        event.stop()
        event.prevent_default()

        if self.parent and self.parent.children[-1] != self:
            self.parent.move_child(self, after=self.parent.children[-1])
        self.focus()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._dragging:
            self.handle_dragging(event)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        log_debug(f"Window: on_mouse_up at {event.screen_x}, {event.screen_y}")
        # We NO LONGER stop on MouseUp to allow Touch Swiping work
        pass

    def on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        event.stop()
        event.prevent_default()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        event.stop()
        event.prevent_default()