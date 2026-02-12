from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, Input, ListView, ListItem, OptionList, Button
from textual import events
from .components import CustomButton, WalletDisplay, ArabicInput
from ..utils import format_arabic
from datetime import datetime
from typing import Optional, Callable

class EditTransactionScreen(ModalScreen):
    """شاشة تعديل المعاملة"""
    def __init__(self, db, txn_id: int, current_desc: str, current_amount: float, current_type: str, callback=None):
        super().__init__()
        self.db = db
        self.txn_id = txn_id
        self.current_desc = current_desc
        self.current_amount = current_amount
        self.current_type = current_type
        self.callback = callback
        self.txn_type = current_type

    def compose(self) -> ComposeResult:
        with Container(id="expense-form", classes="modal-dialog small-modal"):
            yield Static("EDIT TRANSACTION", id="title")
            
            with Vertical(id="edit-content"):
                # نوع العملية (زر تبديل)
                type_label = "Type: INCOME" if self.txn_type == "IN" else "Type: EXPENSE"
                type_class = "button-in" if self.txn_type == "IN" else "button-out"
                yield CustomButton(type_label, id="toggle-type", classes=type_class)
                
                yield ArabicInput(value=self.current_desc, placeholder="Description", id="edit-desc")
                yield Input(value=str(self.current_amount), placeholder="Amount", id="edit-amount", type="number")
                
                with Horizontal(id="dialog-buttons"):
                    yield CustomButton("Save", id="save-edit", custom_width=12)
                    yield CustomButton("Cancel", id="cancel-edit", custom_width=12)

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

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
            self.dismiss()

    async def save_changes(self) -> None:
        desc_input = self.query_one("#edit-desc")
        amount_input = self.query_one("#edit-amount")
        
        desc = desc_input.value.strip()
        amount_str = amount_input.value.strip()
        
        has_error = False
        
        if not desc:
            desc_input.add_class("invalid")
            has_error = True
        else:
            desc_input.remove_class("invalid")
            
        if not amount_str:
            amount_input.add_class("invalid")
            has_error = True
        else:
            try:
                float(amount_str) # Check if valid number
                amount_input.remove_class("invalid")
            except ValueError:
                amount_input.add_class("invalid")
                has_error = True

        if has_error:
            self.notify("Please check the highlighted fields", severity="error")
            return
            
        try:
            amount = float(amount_str)
            if self.db.update_expense(self.txn_id, desc, amount, self.txn_type):
                self.notify("Transaction updated!")
                if self.callback: self.callback()
                self.dismiss()
            else:
                self.notify("Failed to update", severity="error")
        except ValueError:
            self.notify("Invalid amount", severity="error")

class ConfirmDeleteScreen(ModalScreen):
    """شاشة تأكيد الحذف"""
    def __init__(self, db, txn_id: int, callback=None):
        super().__init__()
        self.db = db
        self.txn_id = txn_id
        self.callback = callback

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog small-modal"):
            yield Static("DELETE TRANSACTION?", id="title")
            yield Static("\nAre you sure you want to delete this transaction?\n", classes="warning-text")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("YES, DELETE", id="confirm-delete", classes="button-out", custom_width=16)
                yield CustomButton("CANCEL", id="cancel-delete", custom_width=12)

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-delete":
            if self.db.delete_expense(self.txn_id):
                self.notify("Transaction deleted!")
                if self.callback: self.callback()
                self.dismiss()
            else:
                self.notify("Failed to delete", severity="error")
                self.dismiss()
        elif event.button.id == "cancel-delete":
            self.dismiss()

