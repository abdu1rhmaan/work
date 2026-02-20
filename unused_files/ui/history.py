from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, DataTable, ListView, Label, ListItem
from textual import events
from datetime import datetime, timedelta
from ..database import Database
from .components import CustomButton, HistoryTable, HistoryRow, OptionSelector

class OrderDetailsScreen(ModalScreen):
    """نافذة منبثقة لعرض تفاصيل الطلب كاملة مع خيار التعديل"""
    
    def __init__(self, order_data: dict, display_id: int, db=None, refresh_callback=None):
        super().__init__()
        self.order = order_data
        self.display_id = display_id
        self.db = db
        self.refresh_callback = refresh_callback

    def on_mount(self) -> None:
        # ✅ Prevent auto-focus on Close button
        self.set_focus(None)
        self.set_timer(0.1, lambda: self.set_focus(None))
        
    def compose(self) -> ComposeResult:
        with Container(id="order-details-dialog", classes="modal-dialog small-modal"):
            with Horizontal(id="details-header"):
                yield Static(f"Order Details #{self.display_id}", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="details-content"):
                yield Static(f"Date: [b]{self.order['datetime']}[/b]")
                yield Static(f"Type: [b]{self.order['order_type']}[/b]")
                yield Static("────────────────────────")
                yield Static(f"Paid Amount: {self.order['paid']:.2f} EGP")
                yield Static(f"Expected:    {self.order['expected']:.2f} EGP")
                yield Static(f"Actual:      {self.order['actual']:.2f} EGP")
                yield Static("────────────────────────")
                yield Static(f"Cash Tip:    {self.order['tip_cash']:.2f} EGP")
                yield Static(f"Visa Tip:    {self.order['tip_visa']:.2f} EGP")
                yield Static(f"Delivery:    {self.order['delivery_fee']:.2f} EGP")
                
                profit = self.order['delivery_fee'] + self.order['tip_cash'] + self.order['tip_visa']
                yield Static(f"\nTotal Profit: [b green]{profit:.2f} EGP[/b green]")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Edit", id="edit-order")
                yield CustomButton("Close", id="close-details")

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["close-details", "close-x"]:
            self.dismiss()
        elif event.button.id == "edit-order":
            from .add_order import AddOrderScreen
            # إغلاق شاشة التفاصيل وفتح شاشة التعديل
            self.dismiss()
            await self.app.push_screen(AddOrderScreen(self.db, self.refresh_callback, order_to_edit=self.order))

class TipDetailsScreen(ModalScreen):
    """نافذة منبثقة لعرض تفاصيل البقشيش"""
    
    def __init__(self, order_data: dict, display_id: int):
        super().__init__()
        self.order = order_data
        self.display_id = display_id

    def on_mount(self) -> None:
        # ✅ Prevent auto-focus on Close button
        self.set_focus(None)
        self.set_timer(0.1, lambda: self.set_focus(None))
        
    def compose(self) -> ComposeResult:
        with Container(id="tip-details-dialog", classes="modal-dialog small-modal"):
            with Horizontal(id="details-header"):
                yield Static(f"Tip Details #{self.display_id}", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="details-content"):
                yield Static(f"Date: [b]{self.order['datetime']}[/b]")
                yield Static("────────────────────────")
                
                tip_cash = self.order.get('tip_cash', 0.0)
                tip_visa = self.order.get('tip_visa', 0.0)
                total_tip = tip_cash + tip_visa
                
                if tip_cash > 0:
                    yield Static(f"💵 Cash Tip:  [b cyan]{tip_cash:.2f} EGP[/b cyan]")
                if tip_visa > 0:
                    yield Static(f"💳 Visa Tip:  [b cyan]{tip_visa:.2f} EGP[/b cyan]")
                
                yield Static("────────────────────────")
                yield Static(f"Total Tip: [b green]{total_tip:.2f} EGP[/b green]")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="close-details")

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["close-details", "close-x"]:
            self.dismiss()

