from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, Input, ListView, ListItem, OptionList, Button
from textual import events, on
from .components import CustomButton, WalletDisplay, ArabicInput
from ..utils import format_arabic
from typing import Optional, Callable
from .window import BaseWindow

class EditTransactionWindow(BaseWindow):
    WINDOW_ID = "edit_transaction"
    """نافذة تعديل المعاملة"""
    def __init__(self, db, txn_id: int, current_desc: str, current_amount: float, current_type: str, callback=None):
        super().__init__(title="EDIT TRANSACTION", id="edit-txn-window", width=55)  # auto height
        self.db = db
        self.txn_id = txn_id
        self.current_desc = current_desc
        self.current_amount = current_amount
        self.current_type = current_type
        self.callback = callback
        self.txn_type = current_type

    def compose_content(self) -> ComposeResult:
        with Vertical(id="edit-content"):
            type_label = "Type: INCOME" if self.txn_type == "IN" else "Type: EXPENSE"
            type_class = "button-in" if self.txn_type == "IN" else "button-out"
            yield CustomButton(type_label, id="toggle-type", classes=type_class)
            
            yield ArabicInput(value=self.current_desc, placeholder="Description", id="edit-desc")
            yield ArabicInput(value=str(self.current_amount), placeholder="Amount", id="edit-amount", min_value=0)
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Save", id="save-edit", custom_width=12)
                yield CustomButton("Cancel", id="cancel-edit", custom_width=12)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle-type":
            if self.txn_type == "OUT":
                self.txn_type = "IN"
                event.button.label = "Type: INCOME"
                event.button.remove_class("button-out")
                event.button.add_class("button-in")
            else:
                self.txn_type = "OUT"
                event.button.label = "Type: EXPENSE"
                event.button.remove_class("button-in")
                event.button.add_class("button-out")
                
        elif event.button.id == "save-edit":
            await self.save_changes()
        elif event.button.id == "cancel-edit":
            self.close()

    async def save_changes(self) -> None:
        desc = self.query_one("#edit-desc").value.strip()
        amount_str = self.query_one("#edit-amount").value.strip()
        
        if not desc or not amount_str:
            self.notify("Invalid fields", severity="error")
            return
            
        try:
            amount = float(amount_str)
            if self.db.update_expense(self.txn_id, desc, amount, self.txn_type):
                self.notify("Transaction updated!")
                # 🚀 Broadcast update
                self.post_message(self.DataChanged())
                if self.callback: self.callback()
                self.close()
            else:
                self.notify("Failed to update", severity="error")
        except ValueError:
            self.notify("Invalid amount", severity="error")

class ConfirmDeleteWindow(BaseWindow):
    WINDOW_ID = "confirm_delete"
    """نافذة تأكيد الحذف"""
    def __init__(self, db, txn_id: int, callback=None):
        super().__init__(title="DELETE TRANSACTION?", id="confirm-delete-window", width=50)  # auto height
        self.db = db
        self.txn_id = txn_id
        self.callback = callback

    def compose_content(self) -> ComposeResult:
        yield Static("\nAre you sure you want to delete this transaction?\n", classes="warning-text")
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("YES", id="confirm-delete", classes="button-out", custom_width=14)
            yield CustomButton("NO", id="cancel-delete", custom_width=12)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-delete":
            if self.db.delete_expense(self.txn_id):
                self.notify("Transaction deleted!")
                # 🚀 Broadcast update
                self.post_message(self.DataChanged())
                if self.callback: self.callback()
                self.close()
            else:
                self.notify("Failed to delete", severity="error")
                self.close()
        elif event.button.id == "cancel-delete":
            self.close()