class TransactionDetailsScreen(ModalScreen):
    """شاشة تفاصيل المعاملة"""
    def __init__(self, db, txn: dict, callback=None):
        super().__init__()
        self.db = db
        self.txn = txn
        self.callback = callback
        self.txn_id = txn['id']

    def compose(self) -> ComposeResult:
        txn_class = "txn-details-in" if self.txn['type'] == 'IN' else "txn-details-out"
        with Container(id="txn-details-dialog", classes=f"modal-dialog {txn_class}"):
            yield Static("TRANSACTION DETAILS", id="title")
            
            with Vertical(id="txn-details-content"):
                yield Label(f"Date: {self.txn['datetime']}")
                type_name = "Income" if self.txn['type'] == 'IN' else "Expense"
                yield Label(format_arabic(f"Type: {type_name}"))
                yield Label(format_arabic(f"Description: {self.txn['description']}"))
                
                # إضافة كلاس للمبلغ للتلوين
                yield Label(f"Amount: {self.txn['amount']:.2f} EGP", id="details-amount-text")
            
            # أزرار التحكم (Grid)
            # تم طلب: Edit, Delete, Close بجانب بعض
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Edit", id="edit-txn", custom_width=12)
                yield CustomButton("Delete", id="delete-txn", custom_width=12)
                yield CustomButton("Close", id="close-txn-details", custom_width=12)

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        if event.button.id == "close-txn-details":
            self.dismiss()
        elif event.button.id == "delete-txn":
            # إغلاق هذه الشاشة وفتح تأكيد الحذف
            self.dismiss()
            await self.app.push_screen(ConfirmDeleteScreen(self.db, self.txn_id, self.callback))
        elif event.button.id == "edit-txn":
            # إغلاق هذه الشاشة وفتح التعديل
            self.dismiss()
            await self.app.push_screen(
                EditTransactionScreen(
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

    def compose(self) -> ComposeResult:
        # استخدام .get للمسابقة مع البيانات القديمة التي قد تفتقد لعمود type
        txn_type = self.expense.get('type', 'OUT')
        txn_char = "+" if txn_type == 'IN' else "-"
        txn_class = "txn-in" if txn_type == 'IN' else "txn-out"
        
        with Horizontal(classes=f"expense-row-content {txn_class}"):
            yield Label(self.expense['datetime'][11:16], classes="expense-date")
            desc = self.expense.get('description', 'No Desc')
            yield Label(format_arabic(desc), classes="expense-desc")
            yield Label(f"{txn_char} {self.expense.get('amount', 0.0):.2f}", classes="expense-amount")

class WalletScreen(ModalScreen):
    """شاشة المحفظة والمصاريف المتطورة"""
    def __init__(self, db, on_close: Optional[Callable] = None):
        super().__init__()
        self.db = db
        self.on_close = on_close
        self.txn_type = 'OUT' # الافتراضي هو مصاريف
        self._selecting_suggestion = False
        
    def compose(self) -> ComposeResult:
        settings = self.db.get_settings()
        
        with Container(id="wallet-dialog", classes="modal-dialog"):
            yield Static("WALLET & PERSONAL ACCOUNTING", id="title")
            
            with Vertical(id="wallet-content"):
                # ملخص سريع للحساب الشخصي
                self.stats_display = Static(id="wallet-stats-bar")
                yield self.stats_display

                # عرض الأرصدة الحالية
                with Horizontal(id="wallet-info-row"):
                    yield WalletDisplay("Personal Balance", settings['personal_wallet'], id="wallet-personal")
                    yield WalletDisplay("Company Balance", settings['company_wallet'], id="wallet-company")
                
                yield Static(classes="divider")
                
                # إضافة عملية جديدة
                yield Static("Record New Transaction", classes="section-title")
                with Vertical(id="expense-form"):
                    with Horizontal(id="txn-type-toggle"):
                        yield CustomButton("Type: EXPENSE", id="toggle-txn-type", custom_width=16)
                    
                    yield ArabicInput(placeholder="Description (e.g. Lunch or Bonus)", id="expense-desc", required=True)
                    yield ArabicInput(placeholder="Amount", id="expense-amount", required=True, min_value=0)
                    
                    with Horizontal(id="expense-buttons"):
                        yield CustomButton("Save", id="save-expense", custom_width=12)
                
                yield Static(classes="divider")
                
                # تاريخ المصاريف
                yield Static("Transaction History", classes="section-title")
                self.expense_list = ListView(id="expense-list")
                yield self.expense_list
                
                with Horizontal(id="dialog-buttons"):
                    yield CustomButton("Back", id="back", custom_width=12)
            
            # حاوية الاقتراحات - عائمة في طبقة منفصلة
            self.suggestions_list = OptionList(id="suggestion-list")
            self.suggestions_list.display = False
            yield self.suggestions_list

    def on_click(self, event) -> None:
        if event.widget == self:
            if self.on_close:
                self.on_close()
            self.dismiss()

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        """تحميل المصاريف السابقة والإحصائيات"""
        # تحديث الإحصائيات
        stats = self.db.get_wallet_stats()
        stats_text = f"Total In: [b green]{stats['total_in']:.2f}[/b green] | Total Out: [b red]{stats['total_out']:.2f}[/b red] | Net: [b]{stats['net']:.2f}[/b]"
        self.query_one("#wallet-stats-bar").update(stats_text)

        # تحميل التاريخ
        expenses = self.db.get_all_expenses(limit=20)
        self.expense_list.clear()
        for exp in expenses:
            self.expense_list.append(ExpenseRow(exp))
            
        # تحديث الأرصدة المعروضة أيضاً إذا تغيرت
        settings = self.db.get_settings()
        self.query_one("#wallet-personal").value = settings['personal_wallet']
        self.query_one("#wallet-company").value = settings['company_wallet']

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """عند الضغط على عنصر في التاريخ"""
        if isinstance(message.item, ExpenseRow):
            # نمرر self.load_data كـ callback ليتم تحديث القائمة عند العودة من الحذف/التعديل
            self.app.push_screen(TransactionDetailsScreen(self.db, message.item.expense, callback=self.load_data))

    def on_input_changed(self, event: Input.Changed) -> None:
        """تحديث الاقتراحات عند الكتابة"""
        # إذا كنا بصدد اختيار اقتراح، نتجاهل هذا الحدث لمنع القائمة من الظهور مرة أخرى
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
                    self.suggestions_list.display = True
                else:
                    self.suggestions_list.display = False
            else:
                self.suggestions_list.display = False

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """عند اختيار اقتراح من القائمة"""
        if event.option_list.id == "suggestion-list":
            self._selecting_suggestion = True
            desc_input = self.query_one("#expense-desc")
            
            # إخفاء القائمة فوراً ومسحها
            self.suggestions_list.display = False
            self.suggestions_list.clear_options()
            
            # تحديث القيمة (سيؤدي ذلك لإرسال حدث Changed)
            selected_text = str(event.option.prompt)
            desc_input.value = selected_text
            
            # نقل التركيز للمبلغ
            self.query_one("#expense-amount").focus()
            
            # لا نقم بتصفير العلم فوراً لأن الحدث قد يكون في الطابور
            # سيتم تصفيره في on_input_changed عند أول تغيير حقيقي

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
            desc_input = self.query_one("#expense-desc")
            amount_input = self.query_one("#expense-amount")
            
            # التحقق من صحة الحقول قبل الحفظ
            if not desc_input.validate_input() or not amount_input.validate_input():
                self.app.notify("Please fill all fields with valid data", severity="error")
                return
                
            description = desc_input.value.strip()
            amount_str = amount_input.value.strip()
            
            if not description or not amount_str:
                self.app.notify("Please fill all fields", severity="error")
                return
                
            try:
                amount = float(amount_str)
                if self.db.add_expense(description, amount, self.txn_type):
                    self.app.notify("Transaction recorded!")
                    desc_input.value = ""
                    amount_input.value = ""
                    desc_input.remove_class("invalid")
                    amount_input.remove_class("invalid")
                    self.suggestions_list.display = False
                    self.load_data()
                else:
                    self.app.notify("Failed to save transaction", severity="error")
            except ValueError:
                self.app.notify("Invalid amount", severity="error")
                
        elif button_id == "back":
            if self.on_close:
                self.on_close()
            self.dismiss()
