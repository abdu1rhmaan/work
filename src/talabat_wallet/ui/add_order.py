from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Select
from textual import events
from ..models import ModeType, OrderType
from ..engine import AccountingEngine
from .components import CustomButton, OptionSelector, ArabicInput

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
        
        with Container(id="add-order-dialog", classes="modal-dialog"):
            # Header with Title and X button
            with Horizontal(id="details-header"):
                yield Static(title_text, id="details-title")
                yield Button("X", id="close-x", classes="close-button")
            
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
                    self.paid_input = ArabicInput(
                        placeholder="0.0",
                        id="paid",
                        required=True,
                        min_value=0
                    )
                    yield self.paid_input
                
                # المتوقع من العميل
                with Vertical(id="expected-container"):
                    yield Static("Expected Amount:")
                    self.expected_input = ArabicInput(
                        placeholder="0.0",
                        id="expected",
                        required=True,
                        min_value=0
                    )
                    yield self.expected_input
                
                # الفعلي من العميل
                with Vertical(id="actual-container"):
                    yield Static("Actual Received:")
                    self.actual_input = ArabicInput(
                        placeholder="0.0",
                        id="actual",
                        required=True,
                        min_value=0
                    )
                    yield self.actual_input
                
                # بقشيش كاش (للفيزا مود)
                with Vertical(id="tip-cash-container"):
                    yield Static("Tip Cash:")
                    self.tip_cash_input = ArabicInput(
                        placeholder="0.0",
                        id="tip-cash"
                    )
                    yield self.tip_cash_input
                
                # بقشيش فيزا (للفيزا مود)
                with Vertical(id="tip-visa-container"):
                    yield Static("Tip Visa:")
                    self.tip_visa_input = ArabicInput(
                        placeholder="0.0",
                        id="tip-visa"
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
            # self.set_expected_default()  # Disabled per user request
            pass
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
        """تعيين القيمة الافتراضية للمبلغ المتوقع - تم تعطيله بطلب المستخدم"""
        pass
        # كان يقوم بتعبئة الحقل تلقائياً بناءً على نوع الطلب والباتش
        # order_type = self.order_type_selector.value
        # if order_type and self.current_batch in self.batch_prices:
        #     prices = self.batch_prices[self.current_batch]
        #     if order_type == "Restaurant":
        #         default_value = str(prices['restaurant'])
        #     else:
        #         default_value = str(prices['mart'])
        #     self.expected_input.value = default_value
    
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
            # if not self.order_to_edit:
            #     self.set_expected_default()
            self.update_delivery_fee()
    
    async def on_input_submitted(self, event: ArabicInput.Submitted) -> None:
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

    def on_click(self, event) -> None:
        if event.widget == self:
            self.dismiss()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "submit":
            await self.submit_order()
        elif event.button.id in ["cancel", "close-x"]:
            self.dismiss()
    
    async def submit_order(self) -> None:
        """إرسال أو تحديث الطلب"""
        # ✅ CHECK: Require active shift before adding orders (unless editing)
        if not self.order_to_edit:
            active_shift = self.db.get_active_shift()
            if not active_shift:
                self.notify(
                    "❌ Please start a shift first!\n"
                    "You must start a shift before adding orders.",
                    severity="error",
                    timeout=5
                )
                return
        
        # تحديد المود الحالي
        mode = self.order_to_edit['mode'] if self.order_to_edit else self.settings['mode']
        
        # الحصول على نوع الطلب الحالي
        order_type = self.order_type_selector.value
        
        # تحديد الحقول المطلوبة حسب المود ونوع الطلب
        required_fields = []
        if mode == "CASH":
            # في CASH mode: Expected و Actual مطلوبين دائماً
            required_fields = [
                (self.expected_input, "Expected Amount"), 
                (self.actual_input, "Actual Received")
            ]
            
            # ✅ FIX: Paid to Restaurant مطلوب فقط للـ Restaurant orders
            if order_type == "Restaurant":
                required_fields.insert(0, (self.paid_input, "Paid to Restaurant"))
        else:  # VISA mode
            # في وضع الفيزا، لا توجد حقول إلزامية - حقول التبس اختيارية
            required_fields = []
        
        # التحقق من الحقول المطلوبة فقط
        validation_errors = []
        for field, field_name in required_fields:
            value = field.value.strip()
            if not value:
                validation_errors.append(f"{field_name} is required")
                field.add_class("invalid")
            else:
                try:
                    num_value = float(value)
                    if num_value < 0:
                        validation_errors.append(f"{field_name} must be positive")
                        field.add_class("invalid")
                    else:
                        field.remove_class("invalid")
                except ValueError:
                    validation_errors.append(f"{field_name} must be a valid number")
                    field.add_class("invalid")
        
        # في وضع الفيزا: التحقق من حقول البقشيش فقط إذا كانت مملوءة
        if mode == "VISA":
            tip_fields = [
                (self.tip_cash_input, "Tip Cash"),
                (self.tip_visa_input, "Tip Visa")
            ]
            for field, field_name in tip_fields:
                value = field.value.strip()
                if value:  # فقط ن-validatع إذا كان الحقل مملوء
                    try:
                        num_value = float(value)
                        if num_value <= 0:
                            validation_errors.append(f"{field_name} must be positive")
                            field.add_class("invalid")
                        else:
                            field.remove_class("invalid")
                    except ValueError:
                        validation_errors.append(f"{field_name} must be a valid number")
                        field.add_class("invalid")
                else:
                    # إذا كان الحقل فارغاً في وضع الفيزا، نمسح أي علامات خطأ سابقة
                    field.remove_class("invalid")
        
        # إذا كان هناك أخطاء في التحقق
        if validation_errors:
            error_msg = "Please fix the following:\n" + "\n".join(f"• {err}" for err in validation_errors)
            self.notify(error_msg, severity="error")
            return
            
        # إذا لم يكن هناك أخطاء، نواصل معالجة الطلب
        try:
            # نستخدم المود الأصلي للأوردر عند التعديل
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
                # فقط نقرأ قيم البقشيش إذا كانت موجودة
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
