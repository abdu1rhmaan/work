from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, ListView, Label, ListItem
from textual.reactive import reactive
from textual import events, on
from textual.message import Message

from ..database import Database
from ..utils import format_arabic
from .window import BaseWindow
from .components import CustomButton, OptionSelector, HistoryRow

class OrderDetailsWindow(BaseWindow):
    WINDOW_ID = "order_details"
    """نافذة تفاصيل الطلب (MDI)"""
    WINDOW_ID = "order_details"
    def __init__(self, order_data: dict, display_id: int, db=None, refresh_callback=None):
        super().__init__(title=f"ORDER DETAILS #{display_id}", width=55)  # auto height
        self.order = order_data
        self.display_id = display_id
        self.db = db
        self.refresh_callback = refresh_callback

    def compose_content(self) -> ComposeResult:
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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-details":
            self.remove()
        elif event.button.id == "edit-order":
            from .add_order import AddOrderWindow
            self.remove()
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(AddOrderWindow(self.db, self.refresh_callback, order_to_edit=self.order))

class TipDetailsWindow(BaseWindow):
    WINDOW_ID = "tip_details"
    """نافذة تفاصيل البقشيش (MDI)"""
    WINDOW_ID = "tip_details"
    def __init__(self, order_data: dict, display_id: int):
        super().__init__(title=f"TIP DETAILS #{display_id}", width=50)  # auto height
        self.order = order_data
        self.display_id = display_id

    def compose_content(self) -> ComposeResult:
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-details":
            self.remove()

