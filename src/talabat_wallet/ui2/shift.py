from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import Button, Static, Label, Select, ListItem, ListView
from textual.message import Message
from textual import events, on
from datetime import datetime, timedelta, date
import calendar
from .window import BaseWindow
from .components import CustomButton
from ..utils import format_arabic

class TimePickerWidget(Container):
    """ويدجت لاختيار الوقت (ساعات ودقائق)"""
    def __init__(self, label: str = "", initial_time: str = "00:00", **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
        self.initial_time = initial_time

    def compose(self) -> ComposeResult:
        hours = [(f"{i:02d}", f"{i:02d}") for i in range(24)]
        minutes = [(f"{i:02d}", f"{i:02d}") for i in range(60)]
        try:
            h, m = self.initial_time.split(":")
        except:
            h, m = "00", "00"
        with Horizontal(classes="time-picker-row"):
            if self.label_text:
                yield Label(self.label_text, classes="time-picker-label")
            yield Select(hours, value=h, id="hour-select", allow_blank=False)
            yield Static(":", classes="time-separator")
            yield Select(minutes, value=m, id="minute-select", allow_blank=False)

    @property
    def value(self) -> str:
        try:
            h = self.query_one("#hour-select").value
            m = self.query_one("#minute-select").value
            return f"{h}:{m}"
        except:
            return "00:00"

class ShiftSummaryWindow(BaseWindow):
    WINDOW_ID = "shift_summary"
    """نافذة ملخص الوردية (MDI)"""
    def __init__(self, shift_summary):
        super().__init__(title="SHIFT SUMMARY", width=55)  # 📏 auto height
        self.shift_summary = shift_summary

    def compose_content(self) -> ComposeResult:
        try:
            start_time = datetime.strptime(self.shift_summary['actual_start'], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(self.shift_summary['actual_end'], "%Y-%m-%d %H:%M:%S")
            duration = end_time - start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes = remainder // 60
            s_str = start_time.strftime('%I:%M %p')
            e_str = end_time.strftime('%I:%M %p')
        except:
            hours, minutes = 0, 0
            s_str = self.shift_summary.get('actual_start', 'N/A')
            e_str = self.shift_summary.get('actual_end', 'N/A')
        
        with Vertical(id="shift-summary-content"):
            yield Static(f"\n🕒 SHIFT DURATION: {hours}h {minutes}m\n", classes="shift-stat")
            yield Static(f"Started: {s_str}", classes="shift-detail")
            yield Static(f"Ended:   {e_str}\n", classes="shift-detail")
            yield Static("─" * 30, classes="divider-text")
            yield Static(f"\n📦 TOTAL ORDERS: {self.shift_summary['total_orders']}", classes="shift-stat")
            yield Static(f"💰 TOTAL INCOME: {self.shift_summary['total_income']:.2f} EGP", classes="shift-stat")
            yield Static(f"💸 EXPENSES: {self.shift_summary['total_expenses']:.2f} EGP", classes="shift-stat")
            yield Static("─" * 30, classes="divider-text")
            net_profit = self.shift_summary['net_profit']
            profit_label = f"\n✅ NET PROFIT: {net_profit:.2f} EGP\n" if net_profit >= 0 else f"\n❌ NET LOSS: {abs(net_profit):.2f} EGP\n"
            yield Static(profit_label, classes="shift-profit")
            with Horizontal(id="shift-summary-buttons"):
                yield CustomButton("Close", id="close-summary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-summary":
            self.close()

class CalendarWindow(BaseWindow):
    WINDOW_ID = "shift_calendar"
    """نافذة التقويم (MDI)"""
    def __init__(self, db):
        super().__init__(title="SHIFT CALENDAR", width=75)  # 🗓️ No fixed height — use min-height in CSS
        self.db = db
        self.year = datetime.now().year
        self.month = datetime.now().month
        
    def compose_content(self) -> ComposeResult:
        with Horizontal(id="calendar-nav"):
            yield Button("<", id="prev-month", classes="nav-btn")
            yield Static(f"{calendar.month_name[self.month]} {self.year}", id="month-label")
            yield Button(">", id="next-month", classes="nav-btn")
        with Grid(id="days-header"):
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                yield Static(day, classes="day-name")
        yield Grid(id="calendar-grid")

    def on_mount(self) -> None:
        self.call_after_refresh(self.update_calendar)

    # 🚀 REAL-TIME UPDATES
    @on(BaseWindow.ShiftUpdated)
    async def handle_shift_update(self) -> None:
        await self.update_calendar()

    async def update_calendar(self) -> None:
        try:
            grid = self.query_one("#calendar-grid")
            await grid.remove_children()
            month_days = calendar.monthcalendar(self.year, self.month)
            today = date.today()
            for week in month_days:
                for day in week:
                    if day == 0:
                        grid.mount(Static("", classes="day-cell empty-day"))
                    else:
                        date_val = date(self.year, self.month, day)
                        date_iso = date_val.isoformat()
                        shifts = self.db.get_shifts_by_date(date_iso)
                        is_today = (date_val == today)
                        has_pending = any(s['status'] in ['SCHEDULED', 'ACTIVE'] for s in shifts)
                        all_finished = len(shifts) > 0 and all(s['status'] in ['FINISHED', 'ABSENT'] for s in shifts)
                        btn = Button(str(day), classes="day-cell")
                        btn.date_str = date_iso
                        if is_today: btn.add_class("today")
                        if has_pending: btn.add_class("has-shift")
                        elif all_finished: btn.add_class("shifts-completed")
                        grid.mount(btn)
            self.query_one("#month-label").update(f"{calendar.month_name[self.month]} {self.year}")
        except Exception as e:
            self.notify(f"Calendar Error: {e}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prev-month":
            self.month -= 1
            if self.month == 0: self.month = 12; self.year -= 1
            await self.update_calendar()
        elif event.button.id == "next-month":
            self.month += 1
            if self.month == 13: self.month = 1; self.year += 1
            await self.update_calendar()
        elif hasattr(event.button, "date_str"):
            if hasattr(self.app.screen, "open_window"):
                 self.app.screen.open_window(DayShiftsWindow(self.db, event.button.date_str, self.update_calendar))

class DayShiftsWindow(BaseWindow):
    WINDOW_ID = "day_shifts"
    """نافذة ورديات اليوم (MDI)"""
    def __init__(self, db, date_str, on_change=None):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            title = dt.strftime("%a, %d %b %Y")
        except: title = date_str
        super().__init__(title=f"SHIFTS: {title}", width=55)  # 📏 No fixed height — auto-sizes to shift list
        self.db = db
        self.date_str = date_str
        self.on_change = on_change

    def compose_content(self) -> ComposeResult:
        yield Vertical(id="shifts-list")
        with Horizontal(classes="dialog-buttons"):
            if datetime.strptime(self.date_str, "%Y-%m-%d").date() >= date.today():
                yield CustomButton("Add Shift", id="add-shift-btn")
            yield CustomButton("Close", id="close-day-shifts")

    def on_mount(self) -> None:
        self.call_after_refresh(self._do_refresh_shifts)

    async def _do_refresh_shifts(self):
        await self.refresh_shifts()

    async def refresh_shifts(self) -> None:
        try:
            container = self.query_one("#shifts-list")
            await container.remove_children()
            shifts = self.db.get_shifts_by_date(self.date_str)
            if not shifts:
                await container.mount(Static("No shifts scheduled.", classes="no-data-msg"))
            else:
                to_mount = [ShiftItemWidget(s) for s in shifts]
                await container.mount(*to_mount)
        except Exception as e:
            self.notify(f"Error loading shifts: {e}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-day-shifts":
            if self.on_change:
                import inspect
                if inspect.iscoroutinefunction(self.on_change): await self.on_change()
                else: self.on_change()
            self.remove()
        elif event.button.id == "add-shift-btn":
            if hasattr(self.app.screen, "open_window"):
                 self.app.screen.open_window(AddShiftWindow(self.db, self.date_str, self.refresh_shifts))

    async def on_shift_item_widget_selected(self, message: "ShiftItemWidget.Selected") -> None:
        if hasattr(self.app.screen, "open_window"):
            self.app.screen.open_window(ShiftDetailsWindow(self.db, message.shift, self.refresh_shifts))

class ShiftItemWidget(Static):
    """عنصر وردية في القائمة"""
    class Selected(Message):
        def __init__(self, shift): self.shift = shift; super().__init__()
    def __init__(self, shift):
        try:
            s_dt = datetime.strptime(shift['scheduled_start'], "%H:%M")
            e_dt = datetime.strptime(shift['scheduled_end'], "%H:%M")
            time_str = f"{s_dt.strftime('%I:%M %p')} - {e_dt.strftime('%I:%M %p')}"
        except: time_str = f"{shift['scheduled_start']} - {shift['scheduled_end']}"
        icon = {"ACTIVE": "🟢", "SCHEDULED": "📅", "FINISHED": "🏁", "ABSENT": "❌"}.get(shift['status'], "❓")
        super().__init__(f"[b]{icon} {time_str} | {shift['status']}[/b]")
        self.shift = shift
        self.can_focus = True
    def on_click(self) -> None: self.post_message(self.Selected(self.shift))

class AddShiftWindow(BaseWindow):
    WINDOW_ID = "add_shift"
    """نافذة إضافة وردية (MDI)"""
    def __init__(self, db, date_str, on_success):
        super().__init__(title="ADD NEW SHIFT", width=55)  # 📏 auto height
        self.db = db
        self.date_str = date_str
        self.on_success = on_success

    def compose_content(self) -> ComposeResult:
        now = datetime.now()
        start = (now.replace(minute=0, second=0) + timedelta(hours=1)).strftime("%H:%M")
        end = (now.replace(minute=0, second=0) + timedelta(hours=7)).strftime("%H:%M")
        yield TimePickerWidget(label="Start Time", initial_time=start, id="start-picker")
        yield TimePickerWidget(label="End Time", initial_time=end, id="end-picker")
        yield Static("", id="error-msg", classes="error-text")
        with Horizontal(classes="dialog-buttons"):
            yield CustomButton("Save", id="save-shift")
            yield CustomButton("Cancel", id="cancel-shift")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-shift": self.remove()
        elif event.button.id == "save-shift":
            start = self.query_one("#start-picker").value
            end = self.query_one("#end-picker").value
            success, final_date, err = self.db.add_scheduled_shift(self.date_str, start, end)
            if success:
                # 🚀 Broadcast update
                self.post_message(self.ShiftUpdated())
                if self.on_success: 
                    import inspect
                    if inspect.iscoroutinefunction(self.on_success):
                        await self.on_success()
                    else:
                        self.on_success()
                self.remove()
            else: self.query_one("#error-msg").update(err)

class ShiftDetailsWindow(BaseWindow):
    WINDOW_ID = "shift_details"
    """تفاصيل الوردية (MDI)"""
    def __init__(self, db, shift, on_change):
        super().__init__(title="SHIFT DETAILS", width=55)  # 📏 No fixed height — inline buttons
        self.db = db
        self.shift = shift
        self.on_change = on_change

    def compose_content(self) -> ComposeResult:
        yield Static(id="shift-info-display", classes="shift-info-summary")
        # ✅ All action buttons on ONE horizontal line — no gap below
        with Horizontal(classes="inline-buttons", id="shift-action-buttons"):
            yield CustomButton("Start", id="start-shift-btn")
            yield CustomButton("Delete", id="delete-shift-btn")
            yield CustomButton("Start Break", id="break-btn")
            yield CustomButton("End Break", id="end-break-btn")

    def on_mount(self) -> None: self.refresh_ui()

    def refresh_ui(self) -> None:
        updated = self.db.get_shift_summary(self.shift['id'])
        if not updated: self.close(); return
        self.shift = updated
        self.query_one("#shift-info-display").update(
            f"Status: {self.shift['status']}\nTime: {self.shift['scheduled_start']} - {self.shift['scheduled_end']}"
        )
        on_break = self.shift.get('break_active', False)
        status = self.shift['status']
        # ✅ Show/hide per status — all buttons remain in the same row
        self.query_one("#start-shift-btn").display = "block" if (status == 'SCHEDULED') else "none"
        self.query_one("#break-btn").display = "block" if (status == 'ACTIVE' and not on_break) else "none"
        self.query_one("#end-break-btn").display = "block" if (status == 'ACTIVE' and on_break) else "none"
        self.refresh()  # 🔄 retrigger layout after show/hide

    # 🚀 REAL-TIME UPDATES: refresh if orders are added elsewhere
    @on(BaseWindow.OrderAdded)
    def handle_order_added(self) -> None:
        self.refresh_ui()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-shift-btn":
            if self.db.delete_shift(self.shift['id']):
                if self.on_change: self.on_change()
                self.close()
        elif event.button.id == "start-shift-btn":
            if self.db.start_shift(self.shift['id'])[0]:
                self.refresh_ui()
                if self.on_change: self.on_change()
        elif event.button.id == "break-btn":
            if hasattr(self.app.screen, "open_window"):
                 self.app.screen.open_window(BreakWindow(self.db, self.shift['id'], self.refresh_ui))
        elif event.button.id == "end-break-btn":
            self.db.toggle_break(self.shift['id'])
            # 🚀 Broadcast update
            self.post_message(self.ShiftUpdated())
            self.refresh_ui()
            if self.on_change: self.on_change()

class BreakWindow(BaseWindow):
    WINDOW_ID = "break_duration"
    """نافذة الاستراحة (MDI)"""
    def __init__(self, db, shift_id, on_success):
        super().__init__(title="BREAK DURATION", width=45)  # 📏 No fixed height — stops at last button
        self.db = db
        self.shift_id = shift_id
        self.on_success = on_success

    def compose_content(self) -> ComposeResult:
        with Vertical(classes="spaced-vertical"):
            for m in [5, 10, 15, 20, 30, 60]:
                yield CustomButton(f"{m} Minutes", id=f"break-{m}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith("break-"):
            mins = int(event.button.id.split("-")[1])
            self.db.toggle_break(self.shift_id, mins)
            # 🚀 Broadcast update
            self.post_message(self.ShiftUpdated())
            if self.on_success: self.on_success()
            self.close()

class ShiftHistoryRow(ListItem):
    """سطر تاريخ الورديات المطور - أعمدة منظمة"""
    def __init__(self, shift: dict, **kwargs):
        super().__init__(**kwargs)
        self.shift = shift
        self.add_class("shift-history-row")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="shift-row-content"):
            # 📅 Date (formatted for display)
            yield Label(format_arabic(str(self.shift.get('shift_date', 'N/A'))), classes="col-date")
            
            # 🏁 Status
            status = self.shift.get('status', 'Unknown')
            icon = {"ACTIVE": "🟢", "SCHEDULED": "📅", "FINISHED": "🏁", "ABSENT": "❌"}.get(status, "❓")
            yield Label(format_arabic(f"{icon} {status}"), classes="col-status")
            
            # 📦 Orders
            orders = self.shift.get('total_orders', 0)
            yield Label(f"{orders}", classes="col-orders")

class ShiftsHistoryWindow(BaseWindow):
    WINDOW_ID = "shifts_history"
    """سجل الورديات (MDI)"""
    def __init__(self, db):
        super().__init__(title="SHIFTS HISTORY", width=80)  # 📏 No fixed height — fills real rows only
        self.db = db

    def compose_content(self) -> ComposeResult:
        with Horizontal(id="shifts-history-header"):
            yield Label("DATE", classes="col-date")
            yield Label("STATUS", classes="col-status")
            yield Label("ORDERS", classes="col-orders")
            
        self.history_list = ListView(id="shifts-history-content")
        yield self.history_list
        
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("Close", id="close-history-btn", custom_width=15)

    def on_mount(self) -> None:
        self.refresh_history()
        self.set_interval(60, self.refresh_history)

    # 🚀 REAL-TIME UPDATES
    @on(BaseWindow.ShiftUpdated)
    def handle_shift_update(self) -> None:
        self.refresh_history()

    def refresh_history(self) -> None:
        try:
            all_shifts = self.db.get_all_shifts(limit=50)
        except Exception:
            return
        # ✅ Only real DB rows — no placeholders, no spacers
        # Always refresh when count changes
        current_count = len(self.history_list.children)
        if current_count != len(all_shifts):
            self.history_list.clear()
            for s in all_shifts:
                self.history_list.append(ShiftHistoryRow(s))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-history-btn":
            self.remove()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and hasattr(event.item, "shift"):
             shift = event.item.shift
             if shift['status'] in ['SCHEDULED', 'ACTIVE']:
                 if hasattr(self.app.screen, "open_window"):
                      self.app.screen.open_window(ShiftDetailsWindow(self.db, shift, self.refresh_history))
             else:
                 if hasattr(self.app.screen, "open_window"):
                      self.app.screen.open_window(ShiftSummaryWindow(shift))
