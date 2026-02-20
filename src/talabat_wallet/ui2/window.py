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
        background: #e74c3c;
        color: #ffffff;
    }
    """

    def __init__(self):
        super().__init__("✕", id="close_btn")

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        self.styles.background = "#7b0000"
        self.styles.color = "#ffcccc"

    def on_mouse_up(self, event: events.MouseUp) -> None:
        event.stop()
        self.styles.background = "#c0392b"
        self.styles.color = "#ffffff"
        # Find the window ancestor safely
        window = next((p for p in self.ancestors_with_self if isinstance(p, BaseWindow)), None)
        if window:
            window.close()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()

class ResizeHandle(Static):
    """Small handle at bottom-right for resizing."""
    def __init__(self):
        super().__init__("◢", id="resize_handle")

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        if isinstance(self.parent, BaseWindow):
            self.parent.start_resizing(event.screen_x, event.screen_y)




# ================= HEADER ================= #

class WindowHeader(Horizontal):

    DEFAULT_CSS = "" # Styles move to styles.tcss

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title

    def compose(self) -> ComposeResult:
        yield Static(self.title_text, classes="window-title")
        yield CloseButton()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        widget, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
        if widget and (widget.id == "close_btn" or isinstance(widget, CloseButton)):
            return

        event.stop()
        event.prevent_default()

        if isinstance(self.parent, BaseWindow):
            self.parent.start_dragging(event.screen_x, event.screen_y)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        pass


# ================= WINDOW ================= #

class BaseWindow(Vertical):
    """Base class for all draggable/resizable windows with Reactive UI support."""

    # ── WINDOW_ID REGISTRY ────────────────────────────────────────────────────
    WINDOW_ID: str = ""  # Every concrete subclass MUST override this.
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ == "BaseWindow":
            return
        if not cls.WINDOW_ID:
            raise RuntimeError(f"Class {cls.__name__} must define a non-empty WINDOW_ID.")
        if cls.WINDOW_ID in BaseWindow._registry:
            existing = BaseWindow._registry[cls.WINDOW_ID]
            if existing is not cls:
                raise RuntimeError(
                    f"Duplicate WINDOW_ID '{cls.WINDOW_ID}': "
                    f"already registered by {existing.__name__}"
                )
        BaseWindow._registry[cls.WINDOW_ID] = cls

    @staticmethod
    def reset_registry() -> None:
        """Clear the WINDOW_ID registry. Call once at App startup."""
        BaseWindow._registry.clear()

    def get_window_id(self) -> str:
        """Return this window's WINDOW_ID."""
        return self.__class__.WINDOW_ID

    # ── MESSAGES ──────────────────────────────────────────────────────────────

    class GlobalSettingsChanged(Message):
        """Broadcasted when settings (mode, batch, etc.) change."""
        def __init__(self, settings: dict):
            self.settings = settings
            super().__init__()

    class DataChanged(Message):
        """Broadcasted when any major database change occurs."""
        pass

    class OrderAdded(Message):
        """Broadcasted when a new order is successfully added."""
        pass

    class ShiftUpdated(Message):
        """Broadcasted when shift status or data changes."""
        pass

    class WindowResized(Message):
        """Broadcasted when a focused window is resized."""
        def __init__(self, title: str, width: int, height: int):
            super().__init__()
            self.title = title
            self.width = width
            self.height = height

    DEFAULT_CSS = ""  # Styles moved to styles.tcss

    class Closed(Message):
        pass

    def __init__(self, title="Window", id=None, classes=None, width=None, height=None):
        super().__init__(id=id, classes=classes)
        self.can_focus = True
        self.window_title = title
        self._drag_start_time = 0
        self.drag_start = None
        self.resize_start = None
        self.start_offset = None
        self.start_size = None
        
        # 📏 Logic: If specific size is NOT provided, use 'auto' for dynamic wrapping
        self.styles.width = width if width is not None else "auto"
        self.styles.height = height if height is not None else "auto"

    # ── LIFECYCLE HOOKS (empty stubs — override freely in subclasses) ─────────

    def on_window_open(self) -> None: pass
    def on_window_close(self) -> None: pass
    def on_window_focus(self) -> None: pass
    def on_window_blur(self) -> None: pass

    # ── TEXTUAL LIFECYCLE ─────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        """Handle window mounting."""
        self.on_window_open()
        if self.has_focus_within:
            self.post_message(self.WindowResized(self.window_title, self.size.width, self.size.height))

    def on_resize(self, event: events.Resize) -> None:
        w, h = self.size
        if self.has_focus_within:
            self.post_message(self.WindowResized(self.window_title, w, h))

    def on_focus(self, event: events.Focus) -> None:
        """Inform dashboard when this window becomes the active focus."""
        self.on_window_focus()
        self.add_class("-active")
        self.remove_class("-inactive")
        self.post_message(self.WindowResized(self.window_title, self.size.width, self.size.height))

    def on_blur(self, event: events.Blur) -> None:
        """Clear size info when window loses focus."""
        self.on_window_blur()
        self.remove_class("-active")
        self.add_class("-inactive")
        self.post_message(self.WindowResized("", 0, 0))

    def compose(self) -> ComposeResult:
        """Build window shell. Calls compose_content() — subclasses override compose_content ONLY."""
        yield WindowHeader(self.window_title)
        with Vertical(classes="window-content"):
            result = self.compose_content()
            if result is None:
                raise RuntimeError(
                    f"BaseWindow.compose_content() returned None in window '{self.get_window_id()}'. "
                    f"Use 'yield' or return a generator."
                )
            yield from result
        yield ResizeHandle()

    def compose_content(self) -> ComposeResult:
        """Override in subclasses to provide window content."""
        raise RuntimeError(f"Window '{self.get_window_id()}' must override compose_content()")

    def close(self) -> None:
        self.on_window_close()
        if self.drag_start:
            self.stop_dragging()
        self.post_message(self.Closed())
        self.remove()

    # ---------- DRAG ---------- #

    def start_dragging(self, screen_x: int, screen_y: int) -> None:
        self.drag_start = (screen_x, screen_y)
        self.start_offset = (
            self.styles.offset.x.value,
            self.styles.offset.y.value,
        )
        self.add_class("is-dragging")
        self.capture_mouse()

        if self.parent:
            self.parent.move_child(self, after=self.parent.children[-1])

    def handle_dragging(self, event: events.MouseMove) -> None:
        if self.drag_start and self.start_offset:
            dx = event.screen_x - self.drag_start[0]
            dy = event.screen_y - self.drag_start[1]
            self.styles.offset = (
                int(self.start_offset[0] + dx),
                int(self.start_offset[1] + dy),
            )

    @property
    def _dragging(self) -> bool:
        return self.drag_start is not None

    def on_key(self, event: events.Key) -> None:
        """Move the window using arrow keys."""
        if not (self.has_focus or self.has_focus_within):
            return

        step = 2
        moved = False
        ox, oy = self.styles.offset.x.value, self.styles.offset.y.value

        if event.key == "up":
            oy -= step
            moved = True
        elif event.key == "down":
            oy += step
            moved = True
        elif event.key == "left":
            ox -= step
            moved = True
        elif event.key == "right":
            ox += step
            moved = True

        if moved:
            self.styles.offset = (ox, oy)
            event.stop()

    def stop_dragging(self) -> None:
        self.drag_start = None
        self.start_offset = None
        self.remove_class("is-dragging")
        self.release_mouse()

    # ---------- RESIZE ---------- #

    def start_resizing(self, screen_x: int, screen_y: int) -> None:
        self.resize_start = (screen_x, screen_y)
        # Using .region to get current rendered size
        self.start_size = (self.region.width, self.region.height)
        self.add_class("is-resizing")
        self.capture_mouse()
        
        # 🔓 Allow resizing beyond initial max constraints
        self.styles.max_width = None
        self.styles.max_height = None

    def handle_resizing(self, event: events.MouseMove) -> None:
        if self.resize_start and self.start_size:
            dx = event.screen_x - self.resize_start[0]
            dy = event.screen_y - self.resize_start[1]
            
            # 🛡️ Minimums to prevent Range Error, no upper limits
            new_w = max(35, self.start_size[0] + dx)
            new_h = max(8, self.start_size[1] + dy)
            
            self.styles.width = new_w
            self.styles.height = new_h

    def stop_resizing(self) -> None:
        self.resize_start = None
        self.start_size = None
        self.remove_class("is-resizing")
        self.release_mouse()

    @property
    def _resizing(self) -> bool:
        return self.resize_start is not None

    # ---------- MOUSE EVENTS ---------- #

    def on_mouse_down(self, event: events.MouseDown) -> None:
        # Bring to front
        if self.parent and self.parent.children[-1] != self:
            self.parent.move_child(self, after=self.parent.children[-1])

        # Force window to top level focus regardless of children
        self.focus()

        # Header zone drag (top 3 rows): stop + prevent so content doesn't shift
        rel_y = event.screen_y - self.region.y
        if rel_y <= 3:
            widget_at, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
            if not (widget_at and (widget_at.id == "close_btn" or isinstance(widget_at, CloseButton))):
                self.start_dragging(event.screen_x, event.screen_y)
                event.stop()
                event.prevent_default()
        # DO NOT stop events for body clicks — let Input/Button receive them normally

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._dragging:
            self.handle_dragging(event)
        elif self._resizing:
            self.handle_resizing(event)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self.stop_dragging()
        elif self._resizing:
            self.stop_resizing()

    def on_click(self, event: events.Click) -> None:
        """Bring window to front and focus if nothing inside is focused."""
        widget_at, _ = getattr(self.app, "screen", self.app).get_widget_at(event.screen_x, event.screen_y)
        if widget_at is self:
            event.stop() # 🛑 Prevent dashboard from receiving this click and clearing focus!
        if self.parent:
            self.parent.move_child(self, after=self.parent.children[-1])
        self.focus()

    def on_base_window_global_settings_changed(self, message: GlobalSettingsChanged) -> None:
        """Reactive UI: Refresh window content when settings change globally."""
        self.refresh_ui(message.settings)

    def refresh_ui(self, settings: dict) -> None:
        """Override in subclasses to perform reactive updates (e.g. AddOrderWindow field visibility)."""
        pass

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        # Let scroll propagate naturally — don't stop it
        pass

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        pass