class TransactionDetailsWindow(BaseWindow):
    WINDOW_ID = "transaction_details"
    """نافذة تفاصيل المعاملة"""
    def __init__(self, db, txn: dict, callback=None):
        title = "TRANSACTION DETAILS"
        super().__init__(title=title, id="txn-details-window", width=50)  # auto height
        self.db = db
        self.txn = txn
        self.callback = callback
        self.txn_id = txn['id']

    def compose_content(self) -> ComposeResult:
        with Vertical(id="txn-details-content"):
            yield Label(f"Date: {self.txn['datetime']}")
            type_name = "Income" if self.txn['type'] == 'IN' else "Expense"
            yield Label(format_arabic(f"Type: {type_name}"))
            yield Label(format_arabic(f"Description: {self.txn['description']}"))
            yield Label(f"Amount: {self.txn['amount']:.2f} EGP", id="details-amount-text")
        
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("Edit", id="edit-txn", custom_width=12)
            yield CustomButton("Delete", id="delete-txn", classes="button-out", custom_width=12)
            yield CustomButton("Close", id="close-txn-details", custom_width=12)

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        if event.button.id == "close-txn-details":
            self.close()
        elif event.button.id == "delete-txn":
            self.close()
            # Open confirm delete window
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(ConfirmDeleteWindow(self.db, self.txn_id, self.callback))
        elif event.button.id == "edit-txn":
            self.close()
            # Open edit window
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(
                    EditTransactionWindow(
                        self.db, 
                        self.txn_id, 
                        self.txn['description'], 
                        self.txn['amount'], 
                        self.txn['type'], 
                        self.callback
                    )
                )

class ExpenseRow(ListItem):
    """سطر لعرض مصروف واحد"""
    def __init__(self, expense: dict, **kwargs):
        super().__init__(**kwargs)
        self.expense = expense
        self.add_class("expense-row")

    def compose(self) -> ComposeResult:
        txn_type = self.expense.get('type', 'OUT')
        txn_char = "+" if txn_type == 'IN' else "-"
        txn_class = "txn-in" if txn_type == 'IN' else "txn-out"
        
        with Horizontal(classes=f"expense-row-content {txn_class}"):
            yield Label(self.expense['datetime'][11:16], classes="expense-date")
            desc = self.expense.get('description', 'No Desc')
            yield Label(format_arabic(desc), classes="expense-desc")
            # The color is now controlled by CSS .txn-in / .txn-out classes
            yield Label(f"{txn_char} {self.expense.get('amount', 0.0):.2f}", classes="expense-amount")

