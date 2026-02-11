from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Input
from textual import events
from datetime import datetime
from ..database import Database
from .components import CustomButton

class SettlementScreen(ModalScreen):
    """شاشة التسوية كـ Popup"""
    
    def __init__(self, db, callback=None):
        super().__init__()
        self.db = db
        self.callback = callback
        self.settings = self.db.get_settings()
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        with Container(id="settlement-dialog", classes="modal-dialog"):
            yield Static("SETTLEMENT", id="title")
            
            with Vertical(id="settlement-content"):
                # عرض رصيد المحفظة الحالي
                company_balance = self.settings['company_wallet']
                # إذا كان الرصيد سالباً، فهذا يعني أن السائق مديون للشركة (حسب الممارسة المحاسبية المعتادة وتجربة المستخدم)
                # إذا كان موجباً، فالشركة مدينة للسائق
                balance_status = "Company owes you" if company_balance > 0 else "You owe company"
                balance_text = f"{balance_status}: {abs(company_balance):.2f} EGP"
                yield Static(balance_text, id="balance-info")
                
                # مبلغ التسوية
                with Vertical(classes="input-group"):
                    yield Static("Settlement Amount:")
                    self.amount_input = Input(
                        placeholder="0.0",
                        id="settlement-amount",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.amount_input
                
                # اتجاه العملية (Transaction Direction Toggle)
                with Vertical(classes="input-group"):
                    yield Static("Transaction Direction:")
                    self.direction_toggle = CustomButton(
                        "PAY TO COMPANY",
                        id="direction-toggle"
                    )
                    yield self.direction_toggle
                
                # التأثير المتوقع
                yield Static("", id="effect-preview")
            
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Process", id="process")
                yield CustomButton("Close", id="back")
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.amount_input.focus()
        self.update_preview()
    
    def update_preview(self) -> None:
        """تحديث معاينة التأثير"""
        try:
            amount_val = self.amount_input.value or "0"
            amount = float(amount_val)
            company_balance = self.settings['company_wallet']
            
            if amount <= 0:
                self.query_one("#effect-preview").update("Enter valid amount")
                return
            
            direction = self.direction_toggle.label
            
            # ACCOUNTING LOGIC: company_wallet = company_wallet - amount (for both)
            new_company_balance = company_balance - amount
            
            effect_text = f"New Balance: {new_company_balance:.2f} EGP"
            self.query_one("#effect-preview").update(effect_text)
            
        except ValueError:
            self.query_one("#effect-preview").update("Invalid number")
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """عند تغيير قيمة الإدخال"""
        if event.input.id == "settlement-amount":
            self.update_preview()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "process":
            await self.process_settlement()
        elif event.button.id == "back":
            self.dismiss()
        elif event.button.id == "direction-toggle":
            # التبديل بين القبض والتوريد
            current = self.direction_toggle.label.plain
            if "PAY" in current:
                self.direction_toggle.label = "RECEIVE FROM COMPANY"
            else:
                self.direction_toggle.label = "PAY TO COMPANY"
            self.update_preview()
    
    async def process_settlement(self) -> None:
        """معالجة التسوية"""
        try:
            amount = float(self.amount_input.value or 0)
            if amount <= 0:
                self.notify("Please enter a valid amount", severity="error")
                return
            
            company_balance = self.settings['company_wallet']
            direction = self.direction_toggle.label.plain
            
            # ACCOUNTING LOGIC: company_wallet = company_wallet - amount (for both)
            company_effect = -amount
                
            new_company_balance = company_balance + company_effect
            
            # تسجيل العملية - الـ add_order حيتكفل بتحديث الـ settings برضه
            settlement_order = {
                'datetime': datetime.now().isoformat(),
                'mode': 'SETTLEMENT',
                'order_type': 'Settlement',
                'paid': 0,
                'expected': 0,
                'actual': amount,
                'tip_cash': 0,
                'tip_visa': 0,
                'delivery_fee': 0,
                'personal_wallet_effect': -amount if "PAY" in direction else amount, 
                'company_wallet_effect': company_effect
            }
            
            self.db.add_order(settlement_order)
            
            if self.callback:
                self.callback()
            
            self.notify(f"Settlement Done! New balance: {new_company_balance:.2f} EGP")
            self.dismiss()
            
        except ValueError:
            self.notify("Invalid number", severity="error")
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()