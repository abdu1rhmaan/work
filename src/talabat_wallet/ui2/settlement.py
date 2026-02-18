import json
from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static
from .window import DraggableWindow
from ..ui.components import CustomButton, ArabicInput
from ..engine import AccountingEngine

class ManualSettlementWindow(DraggableWindow):
    """نافذة التسوية اليدوية (MDI)"""
    def __init__(self, callback=None):
        super().__init__(title="MANUAL SETTLEMENT")
        self.callback = callback
        self.mode = "PAY"

    def compose_content(self) -> ComposeResult:
        with Horizontal(id="mode-selection"):
            yield CustomButton("I pay", id="pay-mode", custom_width=14, classes="active" if self.mode == "PAY" else "")
            yield CustomButton("Company", id="receive-mode", custom_width=14, classes="active" if self.mode == "RECEIVE" else "")
        with Vertical(classes="input-group"):
            yield Static("Amount:")
            self.amount_input = ArabicInput(placeholder="0.0")
            yield self.amount_input
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("Confirm", id="confirm-manual")
            yield CustomButton("Cancel", id="cancel-manual")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pay-mode":
            self.mode = "PAY"
            self.query_one("#pay-mode").add_class("active")
            self.query_one("#receive-mode").remove_class("active")
        elif event.button.id == "receive-mode":
            self.mode = "RECEIVE"
            self.query_one("#receive-mode").add_class("active")
            self.query_one("#pay-mode").remove_class("active")
        elif event.button.id == "confirm-manual":
            try:
                val = float(self.amount_input.value or 0)
                if val <= 0: return
                if self.callback: self.callback(self.mode, val)
                self.close()
            except: pass
        elif event.button.id == "cancel-manual":
            self.close()

class SettlementWindow(DraggableWindow):
    """نافذة التسوية (MDI)"""
    def __init__(self, db, callback=None):
        super().__init__(title="SETTLEMENT")
        self.db = db
        self.callback = callback
        self.settings = self.db.get_settings()
        self.receive_mode = "NORMAL"
        self.settlement_results = None

    def compose_content(self) -> ComposeResult:
        company_balance = self.settings['company_wallet']
        balance_status = "Company owes you" if company_balance > 0 else "You owe company"
        yield Static(f"{balance_status}: {abs(company_balance):.2f} EGP", id="balance-info")
        yield Static("Amount / Salary Received:")
        self.amount_input = ArabicInput(placeholder="0.0", id="settlement-amount")
        yield self.amount_input
        yield Static("Transaction Direction:")
        self.direction_toggle = CustomButton("PAY TO COMPANY", id="direction-toggle", custom_width=25)
        yield self.direction_toggle
        with Vertical(id="receive-mode-group"):
            yield Static("Receive Mode:")
            with Horizontal(id="mode-buttons"):
                self.normal_btn = CustomButton("Normal", id="mode-normal", custom_width=12, classes="active")
                self.salary_btn = CustomButton("Salary", id="mode-salary", custom_width=12)
                yield self.normal_btn
                yield self.salary_btn
        with Vertical(id="confirmation-box", classes="hidden"):
            yield Static("", id="confirm-details")
            yield Static("", id="confirm-result")
        yield Static("", id="effect-preview")
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("Process", id="process-settlement")
            self.manual_btn = CustomButton("Manual", id="manual-settlement", classes="hidden")
            yield self.manual_btn
            yield CustomButton("Close", id="close-settlement")

    def on_mount(self) -> None:
        self.update_ui_state()
        self.update_preview()

    def update_ui_state(self) -> None:
        is_receive = "RECEIVE" in self.direction_toggle.label.plain
        self.query_one("#receive-mode-group").display = is_receive
        if not is_receive: self.receive_mode = "NORMAL"
        if self.receive_mode == "NORMAL":
            self.normal_btn.add_class("active"); self.salary_btn.remove_class("active")
            self.query_one("#confirmation-box").add_class("hidden")
            self.manual_btn.add_class("hidden")
        else:
            self.salary_btn.add_class("active"); self.normal_btn.remove_class("active")
            self.query_one("#confirmation-box").remove_class("hidden")
            self.manual_btn.remove_class("hidden")

    def update_preview(self) -> None:
        try:
            amount = float(self.amount_input.value or 0)
            balance = self.settings['company_wallet']
            if self.receive_mode == "SALARY":
                res = AccountingEngine.calculate_salary_settlement(amount, balance)
                self.settlement_results = res
                self.query_one("#confirm-details").update(f"Salary: {amount:.2f} | Balance: {balance:.2f}")
                self.query_one("#confirm-result").update(res['result_text'])
                self.query_one("#effect-preview").update("")
            else:
                self.query_one("#effect-preview").update(f"New Balance: {balance - amount:.2f} EGP")
        except: self.query_one("#effect-preview").update("Invalid number")

    async def on_input_changed(self, event: ArabicInput.Changed) -> None:
        if event.input.id == "settlement-amount": self.update_preview()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "direction-toggle":
            current = self.direction_toggle.label.plain
            self.direction_toggle.label = "RECEIVE FROM COMPANY" if "PAY" in current else "PAY TO COMPANY"
            self.update_ui_state(); self.update_preview()
        elif event.button.id == "mode-normal":
            self.receive_mode = "NORMAL"; self.update_ui_state(); self.update_preview()
        elif event.button.id == "mode-salary":
            self.receive_mode = "SALARY"; self.update_ui_state(); self.update_preview()
        elif event.button.id == "process-settlement":
            await self.process()
        elif event.button.id == "manual-settlement":
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(ManualSettlementWindow(self.on_manual_done))
        elif event.button.id == "close-settlement":
            self.close()

    def on_manual_done(self, mode, amount):
        p_effect = -amount if mode == "PAY" else amount
        self.db.add_order({
            'datetime': datetime.now().isoformat(), 'mode': 'SETTLEMENT', 'order_type': 'Settlement',
            'subtype': 'manual', 'paid': 0, 'expected': 0, 'actual': amount,
            'tip_cash': 0, 'tip_visa': 0, 'delivery_fee': 0,
            'personal_wallet_effect': p_effect, 'company_wallet_effect': 0,
            'metadata': json.dumps({"manual_mode": mode})
        })
        if self.callback: self.callback()
        self.close()

    async def process(self) -> None:
        try:
            amount = float(self.amount_input.value or 0)
            if self.receive_mode == "SALARY":
                res = self.settlement_results
                p_effect, c_effect, subtype = res['personal_effect'], res['company_effect'], 'salary'
            else:
                p_effect = -amount if "PAY" in self.direction_toggle.label.plain else amount
                c_effect, subtype = -amount, 'normal'
            
            self.db.add_order({
                'datetime': datetime.now().isoformat(), 'mode': 'SETTLEMENT', 'order_type': 'Settlement',
                'subtype': subtype, 'paid': 0, 'expected': 0, 'actual': amount,
                'tip_cash': 0, 'tip_visa': 0, 'delivery_fee': 0,
                'personal_wallet_effect': p_effect, 'company_wallet_effect': c_effect
            })
            if self.callback: self.callback()
            self.close()
        except Exception as e: self.notify(str(e), severity="error")