class SettlementDetailsScreen(ModalScreen):
    """نافذة منبثقة لعرض تفاصيل عملية التسوية (القبض/التحويل)"""
    
    def __init__(self, order_data: dict, display_id: int):
        super().__init__()
        self.order = order_data
        self.display_id = display_id

    def on_mount(self) -> None:
        # ✅ Prevent auto-focus on Close button
        self.set_focus(None)
        self.set_timer(0.1, lambda: self.set_focus(None))

    def compose(self) -> ComposeResult:
        with Container(id="settlement-details-dialog", classes="modal-dialog small-modal"):
            with Horizontal(id="details-header"):
                yield Static(f"Settlement Details #{self.display_id}", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="details-content"):
                yield Static(f"Date: [b]{self.order['datetime']}[/b]")
                
                # Use personal_wallet_effect because company_wallet_effect is now always negative for both
                direction = "PAY TO COMPANY" if self.order['personal_wallet_effect'] < 0 else "RECEIVE FROM COMPANY"
                yield Static(f"Type: [b]{direction}[/b]")
                yield Static("────────────────────────")
                
                yield Static(f"Amount: [b]{self.order['actual']:.2f} EGP[/b]")
                
                yield Static("────────────────────────")
                yield Static(f"Personal Wallet Effect: {self.order['personal_wallet_effect']:+.2f} EGP")
                yield Static(f"Company Wallet Effect:  {self.order['company_wallet_effect']:+.2f} EGP")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="close-details")

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["close-details", "close-x"]:
            self.dismiss()

from rich.table import Table
from rich import box

