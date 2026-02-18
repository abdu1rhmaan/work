from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, ListView, Label, ListItem
from textual.reactive import reactive
from textual import events

from ..database import Database
from ..utils import format_arabic
from .window import DraggableWindow
from ..ui.components import CustomButton, OptionSelector, HistoryRow

class OrderDetailsWindow(DraggableWindow):
    """نافذة تفاصيل الطلب (MDI)"""
    def __init__(self, order_data: dict, display_id: int, db=None, refresh_callback=None):
        super().__init__(title=f"ORDER DETAILS #{display_id}")
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
            self.close()
        elif event.button.id == "edit-order":
            from .add_order import AddOrderWindow
            self.close()
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(AddOrderWindow(self.db, self.refresh_callback, order_to_edit=self.order))

class TipDetailsWindow(DraggableWindow):
    """نافذة تفاصيل البقشيش (MDI)"""
    def __init__(self, order_data: dict, display_id: int):
        super().__init__(title=f"TIP DETAILS #{display_id}")
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
            self.close()

class SettlementDetailsWindow(DraggableWindow):
    """نافذة تفاصيل التسوية (MDI)"""
    def __init__(self, order_data: dict, display_id: int):
        super().__init__(title=f"SETTLEMENT DETAILS #{display_id}")
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
            self.close()

class OrderHistoryWindow(DraggableWindow):
    """نافذة سجل الطلبات (MDI)"""
    
    def __init__(self, db: Database):
        super().__init__(title="ORDER HISTORY")
        self.db = db
        self.selected_ids = set()
        self.filter_type = "All"
        self.filter_period = "All"
        self.show_chart_only = False

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

        with Vertical(id="history-content", classes="flex-1"):
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
                yield CustomButton("Delete", id="delete-order", custom_width=12)
                yield CustomButton("Close", id="close-window", custom_width=12)

    def on_mount(self) -> None:
        self.load_data()

    def on_option_selector_selected(self, message: OptionSelector.Selected) -> None:
        if message.selector.id == "filter-type":
            self.filter_type = message.value
        elif message.selector.id == "filter-period":
            self.filter_period = message.value
        self.load_data()

    def load_data(self) -> None:
        # Safety check: ensure history_list is composed
        try:
            list_view = self.query_one("#history-list")
        except:
            return

        if self.filter_type == "Order":
            orders = self.db.get_all_orders(limit=100, order_type="All", period=self.filter_period)
            orders = [o for o in orders if o.get('mode') not in ['SETTLEMENT', 'TIP']]
        elif self.filter_type == "Tips":
            orders = self.db.get_all_orders(limit=100, order_type="All", period=self.filter_period)
            orders = [o for o in orders if o.get('mode') == 'TIP']
        else:
            orders = self.db.get_all_orders(limit=100, order_type=self.filter_type, period=self.filter_period)
        
        list_view.clear()
        
        if not orders:
            self.query_one("#no-orders-msg").remove_class("hidden")
            return
        else:
            self.query_one("#no-orders-msg").add_class("hidden")
            
        for idx, order in enumerate(orders, 1):
            is_selected = str(order['id']) in self.selected_ids
            list_view.append(HistoryRow(order, display_id=idx, is_selected=is_selected))

    def on_history_row_toggle_selection(self, message: HistoryRow.ToggleSelection) -> None:
        order_id = message.order_id
        if order_id in self.selected_ids:
            self.selected_ids.remove(order_id)
        else:
            self.selected_ids.add(order_id)
        self.load_data()
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
            self.load_data()
            if hasattr(self.app.screen, "open_window"):
                if order.get('mode') == 'TIP':
                    self.app.screen.open_window(TipDetailsWindow(order, display_id))
                elif order.get('mode') == 'SETTLEMENT':
                    self.app.screen.open_window(SettlementDetailsWindow(order, display_id))
                else:
                    self.app.screen.open_window(OrderDetailsWindow(order, display_id, self.db, self.load_data))

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        if event.button.id == "close-window":
            self.close()
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
        self.load_data()
        self.update_delete_button()

class ConfirmModal(DraggableWindow):
    def __init__(self, title, callback):
        super().__init__(title="Confirm")
        self.title_text = title
        self.callback = callback
    
    def compose_content(self) -> ComposeResult:
         yield Static(self.title_text, id="details-title")
         with Horizontal(id="dialog-buttons"):
            yield CustomButton("YES", id="ok", classes="button-out", custom_width=12)
            yield CustomButton("NO", id="cancel", custom_width=12)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            if self.callback: self.callback()
            self.close()
        else:
            self.close()
