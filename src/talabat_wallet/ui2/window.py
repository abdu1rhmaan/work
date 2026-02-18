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


# ================= HEADER ================= #

class WindowHeader(Horizontal):

    DEFAULT_CSS = """
    WindowHeader {
        dock: top;
        width: 100%;
        height: 2;
        background: #1c2228; /* Unified Navy */
        color: #c9d1d9;
        layout: horizontal;
        padding: 0 1;
        margin: 0;
        border-bottom: none;
        content-align: left middle;
    }

    WindowHeader .window-title {
        width: 1fr;
        height: 2;
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
        # Simplest check for close button to avoid latency in Termux
        if hasattr(event, "widget") and event.widget.id == "close_btn":
            return
        
        # Fallback check
        widget, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
        if widget and (widget.id == "close_btn" or isinstance(widget, CloseButton)):
            return

        event.stop()
        event.prevent_default()

        if isinstance(self.parent, DraggableWindow):
            self.parent.start_dragging(event)


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

    DraggableWindow:focus-within {
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

    def compose(self) -> ComposeResult:
        yield WindowHeader(self.window_title)
        with Vertical(classes="window-content"):
            yield from self.compose_content()

    def compose_content(self) -> ComposeResult:
        yield Static("No data found", classes="no-data-msg")

    def close(self) -> None:
        self.post_message(self.Closed())
        self.remove()

    # ---------- DRAG ---------- #

    def start_dragging(self, event: events.MouseDown) -> None:
        self.drag_start = (event.screen_x, event.screen_y)
        self.start_offset = (
            self.styles.offset.x.value,
            self.styles.offset.y.value,
        )
        self.capture_mouse()

        if self.parent:
            self.parent.move_child(self, after=self.parent.children[-1])

        self.focus()

    def handle_dragging(self, event: events.MouseMove) -> None:
        if self.drag_start and self.start_offset:
            dx = event.screen_x - self.drag_start[0]
            dy = event.screen_y - self.drag_start[1]
            self.styles.offset = (
                int(self.start_offset[0] + dx),
                int(self.start_offset[1] + dy),
            )

    def stop_dragging(self) -> None:
        self.drag_start = None
        self.start_offset = None
        self.release_mouse()

    # ---------- MOUSE EVENTS ---------- #

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        event.prevent_default()

        if self.parent and self.parent.children[-1] != self:
            self.parent.move_child(self, after=self.parent.children[-1])

        self.focus()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        event.stop()
        event.prevent_default()

        if self.drag_start:
            self.handle_dragging(event)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        event.stop()
        event.prevent_default()

        if self.drag_start:
            self.stop_dragging()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        event.stop()
        event.prevent_default()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        event.stop()
        event.prevent_default()