class HistoryScreen(ModalScreen):
    """شاشة التاريخ والرسوم البيانية كـ Popup"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.show_chart_only = False
        self.current_period = "DAILY"
        self.selected_ids = set()
        self.filter_type = "All"
        self.filter_period = "All"
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        container_classes = "modal-dialog"
        if self.show_chart_only:
            container_classes += " analysis-modal"
            
        with Container(id="history-dialog-main", classes=container_classes):
            if self.show_chart_only:
                with Horizontal(id="details-header"):
                    yield Static("PROFIT ANALYSIS", id="details-title")
                    yield Button("X", id="close-x", classes="close-button")
                with Vertical(id="history-content"):
                    # زر التبديل بين الفترات
                    with Horizontal(id="period-buttons"):
                        yield CustomButton(f"PERIOD: {self.current_period}", id="period-toggle", custom_width=20)
                    
                    # حاوية عرض البيانات النصية
                    self.analysis_view = Static(id="analysis-view")
                    yield self.analysis_view
                    
                    with Horizontal(id="dialog-buttons"):
                        yield CustomButton("Back", id="back-chart", custom_width=12)
            else:
                with Horizontal(id="details-header"):
                    yield Static("ORDER HISTORY", id="details-title")
                    yield Button("X", id="close-x", classes="close-button")
                
                with Vertical(id="filter-section"):
                    type_options = [
                        ("All", "All"), ("Order", "Order"), 
                        ("Tips", "Tips"), ("Settlement", "Settlement")
                    ]
                    yield OptionSelector(type_options, self.filter_type, id="filter-type")
                    
                    period_options = [
                        ("All", "All"), ("Today", "Today"), 
                        ("Yesterday", "Yesterday"), ("Week", "Week"),
                        ("Month", "Month")
                    ]
                    yield OptionSelector(period_options, self.filter_period, id="filter-period")

                with Vertical(id="history-content", classes="flex-1"):
                    # ترويسة الجدول لإعطاء مظهر الجدول
                    with Horizontal(id="history-header"):
                        yield Label("✓", classes="col-sel")
                        yield Label("ID", classes="col-id")
                        yield Label("Date", classes="col-date")
                        yield Label("Type", classes="col-type")
                        yield Label("Profit", classes="col-profit")
                    
                    # قائمة الطلبات ( ListView بدل DataTable)
                    self.history_list = ListView(id="history-list")
                    yield self.history_list
                    
                    with Horizontal(id="dialog-buttons"):
                        yield CustomButton("Delete", id="delete-order", custom_width=12)
                        yield CustomButton("Close", id="back", custom_width=12)

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.load_data()
        # ✅ Aggressive focus suppression on entry
        self.set_focus(None)
        self.set_timer(0.01, lambda: self.set_focus(None))
        self.set_timer(0.05, lambda: self.set_focus(None))
        self.set_timer(0.1, lambda: self.set_focus(None))
        self.set_timer(0.2, lambda: self.set_focus(None))

    def on_show(self) -> None:
        """عند استعادة الشاشة"""
        self.set_focus(None)
        self.set_timer(0.1, lambda: self.set_focus(None))
        
    def on_option_selector_selected(self, message: OptionSelector.Selected) -> None:
        """تحديث الفلاتر عند تغيير الخيارات"""
        if message.selector.id == "filter-type":
            self.filter_type = message.value
        elif message.selector.id == "filter-period":
            self.filter_period = message.value
            
        self.load_data()
    
    def load_data(self) -> None:
        """تحميل البيانات وعرضها"""
        if not self.show_chart_only:
            # ✅ Handle new filter logic for Order and Tips
            if self.filter_type == "Order":
                # Order = all non-settlement, non-tip orders (Restaurant/Mart/Grocery/etc)
                orders = self.db.get_all_orders(
                    limit=100,
                    order_type="All",  # Get all types
                    period=self.filter_period
                )
                # Filter out settlement and tip entries
                orders = [o for o in orders if o.get('mode') not in ['SETTLEMENT', 'TIP']]
                
            elif self.filter_type == "Tips":
                # ✅ NEW: Tips = entries with mode='TIP' (separate tip entries)
                orders = self.db.get_all_orders(
                    limit=100,
                    order_type="All",
                    period=self.filter_period
                )
                # Filter for TIP mode entries only
                orders = [o for o in orders if o.get('mode') == 'TIP']
            else:
                # All or Settlement - use database filter
                orders = self.db.get_all_orders(
                    limit=100, 
                    order_type=self.filter_type, 
                    period=self.filter_period
                )
            
            # مسح القائمة الحالية - الطريقة الأكثر أماناً
            self.history_list.clear()
            
            if not orders:
                # عرض رسالة إرشادية إذا لم توجد داتا
                self.history_list.append(ListItem(Label("No orders found", classes="col-type")))
                return
                
            # حساب الترقيم التسلسلي (1 لأحدث طلب، 2 للذي يليه...)
            for idx, order in enumerate(orders, 1):
                is_selected = str(order['id']) in self.selected_ids
                self.history_list.append(HistoryRow(order, display_id=idx, is_selected=is_selected))
        else:
            self.load_analysis_data()

    def load_analysis_data(self) -> None:
        """تحميل وعرض البيانات التحليلية كجدول"""
        stats = self.db.get_analysis_stats(self.current_period)
        
        table = Table(box=box.SIMPLE, expand=True, show_header=True)
        table.add_column("Category", style="cyan", ratio=2)
        table.add_column("Amount (EGP)", justify="right", style="bold", ratio=1)
        
        if self.current_period == "DAILY":
            table.title = f"[bold yellow]=== TODAY ===[/]"
            table.add_row("Delivery Income", f"{stats['delivery_income']:.2f}")
            table.add_row("Tip Cash", f"{stats['tip_cash']:.2f}")
            table.add_row("Tip Visa", f"{stats['tip_visa']:.2f}")
            table.add_section()
            table.add_row("Personal Expenses", f"[red]{stats['total_expenses']:.2f}[/]")
            table.add_section()
            
            # Net Profit
            net = stats['net_profit']
            color = "green" if net >= 0 else "red"
            table.add_row("NET PROFIT", f"[{color}]{net:.2f}[/]")
        
        elif self.current_period == "WEEKLY":
            table.title = f"[bold yellow]=== THIS WEEK ===[/]"
            table.add_row("Delivery Income", f"{stats['delivery_income']:.2f}")
            table.add_row("Total Tips", f"{stats['total_tips']:.2f}")
            table.add_section()
            table.add_row("Personal Expenses", f"[red]{stats['total_expenses']:.2f}[/]")
            table.add_section()
            table.add_row("NET PROFIT", f"[{'green' if stats['net_profit'] >= 0 else 'red'}]{stats['net_profit']:.2f}[/]")
            
        elif self.current_period == "MONTHLY":
            table.title = f"[bold yellow]=== THIS MONTH ===[/]"
            table.add_row("Total Income", f"{stats['total_income']:.2f}")
            table.add_row("Total Expenses", f"[red]{stats['total_expenses']:.2f}[/]")
            table.add_section()
            table.add_row("NET PROFIT", f"[{'green' if stats['net_profit'] >= 0 else 'red'}]{stats['net_profit']:.2f}[/]")
            table.add_row("Daily Average", f"{stats['daily_avg']:.2f}")
            
        elif self.current_period == "YEARLY":
            table.title = f"[bold yellow]=== THIS YEAR ===[/]"
            table.add_row("Total Income", f"{stats['total_income']:.2f}")
            table.add_row("Orders Count", f"{stats['orders_count']}")
            table.add_row("Best Month", f"{stats['best_month']}")
            table.add_section()
            table.add_row("NET PROFIT", f"[{'green' if stats['net_profit'] >= 0 else 'red'}]{stats['net_profit']:.2f}[/]")

        # تحديث العرض
        self.analysis_view.update(table)
        # تحديث تسمية الزر
        self.query_one("#period-toggle").label = f"PERIOD: {self.current_period}"
            
    def on_history_row_toggle_selection(self, message: HistoryRow.ToggleSelection) -> None:
        """عند الضغط على المربع (الزر الحقيقي)"""
        order_id = message.order_id
        if order_id in self.selected_ids:
            self.selected_ids.remove(order_id)
        else:
            self.selected_ids.add(order_id)
        
        # تحديث القائمة فوراً
        self.load_data()
        self.update_delete_button()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """عند الضغط مرتين أو الضغط على السطر بالكامل (Double Click/Enter)"""
        if event.item is None:
            return
            
        row = event.item
        if not hasattr(row, "order_id"):
            return
            
        order_id = row.order_id
        display_id = row.display_id # الحصول على الرقم التسلسلي المعروض في القائمة
        
        # إلغاء الاختيار عند فتح الأوردر ليكون العرض نظيفاً كما طلب المستخدم
        if order_id in self.selected_ids:
            self.selected_ids.remove(order_id)
            self.update_delete_button()
            
        order = self.db.get_order_by_id(int(order_id))
        if order:
            self.load_data() # تحديث القائمة لإخفاء النقطة
            
            # ✅ NEW: Check order mode and open appropriate details screen
            if order.get('mode') == 'TIP':
                # Open Tip Details Screen for tip entries
                self.app.push_screen(TipDetailsScreen(order, display_id))
            elif order.get('mode') == 'SETTLEMENT':
                # Open Settlement Details Screen
                self.app.push_screen(SettlementDetailsScreen(order, display_id))
            else:
                # Open Order Details Screen for regular orders
                self.app.push_screen(OrderDetailsScreen(order, display_id, self.db, self.load_data))

    def update_delete_button(self):
        btn = self.query_one("#delete-order")
        count = len(self.selected_ids)
        if count > 0:
            btn.label = f"Delete ({count})"
        else:
            btn.label = "Delete"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        button_id = event.button.id
        if button_id == "period-toggle":
            periods = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
            current_idx = periods.index(self.current_period)
            self.current_period = periods[(current_idx + 1) % len(periods)]
            self.load_data()
        elif button_id == "delete-order":
            await self.delete_selected_orders()
        elif button_id in ["back", "back-chart", "close-x"]:
            self.dismiss()
    
    async def delete_selected_orders(self) -> None:
        """حذف الطلبات المختارة"""
        if not self.selected_ids:
            self.notify("Please select orders first", severity="warning")
            return
            
        async def on_confirm():
            count = 0
            for oid in list(self.selected_ids):
                if self.db.delete_order(int(oid)):
                    count += 1
            
            self.selected_ids.clear()
            self.notify(f"Deleted {count} orders")
            self.load_data()
            self.update_delete_button()
            
        await self.app.push_screen(self.create_confirm_dialog(f"Delete {len(self.selected_ids)} orders?", on_confirm))

    def create_confirm_dialog(self, title: str, callback):
        from textual.screen import ModalScreen
        from textual.containers import Container, Horizontal
        class ConfirmDialog(ModalScreen):
            def compose(self):
                with Container(classes="modal-dialog small-modal"):
                    with Horizontal(id="details-header"):
                        yield Static(title, id="details-title")
                        yield Button("X", id="close-x", classes="close-button")
                    with Horizontal(id="dialog-buttons"):
                        yield CustomButton("Delete", id="ok", custom_width=12)
                        yield CustomButton("Cancel", id="cancel", custom_width=12)
            
            def on_mount(self) -> None:
                # ✅ Prevent auto-focus on Close button
                self.set_focus(None)
                self.set_timer(0.1, lambda: self.set_focus(None))
            
            def on_click(self, event) -> None:
                if event.widget == self:
                    self.dismiss()

            async def on_button_pressed(self, event):
                if event.button.id == "ok":
                    await callback()
                elif event.button.id in ["cancel", "close-x"]:
                    self.dismiss()
                self.dismiss()
        return ConfirmDialog()
    
    def create_input_dialog(self, title: str, input_widget, callback):
        from textual.screen import ModalScreen
        from textual.containers import Container, Vertical, Horizontal
        class InputDialog(ModalScreen):
            def compose(self):
                with Container(classes="modal-dialog small-modal"):
                    with Horizontal(id="details-header"):
                        yield Static(title, id="details-title")
                        yield Button("X", id="close-x", classes="close-button")
                    yield input_widget
                    with Horizontal(id="dialog-buttons"):
                        yield CustomButton("OK", id="ok", custom_width=12)
                        yield CustomButton("Cancel", id="cancel", custom_width=12)
            
            def on_mount(self) -> None:
                # ✅ Prevent auto-focus on Close button
                self.set_focus(None)
                self.set_timer(0.1, lambda: self.set_focus(None))
            
            def on_click(self, event) -> None:
                if event.widget == self:
                    self.dismiss()

            async def on_button_pressed(self, event):
                if event.button.id == "ok":
                    await callback()
                    self.dismiss()
                elif event.button.id in ["cancel", "close-x"]:
                    self.dismiss()
                else:
                    self.dismiss()
        return InputDialog()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()