class SettlementDetailsWindow(BaseWindow):
    WINDOW_ID = "settlement_details"
    """نافذة تفاصيل التسوية (MDI)"""
    def __init__(self, order_data: dict, display_id: int):
        super().__init__(title=f"SETTLEMENT DETAILS #{display_id}", width=55)  # auto height
        self.order = order_data
        self.display_id = display_id

    def compose_content(self) -> ComposeResult:
        with Vertical(id="details-content"):
            yield Static(f"Date: [b]{self.order['datetime']}[/b]")
            direction = "PAY TO COMPANY" if self.order['personal_wallet_effect'] < 0 else "RECEIVE FROM COMPANY"
            yield Static(f"Type: [b]{direction}[/b]")
            yield Static("────────────────────────")
            yield Static(f"Amount: [b]{self.order['actual']:.2f} EGP[/b]")
            yield Static("────────────────────────")
            yield Static(f"Personal Wallet Effect: {self.order['personal_wallet_effect']:+.2f} EGP")
            yield Static(f"Company Wallet Effect:  {self.order['company_wallet_effect']:+.2f} EGP")
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("Close", id="close-details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-details":
            self.remove()


class OrderHistoryWindow(BaseWindow):
    WINDOW_ID = "order_history"
    """نافذة سجل الطلبات (MDI)"""
    
    def __init__(self, db: Database, chart_only=False):
        if chart_only:
            super().__init__(title="ANALYSIS", width=70, height=25)
        else:
            super().__init__(title="ORDER HISTORY", width=75, height=28)
        self.db = db
        self.show_chart_only = chart_only
        self.selected_ids = set()
        self.filter_type = "All"
        self.filter_period = "All"

    def compose_content(self) -> ComposeResult:
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

        with Vertical(id="history-content"):
            with Horizontal(id="history-header", classes="table-header"):
                yield Label("✓", classes="col-sel")
                yield Label("ID", classes="col-id")
                yield Label("Date", classes="col-date")
                yield Label("Type", classes="col-type")
                yield Label("Profit", classes="col-profit")
            
            self.history_list = ListView(id="history-list")
            yield self.history_list
            yield Static("No orders found", id="no-orders-msg", classes="no-data-msg hidden")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Delete", id="delete-order")
                yield CustomButton("Close", id="close-window")

    def on_mount(self) -> None:
        self.call_after_refresh(self._do_load_data)

    async def _do_load_data(self):
        await self.load_data()

    # 🚀 REAL-TIME UPDATES: Listen for changes elsewhere
    @on(BaseWindow.OrderAdded)
    @on(BaseWindow.DataChanged)
    async def handle_data_update(self) -> None:
        """Debounced load to prevent freezes during rapid data changes."""
        self.set_timer(0.3, self._do_load_data)

    async def on_option_selector_selected(self, message: OptionSelector.Selected) -> None:
        if message.selector.id == "filter-type":
            self.filter_type = message.value
        elif message.selector.id == "filter-period":
            self.filter_period = message.value
        await self.load_data()

    async def load_data(self) -> None:
        # Safety check: ensure history_list is composed
        try:
            list_view = self.query_one("#history-list")
        except:
            return

        # Pass filter directly to DB which now handles it correctly
        try:
            orders = self.db.get_all_orders(limit=100, order_type=self.filter_type, period=self.filter_period)
        except Exception as e:
            orders = []
            self.notify(f"Error loading orders: {e}")
        
        await list_view.clear()
        
        if not orders:
            self.query_one("#no-orders-msg").remove_class("hidden")
            return
        else:
            self.query_one("#no-orders-msg").add_class("hidden")
            
        to_mount = []
        for idx, order in enumerate(orders, 1):
            is_selected = str(order['id']) in self.selected_ids
            to_mount.append(HistoryRow(order, display_id=idx, is_selected=is_selected))
            
        if to_mount:
            await list_view.mount(*to_mount)

    async def on_history_row_toggle_selection(self, message: HistoryRow.ToggleSelection) -> None:
        order_id = message.order_id
        if order_id in self.selected_ids:
            self.selected_ids.remove(order_id)
        else:
            self.selected_ids.add(order_id)
        await self.load_data()
        self.update_delete_button()

    def update_delete_button(self):
        btn = self.query_one("#delete-order")
        count = len(self.selected_ids)
        btn.label = f"Delete ({count})" if count > 0 else "Delete"

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None: return
        row = event.item
        if not hasattr(row, "order_id"): return
        
        order_id = row.order_id
        display_id = row.display_id
        
        if order_id in self.selected_ids:
            self.selected_ids.remove(order_id)
            self.update_delete_button()
            
        order = self.db.get_order_by_id(int(order_id))
        if order:
            await self.load_data()
            if hasattr(self.app.screen, "open_window"):
                if order.get('mode') == 'TIP':
                    self.app.screen.open_window(TipDetailsWindow(order, display_id))
                elif order.get('mode') == 'SETTLEMENT':
                    self.app.screen.open_window(SettlementDetailsWindow(order, display_id))
                else:
                    self.app.screen.open_window(OrderDetailsWindow(order, display_id, self.db, self._do_load_data))

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        if event.button.id == "close-window":
            self.remove()
        elif event.button.id == "delete-order":
            await self.delete_selected_orders()

    async def delete_selected_orders(self) -> None:
        if not self.selected_ids:
            self.notify("Please select orders first", severity="warning")
            return
        
        if hasattr(self.app.screen, "open_window"):
             self.app.screen.open_window(ConfirmModal(f"Delete {len(self.selected_ids)} orders?", self.perform_delete))

    def perform_delete(self):
        count = 0
        for oid in list(self.selected_ids):
            if self.db.delete_order(int(oid)):
                count += 1
        self.selected_ids.clear()
        self.notify(f"Deleted {count} orders")
        # 🚀 Broadcast update
        self.post_message(self.DataChanged())
        self.load_data()
        self.update_delete_button()

class AnalysisWindow(BaseWindow):
    WINDOW_ID = "analysis"
    """نافذة تحليل الأداء (MDI)"""
    def __init__(self, db):
        super().__init__(title="PERFORMANCE ANALYSIS", width=70)
        self.db = db

    def compose_content(self) -> ComposeResult:
        with Vertical(id="analysis-container"):
            yield Static(id="analysis-view")
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="close-analysis")

    def on_mount(self) -> None:
        self.refresh_analysis()

    def refresh_analysis(self) -> None:
        try:
            stats = self.db.get_analysis_stats()
            # Simple summary for now, can be expanded
            content = f"""
[b green]Financial Summary[/b green]
────────────────────────
Total Income:   {stats.get('total_income', 0):.2f} EGP
Total Expenses: {stats.get('total_expenses', 0):.2f} EGP
Total Tips:     {stats.get('total_tips', 0):.2f} EGP
────────────────────────
[b cyan]Net Profit:    {stats.get('net_profit', 0):.2f} EGP[/b cyan]
"""
            self.query_one("#analysis-view").update(content)
        except Exception as e:
            self.query_one("#analysis-view").update(f"Error loading stats: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-analysis":
            self.remove()

class ConfirmModal(BaseWindow):
    WINDOW_ID = "confirm_modal"
    def __init__(self, title, callback):
        super().__init__(title="Confirm", width=45)
        self.title_text = title
        self.callback = callback
    
    def compose_content(self) -> ComposeResult:
         yield Static(self.title_text, id="details-title")
         with Horizontal(id="dialog-buttons"):
            yield CustomButton("YES", id="ok", classes="button-out")
            yield CustomButton("NO", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            if self.callback: self.callback()
            self.remove()
        else:
            self.remove()