class WalletWindow(BaseWindow):
    WINDOW_ID = "wallet"
    """نافذة المحفظة الرئيسية"""
    def __init__(self, db, on_close: Optional[Callable] = None):
        super().__init__(title="WALLET", width=75, height=30)  # 💌 Keep height for scrollable list
        self.db = db
        self.on_close = on_close
        self.txn_type = 'OUT'
        self._selecting_suggestion = False

    def compose_content(self) -> ComposeResult:
        settings = self.db.get_settings()
        
        with Vertical(id="wallet-content"):
            self.stats_display = Static(id="wallet-stats-bar")
            yield self.stats_display
            
            # Combine balances into a single horizontal row
            with Horizontal(id="wallets-horizontal"):
                yield WalletDisplay("Personal Balance", settings['personal_wallet'], id="wallet-personal")
                yield WalletDisplay("Company Balance", settings['company_wallet'], id="wallet-company")
            
            with Vertical(id="expense-form"):
                with Horizontal(id="txn-type-toggle"):
                    yield CustomButton("Type: EXPENSE", id="toggle-txn-type", custom_width=16)
                
                yield ArabicInput(placeholder="Description", id="expense-desc", required=True)
                yield ArabicInput(placeholder="Amount", id="expense-amount", required=True, min_value=0)
                
                with Horizontal(id="expense-buttons"):
                    yield CustomButton("Save", id="save-expense", custom_width=12)
            
            self.expense_list = ListView(id="expense-list")
            yield self.expense_list
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Close", id="back", custom_width=14)
        
        # Suggestions (Overlay handled by OptionList usually, but inside window might be tricky)
        # We place it here; exact positioning depends on CSS or Textual's overlay
        self.suggestions_list = OptionList(id="suggestion-list")
        self.suggestions_list.display = "none"
        yield self.suggestions_list

    def on_mount(self) -> None:
        self.call_after_refresh(self._do_load_data)

    async def _do_load_data(self):
        await self.load_data()

    async def load_data(self) -> None:
        stats = self.db.get_wallet_stats()
        stats_text = f"In: [b green]{stats['total_in']:.2f}[/] | Out: [b red]{stats['total_out']:.2f}[/] | Net: [b]{stats['net']:.2f}[/]"
        self.query_one("#wallet-stats-bar").update(stats_text)

        expenses = self.db.get_all_expenses(limit=15)
        await self.expense_list.clear() # Making this async
        to_mount = [ExpenseRow(exp) for exp in expenses]
        await self.expense_list.mount(*to_mount)
            
        settings = self.db.get_settings()
        self.query_one("#wallet-personal").value = settings['personal_wallet']
        self.query_one("#wallet-company").value = settings['company_wallet']

    # 🚀 REAL-TIME UPDATES: Listen for changes from other windows
    @on(BaseWindow.OrderAdded)
    @on(BaseWindow.DataChanged)
    async def handle_data_update(self) -> None:
        """Update transaction list instantly when an order or txn is added elsewhere"""
        await self.load_data()

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        if isinstance(message.item, ExpenseRow):
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(
                    TransactionDetailsWindow(self.db, message.item.expense, callback=self.load_data)
                )

    def on_input_changed(self, event: Input.Changed) -> None:
        """تحديث الاقتراحات"""
        # Logic copied from original
        if self._selecting_suggestion:
            self._selecting_suggestion = False
            return

        if event.input.id == "expense-desc":
            prefix = event.value.strip()
            if len(prefix) >= 1:
                suggestions = self.db.get_unique_descriptions(prefix)
                if suggestions:
                    self.suggestions_list.clear_options()
                    for s in suggestions:
                        self.suggestions_list.add_option(format_arabic(s))
                    self.suggestions_list.display = "block"
                else:
                    self.suggestions_list.display = "none"
            else:
                self.suggestions_list.display = "none"

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "suggestion-list":
            self._selecting_suggestion = True
            desc_input = self.query_one("#expense-desc")
            self.suggestions_list.display = "none"
            self.suggestions_list.clear_options()
            desc_input.value = str(event.option.prompt)
            self.query_one("#expense-amount").focus()

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "toggle-txn-type":
            if self.txn_type == "OUT":
                self.txn_type = "IN"
                event.button.label = "Type: INCOME"
                event.button.remove_class("button-out")
                event.button.add_class("button-in")
            else:
                self.txn_type = "OUT"
                event.button.label = "Type: EXPENSE"
                event.button.remove_class("button-in")
                event.button.add_class("button-out")

        elif button_id == "save-expense":
            await self.save_expense()
                
        elif button_id == "back":
            if self.on_close:
                self.on_close()
            self.close()

    async def save_expense(self) -> None:
        desc_input = self.query_one("#expense-desc")
        amount_input = self.query_one("#expense-amount")
        
        description = desc_input.value.strip()
        amount_str = amount_input.value.strip()
        
        is_desc_valid = desc_input.validate_input()
        is_amount_valid = amount_input.validate_input()
        
        if not is_desc_valid or not is_amount_valid:
             self.notify("Please fill required fields", severity="error")
             return

        try:
             amount = float(amount_str)
             if self.db.add_expense(description, amount, self.txn_type):
                 self.notify("Saved!")
                 desc_input.value = ""
                 amount_input.value = ""
                 self.suggestions_list.display = "none"
                 await self.load_data()
                 # 🚀 Broadcast my own update too
                 self.post_message(self.DataChanged())
             else:
                 self.notify("Error saving", severity="error")
        except ValueError:
             self.notify("Invalid amount", severity="error")
