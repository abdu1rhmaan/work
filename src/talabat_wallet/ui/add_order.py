from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Input, Select
from textual import events
from ..models import ModeType, OrderType
from ..engine import AccountingEngine
from .components import CustomButton, OptionSelector

class AddOrderScreen(ModalScreen):
    """شاشة إضافة أو تعديل طلب جديد"""
    
    def __init__(self, db, callback=None, order_to_edit=None):
        super().__init__()
        self.db = db
        self.callback = callback
        self.order_to_edit = order_to_edit
        self.settings = self.db.get_settings()
        self.batch_prices = self.db.get_batch_prices()
        self.current_batch = self.settings['batch']
        self.calculated_delivery_fee = 0.0
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        title_text = "EDIT ORDER" if self.order_to_edit else "ADD NEW ORDER"
        submit_text = "Update" if self.order_to_edit else "Submit"
        
        with Container(id="add-order-dialog"):
            yield Static(title_text, id="title")
            
            with Vertical(id="form-container"):
                # نوع الطلب
                with Vertical(id="order-type-container"):
                    yield Static("Order Type:")
                    default_type = self.order_to_edit['order_type'] if self.order_to_edit else "Restaurant"
                    self.order_type_selector = OptionSelector(
                        [
                            ("Restaurant", "Restaurant"),
                            ("Mart", "Mart"),
                            ("Friendly Restaurant", "Friendly")
                        ],
                        value=default_type,
                        id="order-type"
                    )
                    yield self.order_type_selector
                
                # المدفوع للمطعم
                with Vertical(id="paid-container"):
                    yield Static("Paid to Restaurant:")
                    self.paid_input = Input(
                        placeholder="0.0",
                        id="paid",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.paid_input
                
                # المتوقع من العميل
                with Vertical(id="expected-container"):
                    yield Static("Expected Amount:")
                    self.expected_input = Input(
                        placeholder="0.0",
                        id="expected",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.expected_input
                
                # الفعلي من العميل
                with Vertical(id="actual-container"):
                    yield Static("Actual Received:")
                    self.actual_input = Input(
                        placeholder="0.0",
                        id="actual",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.actual_input
                
                # بقشيش كاش (للفيزا مود)
                with Vertical(id="tip-cash-container"):
                    yield Static("Tip Cash:")
                    self.tip_cash_input = Input(
                        placeholder="0.0",
                        id="tip-cash",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.tip_cash_input
                
                # بقشيش فيزا (للفيزا مود)
                with Vertical(id="tip-visa-container"):
                    yield Static("Tip Visa:")
                    self.tip_visa_input = Input(
                        placeholder="0.0",
                        id="tip-visa",
                        type="number",
                        validate_on=["submitted", "blur"]
                    )
                    yield self.tip_visa_input
                
                # ملاحظة التسعيرة (تفاعلية)
                self.delivery_note = Static("", id="delivery-info-note")
                yield self.delivery_note

                # أزرار
                with Horizontal(id="dialog-buttons"):
                    yield CustomButton(submit_text, id="submit")
                    yield CustomButton("Cancel", id="cancel")
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.update_field_visibility()
        if self.order_to_edit:
            self.prepopulate_fields()
        else:
            self.set_expected_default()
        self.update_delivery_fee()
        
    def prepopulate_fields(self) -> None:
        """تعبئة الحقول ببيانات الأوردر المراد تعديله"""
        self.paid_input.value = str(self.order_to_edit['paid'])
        self.expected_input.value = str(self.order_to_edit['expected'])
        self.actual_input.value = str(self.order_to_edit['actual'])
        self.tip_cash_input.value = str(self.order_to_edit['tip_cash'])
        self.tip_visa_input.value = str(self.order_to_edit['tip_visa'])
        self.calculated_delivery_fee = self.order_to_edit['delivery_fee']

    def update_field_visibility(self) -> None:
        """تحديث ظهور الحقول حسب المود ونوع الطلب"""
        # نستخدم المود الأصلي للأوردر عند التعديل
        mode = self.order_to_edit['mode'] if self.order_to_edit else self.settings['mode']
        order_type = self.order_type_selector.value
        
        # حاويات الحقول
        containers = {
            "order-type": self.query_one("#order-type-container"),
            "paid": self.query_one("#paid-container"),
            "expected": self.query_one("#expected-container"),
            "actual": self.query_one("#actual-container"),
            "tip-cash": self.query_one("#tip-cash-container"),
            "tip-visa": self.query_one("#tip-visa-container")
        }
        
        if mode == "VISA":
            containers["order-type"].display = True
            containers["paid"].display = False
            containers["expected"].display = False
            containers["actual"].display = False
            containers["tip-cash"].display = True
            containers["tip-visa"].display = True
            self.tip_cash_input.focus()
        else:
            containers["order-type"].display = True
            containers["expected"].display = True
            containers["actual"].display = True
            containers["tip-cash"].display = False
            containers["tip-visa"].display = False
            if order_type == "Restaurant":
                containers["paid"].display = True
                self.paid_input.focus()
            else:
                containers["paid"].display = False
                self.expected_input.focus()

    def set_expected_default(self) -> None:
        """تعيين القيمة الافتراضية للمبلغ المتوقع"""
        order_type = self.order_type_selector.value
        if order_type and self.current_batch in self.batch_prices:
            prices = self.batch_prices[self.current_batch]
            if order_type == "Restaurant":
                default_value = str(prices['restaurant'])
            else:
                default_value = str(prices['mart'])
            self.expected_input.value = default_value
    
    def update_delivery_fee(self) -> None:
        """تحديث رسوم التوصيل والجملة التوضيحية"""
        order_type = self.order_type_selector.value
        if self.current_batch in self.batch_prices:
            prices = self.batch_prices[self.current_batch]
            if order_type == "Mart":
                self.calculated_delivery_fee = float(prices['mart'])
            else:
                self.calculated_delivery_fee = float(prices['restaurant'])
            
            # تحديث الجملة التوضيحية بالألوان
            fee = self.calculated_delivery_fee
            self.delivery_note.update(f"Delivery Fee: [b green]{fee:.2f} EGP[/b green]")
        else:
            self.calculated_delivery_fee = 0.0
            self.delivery_note.update("[ No Price Info Found ]")

    async def on_option_selector_selected(self, event: OptionSelector.Selected) -> None:
        """عند تغيير نوع الطلب"""
        if event.selector.id == "order-type":
            self.update_field_visibility()
            if not self.order_to_edit:
                self.set_expected_default()
            self.update_delivery_fee()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """التنقل بين الحقول عند الضغط على Enter"""
        if event.input.id == "paid":
            self.expected_input.focus()
        elif event.input.id == "expected":
            self.actual_input.focus()
        elif event.input.id == "actual":
            await self.submit_order()
        elif event.input.id == "tip-cash":
            self.tip_visa_input.focus()
        elif event.input.id == "tip-visa":
            await self.submit_order()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "submit":
            await self.submit_order()
        elif event.button.id == "cancel":
            self.dismiss()
    
    async def submit_order(self) -> None:
        """إرسال أو تحديث الطلب"""
        try:
            # نستخدم المود الأصلي للأوردر عند التعديل
            mode = self.order_to_edit['mode'] if self.order_to_edit else self.settings['mode']
            order_type = self.order_type_selector.value
            
            self.update_delivery_fee()
            delivery_fee = self.calculated_delivery_fee
            
            if mode == "CASH":
                paid = float(self.paid_input.value or 0) if order_type == "Restaurant" else 0.0
                expected = float(self.expected_input.value or 0)
                actual = float(self.actual_input.value or 0)
                tip_cash = 0.0
                tip_visa = 0.0
            else:  # VISA
                paid = 0.0
                expected = 0.0
                actual = 0.0
                tip_cash = float(self.tip_cash_input.value or 0)
                tip_visa = float(self.tip_visa_input.value or 0)
            
            if any(val < 0 for val in [paid, expected, actual, tip_cash, tip_visa, delivery_fee]):
                self.notify("Error: Negative values not allowed", severity="error")
                return

            is_valid, error_message = AccountingEngine.validate_order_values(
                order_type, paid, expected, actual, delivery_fee
            )
            
            if not is_valid:
                self.notify(error_message, severity="error")
                return
            
            # حساب البيانات الجديدة
            order = AccountingEngine.create_order(
                mode=mode,
                order_type=order_type,
                paid=paid,
                expected=expected,
                actual=actual,
                delivery_fee=delivery_fee,
                tip_cash=tip_cash,
                tip_visa=tip_visa
            )
            
            order_dict = order.to_dict()
            
            if self.order_to_edit:
                # الحفاظ على التاريخ الأصلي
                order_dict['datetime'] = self.order_to_edit['datetime']
                if await self.db.update_order(self.order_to_edit['id'], order_dict):
                    self.notify("Order updated successfully!")
                    if self.callback:
                        self.callback()
                    self.dismiss()
                else:
                    self.notify("Error updating order", severity="error")
            else:
                self.db.add_order(order_dict)
                profit = AccountingEngine.calculate_profit(delivery_fee, order.tip_cash, order.tip_visa)
                self.notify(f"Order added! Profit: {profit:.2f} EGP")
                if self.callback:
                    self.callback()
                self.dismiss()
            
        except ValueError:
            self.notify("Please enter valid numbers", severity="error")
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()
