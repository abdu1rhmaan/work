import json
from datetime import datetime
from typing import Dict, Any, Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static
from textual import events

from ..database import Database
from ..engine import AccountingEngine
from .components import CustomButton, ArabicInput

class ManualSettlementDialog(ModalScreen):
    """نافذة التسوية اليدوية المصغرة (Step D)"""
    
    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback
        self.mode = "PAY" # PAY or RECEIVE

    def compose(self) -> ComposeResult:
        with Container(id="manual-settlement-dialog", classes="modal-dialog"):
            with Horizontal(id="details-header"):
                yield Static("MANUAL SETTLEMENT", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="manual-content"):
                with Horizontal(id="mode-selection"):
                    yield CustomButton("I pay", id="pay-mode", custom_width=14, classes="active" if self.mode == "PAY" else "")
                    yield CustomButton("Company", id="receive-mode", custom_width=14, classes="active" if self.mode == "RECEIVE" else "")
                
                with Vertical(classes="input-group"):
                    yield Static("Amount:")
                    self.amount_input = ArabicInput(placeholder="0.0")
                    yield self.amount_input

            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Confirm", id="confirm", custom_width=14)
                yield CustomButton("Cancel", id="back", custom_width=14)

    def on_mount(self) -> None:
        self.amount_input.focus()

    def on_click(self, event: events.Click) -> None:
        if event.widget == self:
            self.dismiss()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["back", "close-x"]:
            self.dismiss()
        elif event.button.id == "pay-mode":
            self.mode = "PAY"
            self.query_one("#pay-mode").add_class("active")
            self.query_one("#receive-mode").remove_class("active")
        elif event.button.id == "receive-mode":
            self.mode = "RECEIVE"
            self.query_one("#receive-mode").add_class("active")
            self.query_one("#pay-mode").remove_class("active")
        elif event.button.id == "confirm":
            try:
                val = float(self.amount_input.value or 0)
                if val <= 0: return
                if self.callback:
                    self.callback(self.mode, val)
                self.dismiss()
            except:
                pass


