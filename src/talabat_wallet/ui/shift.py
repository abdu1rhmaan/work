from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Static, Label
from textual.message import Message
from textual import events
from .components import CustomButton
from datetime import datetime

class ShiftSummaryScreen(ModalScreen):
    """شاشة عرض ملخص الوردية"""
    
    def __init__(self, shift_summary):
        super().__init__()
        self.shift_summary = shift_summary
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        with Container(id="shift-summary-dialog", classes="modal-dialog small-modal"):
            with Horizontal(id="details-header"):
                yield Static("SHIFT SUMMARY", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="shift-summary-content"):
                # حساب مدة الوردية
                try:
                    start_time = datetime.strptime(self.shift_summary['actual_start'], "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.strptime(self.shift_summary['actual_end'], "%Y-%m-%d %H:%M:%S")
                    duration = end_time - start_time
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    
                    s_str = start_time.strftime('%I:%M %p')
                    e_str = end_time.strftime('%I:%M %p')
                except:
                    hours, minutes = 0, 0
                    s_str = self.shift_summary.get('actual_start', 'N/A')
                    e_str = self.shift_summary.get('actual_end', 'N/A')
                
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
                    yield CustomButton("Close", id="close-shift-summary")

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id in ["close-summary", "close-x"]:
            self.dismiss()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

class ShiftsHistoryScreen(ModalScreen):
    """شاشة عرض سجل الورديات السابقة (المنتهية فقط)"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        from textual.widgets import ListView
        from textual.containers import ScrollableContainer, Vertical
        
        with Container(id="shifts-history-dialog", classes="modal-dialog"):
            with Horizontal(id="details-header"):
                yield Static("SHIFTS HISTORY", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="shifts-history-body"):
                with ScrollableContainer(id="shifts-history-content"):
                    # Loaded in refresh_history via on_mount
                    pass
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="close-history-btn", variant="warning")
    
    def on_mount(self) -> None:
        """عند تحميل الشاشة"""
        self.refresh_history() # تحديث فوري عند الفتح
        self.set_interval(2, self.refresh_history)

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id in ["close-history-btn", "close-x-btn", "close-x"]:
            self.dismiss()
            
    async def on_shift_history_row_selected(self, event: "ShiftHistoryRow.Selected") -> None:
        """معالجة اختيار وردية"""
        shift_id = event.shift_id
        shift = self.db.get_shift_summary(shift_id)
        if not shift:
            return
            
        if shift['status'] in ['SCHEDULED', 'ACTIVE']:
            from .calendar_screen import ShiftDetailsDialog
            await self.app.push_screen(ShiftDetailsDialog(self.db, shift, self.refresh_history))
        else:
            self.app.push_screen(ShiftSummaryScreen(shift))

    def refresh_history(self) -> None:
        """تحديث القائمة بسلاسة - يظهر شفت واحد فقط UPCOMING في حالة عدم وجود شفت نشط"""
        content = self.query_one("#shifts-history-content")
        all_shifts = self.db.get_all_shifts(limit=50)
        
        # Filtering Logic:
        # 1. Always keep FINISHED, ABSENT, and ACTIVE
        # 2. If ACTIVE exists, do NOT show any SCHEDULED (upcoming)
        # 3. If NO ACTIVE exists, show ONLY THE FIRST SCHEDULED
        
        has_active = any(s['status'] == 'ACTIVE' for s in all_shifts)
        shifts = []
        upcoming_added = False
        
        for s in all_shifts:
            if s['status'] in ['FINISHED', 'ABSENT', 'ACTIVE']:
                shifts.append(s)
            elif s['status'] == 'SCHEDULED' and not has_active and not upcoming_added:
                shifts.append(s)
                upcoming_added = True
            
        if not shifts:
            if not content.children:
                content.mount(Static("\nNo shifts found.\n", classes="empty-message-text"))
            return

        # إزالة رسالة "لا يوجد ورديات" إذا وجدت
        for child in content.children:
            if isinstance(child, Static) and "No shifts" in str(child.render()):
                child.remove()

        # تحديث أو إضافة الصفوف
        current_ids = set()
        for shift in shifts:
            row_id = f"shift-row-{shift['id']}"
            current_ids.add(row_id)
            
            existing_row = content.query(f"#{row_id}")
            if existing_row:
                existing_row.first().update_data(shift)
            else:
                row = ShiftHistoryRow(shift, db=self.db)
                row.id = row_id
                content.mount(row)
        
        # إزالة الصفوف القديمة التي لم تعد في القائمة
        for child in list(content.children):
            if child.id and child.id.startswith("shift-row-") and child.id not in current_ids:
                child.remove()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

class ShiftHistoryRow(Static):
    """صف يمثل وردية واحدة في السجل ككتلة نصية واحدة لضمان الوضوح"""
    DEFAULT_CLASSES = "shift-row"
    
    class Selected(Message):
        def __init__(self, shift_id: int) -> None:
            self.shift_id = shift_id
            super().__init__()
    
    def __init__(self, shift, db=None, **kwargs):
        super().__init__("", **kwargs)
        self.shift = shift
        self.db = db
        self.can_focus = True
        
    def on_mount(self) -> None:
        self.update_data(self.shift)

    def update_data(self, shift) -> None:
        self.shift = shift
        
        # Date Logic
        if self.shift['actual_start']:
            date_ref = self.shift['actual_start']
            end_ref = self.shift['actual_end']
        else:
            date_ref = f"{self.shift['shift_date']} {self.shift['scheduled_start']}"
            end_ref = None
            
        try:
            start_time = datetime.strptime(date_ref, "%Y-%m-%d %H:%M:%S")
            date_str = start_time.strftime("%m-%d %I:%M%p")
        except:
            date_str = date_ref[:15]
            start_time = None

        # Live stats for ACTIVE
        if self.shift['status'] == 'ACTIVE' and self.db:
            live_stats = self.db.get_shift_stats(self.shift['id'])
            self.shift['total_orders'] = live_stats['total_orders']
            self.shift['net_profit'] = live_stats['net_profit']
            
        orders = self.shift.get('total_orders', 0)
        profit = self.shift.get('net_profit', 0.0)
        status = self.shift['status']
        if status == 'SCHEDULED': status = 'UPCOMING'
        
        # Formatting for a clean single row look
        # Date (35%) | Status (25%) | Orders (20%) | Profit (20%)
        # Using Rich syntax for colors
        color = "white"
        if status == 'ACTIVE': color = "green"
        elif status == 'UPCOMING': color = "cyan"
        elif status == 'ABSENT': color = "red"
        
        # Build the final string with fixed widths (approx padding)
        # 12-13 12:24AM (15 chars) | UPCOMING (9 chars) | Ord:0 (7 chars) | 0.00 (7 chars)
        row_text = f" {date_str:<15}  [{color}]{status:<9}[/]  Ord:{orders:<2}  [bold green]{profit:>7.2f}[/]"
        self.update(row_text)
            
    def on_click(self) -> None:
        """معالجة النقر على الصف"""
        self.post_message(self.Selected(self.shift['id']))
