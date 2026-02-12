from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Grid, Vertical, Horizontal
from textual.widgets import Button, Static, Label, Select
from textual.message import Message
from textual import events
from datetime import datetime, timedelta, date
import calendar
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

        # Parsing initial time safely
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

class CalendarScreen(ModalScreen):
    """شاشة التقويم لإدارة الورديات (بصيغة بوب آب)"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_date = datetime.now()
        self.year = self.current_date.year
        self.month = self.current_date.month
        
    def compose(self) -> ComposeResult:
        with Container(id="calendar-container", classes="modal-dialog"):
            # Header with Title and X button
            with Horizontal(classes="dialog-header"):
                yield Static("Shift Calendar", classes="dialog-title-text")
                yield Button("✕", id="close-calendar-btn", classes="close-icon-btn")
            
            # Navigation Bar
            with Horizontal(id="calendar-nav"):
                yield Button("<", id="prev-month", classes="nav-btn")
                yield Static(f"{calendar.month_name[self.month]} {self.year}", id="month-label")
                yield Button(">", id="next-month", classes="nav-btn")
                
            # Days of week header
            with Grid(id="days-header"):
                for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    yield Static(day, classes="day-name")
            
            # Calendar Grid
            with Grid(id="calendar-grid"):
                # Will be populated in on_mount/update
                pass

    async def on_mount(self) -> None:
        await self.update_calendar()

    async def update_calendar(self) -> None:
        """تحديث عرض التقويم"""
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
                    date_str = date_val.strftime("%Y-%m-%d")
                    shifts = self.db.get_shifts_by_date(date_str)
                    
                    is_today = (date_val == today)
                    has_pending = any(s['status'] in ['SCHEDULED', 'ACTIVE'] for s in shifts)
                    all_finished = len(shifts) > 0 and all(s['status'] in ['FINISHED', 'ABSENT'] for s in shifts)
                    
                    btn = CalendarDayButton(str(day), date_str, len(shifts) > 0, id=f"day-{day}")
                    btn.add_class("day-cell")
                    
                    if is_today:
                        btn.add_class("today")
                        btn.add_class("today-btn")
                    
                    if has_pending:
                        btn.add_class("has-shift")
                    elif all_finished:
                        btn.add_class("shifts-completed")
                    
                    grid.mount(btn)
        
        self.query_one("#month-label").update(f"{calendar.month_name[self.month]} {self.year}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "prev-month":
            self.month -= 1
            if self.month == 0:
                self.month = 12
                self.year -= 1
            await self.update_calendar()
            
        elif btn_id == "next-month":
            self.month += 1
            if self.month == 13:
                self.month = 1
                self.year += 1
            await self.update_calendar()
            
        elif btn_id == "close-calendar-btn":
            self.dismiss()

    async def on_calendar_day_button_selected(self, message: "CalendarDayButton.Selected") -> None:
        """عند اختيار يوم"""
        await self.app.push_screen(DayShiftsDialog(self.db, message.date_str, self.update_calendar_callback))

    async def update_calendar_callback(self) -> None:
         await self.update_calendar()


class CalendarDayButton(Button):
    """زر يمثل يوماً في التقويم"""
    
    class Selected(Message):
        def __init__(self, date_str: str) -> None:
            self.date_str = date_str
            super().__init__()
            
    def __init__(self, label: str, date_str: str, has_shift: bool, **kwargs):
        super().__init__(label, **kwargs)
        self.date_str = date_str
        self.has_shift = has_shift
        
    def on_click(self) -> None:
        self.post_message(self.Selected(self.date_str))


class DayShiftsDialog(ModalScreen):
    """نافذة تعرض ورديات يوم معين"""
    
    def __init__(self, db, date_str, on_close_callback=None):
        super().__init__()
        self.db = db
        self.date_str = date_str
        self.on_close_callback = on_close_callback
        
    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog small-modal"):
            # Header with Title and X button
            with Horizontal(classes="dialog-header"):
                # Format date for title
                try:
                    dt = datetime.strptime(self.date_str, "%Y-%m-%d")
                    title_date = dt.strftime("%a, %d %b %Y")
                except:
                    title_date = self.date_str
                    
                yield Static(f"Shifts: {title_date}", classes="dialog-title-text")
                yield Button("✕", id="close-x-btn", classes="close-icon-btn")

            with Vertical(id="shifts-list"):
                # Loaded in on_mount
                pass
            
            with Horizontal(classes="dialog-buttons"):
                # Hide Add Shift for past dates
                from datetime import date
                today_date = date.today()
                try:
                    target_date = datetime.strptime(self.date_str, "%Y-%m-%d").date()
                    if target_date >= today_date:
                        yield CustomButton("Add Shift", id="add-shift-btn", variant="primary")
                except:
                    yield CustomButton("Add Shift", id="add-shift-btn", variant="primary")

    async def on_mount(self) -> None:
        self.refresh_shifts()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-x-btn":
            if self.on_close_callback:
                try:
                    await self.on_close_callback()
                except:
                    self.on_close_callback()
            self.dismiss()
        elif event.button.id == "add-shift-btn":
            await self.app.push_screen(AddShiftDialog(self.db, self.date_str, self.refresh_shifts))

    async def on_shift_item_selected(self, message: "ShiftItem.Selected") -> None:
        # Open Shift Details
        await self.app.push_screen(ShiftDetailsDialog(self.db, message.shift, self.refresh_shifts))

    def refresh_shifts(self) -> None:
        """إعادة تحميل القائمة"""
        list_container = self.query_one("#shifts-list")
        list_container.remove_children()
        
        shifts = self.db.get_shifts_by_date(self.date_str)
        if not shifts:
            list_container.mount(Static("No shifts scheduled.", classes="no-data-msg"))
        else:
            for shift in shifts:
                list_container.mount(ShiftItem(shift))


class ShiftItem(Static):
    """عنصر وردية في القائمة (تصميم بسيط ومستقر)"""
    DEFAULT_CLASSES = "shift-row"
    
    class Selected(Message):
        def __init__(self, shift) -> None:
            self.shift = shift
            super().__init__()

    def __init__(self, shift):
        # Format time to 12H
        try:
            start_dt = datetime.strptime(shift['scheduled_start'], "%H:%M")
            end_dt = datetime.strptime(shift['scheduled_end'], "%H:%M")
            time_str = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        except:
            time_str = f"{shift['scheduled_start']} - {shift['scheduled_end']}"
            
        status_map = {
            'ACTIVE': "🟢",
            'SCHEDULED': "📅",
            'FINISHED': "🏁",
            'ABSENT': "❌"
        }
        status_icon = status_map.get(shift['status'], "❓")
        
        status_text = shift['status']
        if shift['is_late']:
            status_text += " [LATE]"
            
        label = f"{status_icon} {time_str}  |  {status_text}"
        super().__init__(label)
        self.shift = shift
        self.can_focus = True
        
    def on_click(self) -> None:
        self.post_message(self.Selected(self.shift))


class AddShiftDialog(ModalScreen):
    """نافذة إضافة وردية"""
    
    def __init__(self, db, date_str, on_success):
        super().__init__()
        self.db = db
        self.date_str = date_str
        self.on_success = on_success
        
    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        with Container(classes="modal-dialog small-modal"):
            with Horizontal(classes="dialog-header"):
                yield Static("Add New Shift", classes="dialog-title-text")
                yield Button("✕", id="close-x-btn", classes="close-icon-btn")
            
            with Vertical(classes="dialog-body"):
                # Calculate dynamic defaults
                now = datetime.now()
                # Start time: Next hour, 00 minutes
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                # End time: Start + 6 hours
                end_time_dt = next_hour + timedelta(hours=6)
                
                start_str = next_hour.strftime("%H:%M")
                end_str = end_time_dt.strftime("%H:%M")

                yield TimePickerWidget(label="Start Time", initial_time=start_str, id="start-picker")
                yield TimePickerWidget(label="End Time", initial_time=end_str, id="end-picker")
                
                yield Static("", id="error-msg", classes="error-text")
            
            with Horizontal(classes="dialog-buttons"):
                yield CustomButton("Save", id="save-btn", variant="success")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-x-btn":
            self.dismiss()
        elif event.button.id == "save-btn":
            start_time = self.query_one("#start-picker").value
            end_time = self.query_one("#end-picker").value
            
            # Already formatted as HH:MM
            
            if not start_time or not end_time:
                self.query_one("#error-msg").update("Invalid Time Format! (e.g. 10:00 PM)")
                return
                
            if self.db.add_scheduled_shift(self.date_str, start_time, end_time):
                if self.on_success:
                    self.on_success()
                self.dismiss()
            else:
                self.query_one("#error-msg").update("Failed to add shift (Database Error)")


class ShiftDetailsDialog(ModalScreen):
    """تفاصيل الوردية وإجراءاتها"""
    
    def __init__(self, db, shift, on_change):
        super().__init__()
        self.db = db
        self.shift = shift
        self.on_change = on_change
        
    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog small-modal"):
            with Horizontal(classes="dialog-header"):
                yield Static("Shift Details", classes="dialog-title-text")
                yield Button("✕", id="close-x-btn", classes="close-icon-btn")
            
            with Vertical(classes="dialog-body"):
                yield Static(id="shift-info-display", classes="shift-info-summary")
                yield CustomButton("Start Shift", id="start-shift-btn", variant="success")
                yield CustomButton("Start Break", id="break-btn", variant="primary")
                yield CustomButton("End Break", id="end-break-btn", variant="warning")
                yield CustomButton("Delete", id="delete-shift-btn", variant="error", classes="delete-btn")

    async def on_mount(self) -> None:
        self.refresh_ui()

    def refresh_ui(self) -> None:
        """تحديث بيانات الواجهة لحظياً"""
        # Reload shift data from DB
        updated_shift = self.db.get_shift_summary(self.shift['id'])
        if not updated_shift:
            self.dismiss()
            return
        self.shift = updated_shift
        
        # Update text
        try:
            s_time = datetime.strptime(self.shift['scheduled_start'], "%H:%M").strftime("%I:%M %p")
            e_time = datetime.strptime(self.shift['scheduled_end'], "%H:%M").strftime("%I:%M %p")
        except:
            s_time, e_time = self.shift['scheduled_start'], self.shift['scheduled_end']
            
        self.query_one("#shift-info-display").update(f"Status: {self.shift['status']}\nTime: {s_time} - {e_time}")
        
        # Control visibility
        is_active = (self.shift['status'] == 'ACTIVE')
        is_scheduled = (self.shift['status'] == 'SCHEDULED')
        on_break = self.shift.get('break_active', False)
        
        self.query_one("#start-shift-btn").styles.display = "block" if is_scheduled else "none"
        self.query_one("#break-btn").styles.display = "block" if (is_active and not on_break) else "none"
        self.query_one("#end-break-btn").styles.display = "block" if (is_active and on_break) else "none"
        self.query_one("#delete-shift-btn").styles.display = "block"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-x-btn":
            self.dismiss()
            
        elif event.button.id == "delete-shift-btn":
            if self.db.delete_shift(self.shift['id']):
                self.on_change()
                self.dismiss()
                
        elif event.button.id == "start-shift-btn":
            success, msg = self.db.start_shift(self.shift['id'])
            if success:
                self.notify("✅ Shift Started!", severity="information")
                self.refresh_ui()
                if self.on_change: self.on_change()
            else:
                self.notify(f"❌ {msg}", severity="error")

        elif event.button.id == "break-btn":
             await self.app.push_screen(BreakDialog(self.db, self.shift['id'], self.on_break_change))

        elif event.button.id == "end-break-btn":
             self.db.toggle_break(self.shift['id'])
             self.notify("☕ Break ended! Back to work.", severity="information")
             self.refresh_ui()
             if self.on_change: self.on_change()

    def on_break_change(self):
        self.refresh_ui()
        if self.on_change: self.on_change()

class BreakDialog(ModalScreen):
    """نافذة اختيار نوع الاستراحة"""
    def __init__(self, db, shift_id, on_success):
        super().__init__()
        self.db = db
        self.shift_id = shift_id
        self.on_success = on_success

    async def on_mount(self) -> None:
        """مراقبة حالة الوردية لإغلاق النافذة إذا انتهت"""
        self.set_interval(1, self.check_shift_active)

    def check_shift_active(self) -> None:
        """إغلاق النافذة تلقائياً إذا انتهت الوردية النشطة"""
        active_shift = self.db.get_active_shift()
        if not active_shift or active_shift['id'] != self.shift_id:
            self.dismiss()

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog small-modal"):
             with Horizontal(classes="dialog-header"):
                 yield Static("Select Break Duration", classes="dialog-title-text")
                 yield Button("✕", id="close-x-btn", classes="close-icon-btn")
                 
             with Vertical(classes="break-options"):
                 # قائمة عمودية بسيطة لضمان ظهور جميع الأزرار
                 yield CustomButton("5 Minutes", id="break-5")
                 yield CustomButton("10 Minutes", id="break-10")
                 yield CustomButton("15 Minutes", id="break-15")
                 yield CustomButton("20 Minutes", id="break-20")
                 yield CustomButton("25 Minutes", id="break-25")
                 yield CustomButton("30 Minutes", id="break-30")
                 yield CustomButton("60 Minutes", id="break-60")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-x-btn":
            self.dismiss()
            return
            
        durations = {
            "break-5": 5, "break-10": 10, "break-15": 15, "break-20": 20,
            "break-25": 25, "break-30": 30, "break-60": 60
        }
        
        if event.button.id in durations:
            minutes = durations[event.button.id]
            # التأكد من أن الوردية ما زالت نشطة قبل بدء البريك
            active_shift = self.db.get_active_shift()
            if active_shift and active_shift['id'] == self.shift_id:
                self.db.toggle_break(self.shift_id, minutes)
                self.notify(f"☕ Break started ({minutes} min)", severity="information")
                if self.on_success: self.on_success()
                self.dismiss()
            else:
                self.notify("⚠️ Shift already ended!", severity="error")
                self.dismiss()