class SettlementScreen(ModalScreen):
    """شاشة التسوية كـ Popup مطورة"""
    
    def __init__(self, db, callback=None):
        super().__init__()
        self.db = db
        self.callback = callback
        self.settings = self.db.get_settings()
        self.receive_mode = "NORMAL" # NORMAL or SALARY
        self.settlement_results = None
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        with Container(id="settlement-dialog", classes="modal-dialog"):
            with Horizontal(id="details-header"):
                yield Static("SETTLEMENT", id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
            with Vertical(id="settlement-content"):
                # عرض رصيد المحفظة الحالي
                company_balance = self.settings['company_wallet']
                balance_status = "Company owes you" if company_balance > 0 else "You owe company"
                balance_text = f"{balance_status}: {abs(company_balance):.2f} EGP"
                yield Static(balance_text, id="balance-info")
                
                # مبلغ التسوية
                with Vertical(classes="input-group"):
                    yield Static("Amount / Salary Received:")
                    self.amount_input = ArabicInput(
                        placeholder="0.0",
                        id="settlement-amount",
                        required=True,
                        min_value=0
                    )
                    yield self.amount_input
                
                # اتجاه العملية
                with Vertical(classes="input-group"):
                    yield Static("Transaction Direction:")
                    self.direction_toggle = CustomButton(
                        "PAY TO COMPANY",
                        id="direction-toggle",
                        custom_width=25
                    )
                    yield self.direction_toggle

                # وضع الاستلام (يظهر فقط عند القبض من الشركة)
                with Vertical(classes="input-group", id="receive-mode-group"):
                    yield Static("Receive Mode:")
                    with Horizontal(id="mode-buttons"):
                        self.normal_btn = CustomButton("Normal", id="mode-normal", custom_width=12, classes="active")
                        self.salary_btn = CustomButton("Salary", id="mode-salary", custom_width=12)
                        yield self.normal_btn
                        yield self.salary_btn
                
                # صندوق النتائج / الحسبة (يظهر في وضع الراتب)
                with Vertical(id="confirmation-box", classes="hidden"):
                    yield Static("", id="confirm-details")
                    yield Static("", id="confirm-result")

                # التأثير المتوقع (للوضع العادي)
                yield Static("", id="effect-preview")
            
            with Horizontal(id="dialog-buttons"):
                self.process_btn = CustomButton("Process", id="process", custom_width=12)
                self.reject_btn = CustomButton("Manual", id="reject-salary", custom_width=12, classes="hidden")
                yield self.process_btn
                yield self.reject_btn
                yield CustomButton("Close", id="back", custom_width=12)
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.amount_input.focus()
        self.update_ui_state()
        self.update_preview()
    
    def update_ui_state(self) -> None:
        """تحديث ظهور العناصر بناء على الاختيارات"""
        direction = self.direction_toggle.label.plain
        is_receive = "RECEIVE" in direction
        
        # إظهار/إخفاء خيارات الراتب
        mode_group = self.query_one("#receive-mode-group")
        if is_receive:
            mode_group.remove_class("hidden")
        else:
            mode_group.add_class("hidden")
            self.receive_mode = "NORMAL"

        # تحديث استايل أزرار الوضع
        if self.receive_mode == "NORMAL":
            self.normal_btn.add_class("active")
            self.salary_btn.remove_class("active")
            self.query_one("#confirmation-box").add_class("hidden")
            self.query_one("#reject-salary").add_class("hidden")
            self.process_btn.label = "Process"
        else:
            self.salary_btn.add_class("active")
            self.normal_btn.remove_class("active")
            self.query_one("#confirmation-box").remove_class("hidden")
            self.query_one("#reject-salary").remove_class("hidden")
            self.process_btn.label = "Apply"

    def update_preview(self) -> None:
        """تحديث معاينة التأثير"""
        try:
            amount_val = self.amount_input.value or "0"
            amount = float(amount_val)
            company_balance = self.settings['company_wallet']
            
            if self.receive_mode == "SALARY":
                results = AccountingEngine.calculate_salary_settlement(amount, company_balance)
                self.settlement_results = results
                
                # تحديث صندوق الحسبة
                self.query_one("#confirm-details").update(
                    f"Salary: {amount:.2f} | Balance: {company_balance:.2f}"
                )
                self.query_one("#confirm-result").update(results['result_text'])
                self.query_one("#effect-preview").update("") # Hide preview in salary mode
            else:
                # Normal Mode Logic
                new_company_balance = company_balance - amount
                effect_text = f"New Balance: {new_company_balance:.2f} EGP"
                self.query_one("#effect-preview").update(effect_text)
                
        except ValueError:
            self.query_one("#effect-preview").update("Invalid number")
    
    async def on_input_changed(self, event: ArabicInput.Changed) -> None:
        if event.input.id == "settlement-amount":
            self.update_preview()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "process":
            await self.process_settlement()
        elif event.button.id == "reject-salary":
            # Reject Salary results -> Open Manual
            self.open_manual_settlement()
        elif event.button.id in ["back", "close-x"]:
            self.dismiss()
        elif event.button.id == "direction-toggle":
            current = self.direction_toggle.label.plain
            self.direction_toggle.label = "RECEIVE FROM COMPANY" if "PAY" in current else "PAY TO COMPANY"
            self.update_ui_state()
            self.update_preview()
        elif event.button.id == "mode-normal":
            self.receive_mode = "NORMAL"
            self.update_ui_state()
            self.update_preview()
        elif event.button.id == "mode-salary":
            self.receive_mode = "SALARY"
            self.update_ui_state()
            self.update_preview()
    
    def open_manual_settlement(self) -> None:
        """فتح نافذة التسوية اليدوية"""
        def on_manual_done(mode, amount):
            p_effect = -amount if mode == "PAY" else amount
            manual_order = {
                'datetime': datetime.now().isoformat(),
                'mode': 'SETTLEMENT',
                'order_type': 'Settlement',
                'subtype': 'manual_settlement',
                'paid': 0, 'expected': 0, 'actual': amount,
                'tip_cash': 0, 'tip_visa': 0, 'delivery_fee': 0,
                'personal_wallet_effect': p_effect,
                'company_wallet_effect': 0,
                'metadata': json.dumps({"manual_mode": mode})
            }
            self.db.add_order(manual_order)
            self.notify(f"Manual Settlement recorded: {p_effect:.2f} EGP")
            if self.callback: self.callback()
            self.dismiss()

        self.app.push_screen(ManualSettlementDialog(callback=on_manual_done))

    async def process_settlement(self) -> None:
        """معالجة التسوية النهائية"""
        if not self.amount_input.validate_input():
            self.notify("Please enter a valid amount", severity="error")
            return
            
        try:
            amount = float(self.amount_input.value or 0)
            direction = self.direction_toggle.label.plain
            
            if self.receive_mode == "SALARY":
                res = self.settlement_results
                settlement_order = {
                    'datetime': datetime.now().isoformat(),
                    'mode': 'SETTLEMENT',
                    'order_type': 'Settlement',
                    'subtype': 'salary_settlement',
                    'paid': 0, 'expected': 0, 'actual': amount,
                    'tip_cash': 0, 'tip_visa': 0, 'delivery_fee': 0,
                    'personal_wallet_effect': res['personal_effect'],
                    'company_wallet_effect': res['company_effect'],
                    'metadata': json.dumps({
                        "salary_amount": amount,
                        "company_cleared": True,
                        "pocket_change": res['personal_effect']
                    })
                }
                msg = f"Salary Settled! Balance cleared. Change: {res['personal_effect']:.2f}"
            else:
                # Normal Mode
                if amount <= 0: return
                company_effect = -amount
                settlement_order = {
                    'datetime': datetime.now().isoformat(),
                    'mode': 'SETTLEMENT',
                    'order_type': 'Settlement',
                    'subtype': 'normal',
                    'paid': 0, 'expected': 0, 'actual': amount,
                    'tip_cash': 0, 'tip_visa': 0, 'delivery_fee': 0,
                    'personal_wallet_effect': -amount if "PAY" in direction else amount,
                    'company_wallet_effect': company_effect
                }
                msg = f"Settlement Done! Type: {'Pay' if 'PAY' in direction else 'Receive'}"

            self.db.add_order(settlement_order)
            if self.callback: self.callback()
            self.notify(msg)
            self.dismiss()
            
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()
    
    def on_click(self, event: events.Click) -> None:
        if event.widget == self:
            self.dismiss()
