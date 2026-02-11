from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Static
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
            yield Static("SHIFT SUMMARY", id="title")
            
            with Vertical(id="shift-summary-content"):
                # حساب مدة الوردية
                start_time = datetime.strptime(self.shift_summary['start_time'], "%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(self.shift_summary['end_time'], "%Y-%m-%d %H:%M:%S")
                duration = end_time - start_time
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                
                yield Static(f"\n🕒 SHIFT DURATION: {hours}h {minutes}m\n", classes="shift-stat")
                yield Static(f"Started: {start_time.strftime('%I:%M %p')}", classes="shift-detail")
                yield Static(f"Ended:   {end_time.strftime('%I:%M %p')}\n", classes="shift-detail")
                
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
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "close-shift-summary":
            self.dismiss()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

class ShiftsHistoryScreen(ModalScreen):
    """شاشة عرض سجل الورديات السابقة"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        from textual.widgets import ListView
        from textual.containers import ScrollableContainer, Vertical
        
        with Container(id="shifts-history-dialog", classes="modal-dialog"):
            yield Static("SHIFTS HISTORY", id="title")
            
            # Spacer 1 (~1cm gap)
            yield Static(" ", classes="layout-spacer-top")
            
            # محتوى قابل للتمرير
            with Vertical(id="shifts-history-body"):
                with ScrollableContainer(id="shifts-history-content"):
                    shifts = self.db.get_all_shifts(limit=50)
                    
                    if not shifts:
                        yield Static("\nNo shifts recorded yet.\n", classes="empty-message")
                    else:
                        for shift in shifts:
                            yield ShiftHistoryRow(shift)
            
            # Spacer 2 (~1cm gap)
            yield Static(" ", classes="layout-spacer")
            
            # أزرار ثابتة في الأسفل
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="close-history")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "close-history":
            self.dismiss()
            
    def on_shift_history_row_selected(self, event: "ShiftHistoryRow.Selected") -> None:
        """معالجة اختيار وردية"""
        shift_id = event.shift_id
        summary = self.db.get_shift_summary(shift_id)
        if summary:
            self.app.push_screen(ShiftSummaryScreen(summary))
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

class ShiftHistoryRow(Container):
    """صف يمثل وردية واحدة في السجل"""
    
    class Selected(Message):
        """رسالة عند اختيار الوردية"""
        def __init__(self, shift_id: int) -> None:
            self.shift_id = shift_id
            super().__init__()
    
    def __init__(self, shift):
        super().__init__()
        self.shift = shift
        
    def compose(self) -> ComposeResult:
        """بناء الصف"""
        from textual.widgets import Label
        from textual.containers import Horizontal
        
        start_time = datetime.strptime(self.shift['start_time'], "%Y-%m-%d %H:%M:%S")
        
        if self.shift['end_time']:
            end_time = datetime.strptime(self.shift['end_time'], "%Y-%m-%d %H:%M:%S")
            duration = end_time - start_time
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = "Active"
        
        date_str = start_time.strftime("%Y-%m-%d %I:%M %p")
        
        date_str = start_time.strftime("%Y-%m-%d %I:%M %p")
        
        # Grid Layout: 4 columns defined in CSS
        yield Label(f"{date_str}", classes="shift-date")
        yield Label(f"{duration_str}", classes="shift-duration")
        yield Label(f"Orders: {self.shift['total_orders']}", classes="shift-orders")
        
        # Profit or Active Status in the last column
        if self.shift['end_time']:
            yield Label(f"Profit: {self.shift['net_profit']:.2f}", classes="shift-profit")
        else:
            yield Label("ACTIVE SHIFT", classes="shift-active-label")
            
    def on_click(self) -> None:
        """معالجة النقر على الصف"""
        if self.shift['end_time']:
            self.post_message(self.Selected(self.shift['id']))
