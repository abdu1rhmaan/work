from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Select
from textual import events
from ..models import ModeType, OrderType
from ..engine import AccountingEngine
from .components import CustomButton, OptionSelector, ArabicInput
from .window import BaseWindow

class AddOrderWindow(BaseWindow):
    WINDOW_ID = "add_order"
    """نافذة إضافة أو تعديل طلب جديد (Draggable)"""

    WINDOW_ID = "add_order"

    def __init__(self, db, callback=None, order_to_edit=None):
        title = "EDIT ORDER" if order_to_edit else "ADD NEW ORDER"
        self.db = db
        self.callback = callback
        self.order_to_edit = order_to_edit
        self.settings = self.db.get_settings()
        
        # 📏 Use auto height — field visibility will drive the size dynamically
        super().__init__(title=title, width=65)
        self.batch_prices = self.db.get_batch_prices()
        self.current_batch = self.settings['batch']
        self.calculated_delivery_fee = 0.0

    def compose_content(self) -> ComposeResult:
        """بناء محتوى النافذة"""
        submit_text = "Update" if self.order_to_edit else "Submit"
        
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
        # 🔄 Safe: call_after_refresh ensures widgets are mounted before we query them
        self.call_after_refresh(self._post_mount_init)

    def _post_mount_init(self) -> None:
        """Run after first render to safely query and update widgets"""
        self.update_field_visibility()
        if self.order_to_edit:
            self.prepopulate_fields()
        self.update_delivery_fee()
        self.set_timer(0.2, self.initial_focus)

    def initial_focus(self) -> None:
        if self.order_to_edit:
             pass # Maybe don't focus if editing? Or focus first field
        else:
             # Logic from original: focus paid or expected
             pass

    def prepopulate_fields(self) -> None:
        """تعبئة الحقول ببيانات الأوردر المراد تعديله"""
        self.paid_input.value = str(self.order_to_edit['paid'])
        self.expected_input.value = str(self.order_to_edit['expected'])
        self.actual_input.value = str(self.order_to_edit['actual'])
        self.tip_cash_input.value = str(self.order_to_edit['tip_cash'])
        self.tip_visa_input.value = str(self.order_to_edit['tip_visa'])
        self.calculated_delivery_fee = self.order_to_edit['delivery_fee']

    def update_field_visibility(self) -> None:
        """تحديث ظهور الحقول بناءً على وضع المحاسبة ونوع الطلب"""
        mode = self.settings.get('mode', 'CASH')
        order_type = self.order_type_selector.value
        
        # 🛡️ Safe query: toggle display based on mode
        containers = {
            "paid": self.query_one("#paid-container"),
            "expected": self.query_one("#expected-container"),
            "actual": self.query_one("#actual-container"),
            "tip-cash": self.query_one("#tip-cash-container"),
            "tip-visa": self.query_one("#tip-visa-container")
        }
        
        if mode == "VISA":
            containers["paid"].display = "none"
            containers["expected"].display = "none"
            containers["actual"].display = "none"
            containers["tip-cash"].display = "block"
            containers["tip-visa"].display = "block"
        else: # CASH
            containers["tip-cash"].display = "none"
            containers["tip-visa"].display = "none"
            containers["expected"].display = "block"
            containers["actual"].display = "block"
            # Paid is only for Restaurant in CASH mode
            containers["paid"].display = "block" if (order_type == "Restaurant") else "none"
        
        # 🔄 CRITICAL: trigger immediate layout recalculation after show/hide
        self.refresh()

    def refresh_ui(self, settings: dict) -> None:
        """Reactive UI: Auto-update visibility when settings change globally."""
        self.settings = settings
        self.update_field_visibility()
        self.update_delivery_fee()

    def update_delivery_fee(self) -> None:
        """تحديث رسوم التوصيل والجملة التوضيحية"""
        order_type = self.order_type_selector.value
        if self.current_batch in self.batch_prices:
            prices = self.batch_prices[self.current_batch]
            # Convert decimal strings to float for calculation if needed, 
            # assuming keys like 'mart' and 'restaurant' exist
            if order_type == "Mart":
                self.calculated_delivery_fee = float(prices.get('mart', 0))
            else:
                self.calculated_delivery_fee = float(prices.get('restaurant', 0))
            
            fee = self.calculated_delivery_fee
            self.delivery_note.update(f"Delivery Fee: [b green]{fee:.2f} EGP[/b green]")
        else:
            self.calculated_delivery_fee = 0.0
            self.delivery_note.update("[ No Price Info Found ]")

    async def on_option_selector_selected(self, event: OptionSelector.Selected) -> None:
        if event.selector.id == "order-type":
            self.update_field_visibility()
            self.update_delivery_fee()
    
    async def on_input_submitted(self, event: ArabicInput.Submitted) -> None:
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
        # Check if it's our Close button (handled by base) or custom buttons
        if event.button.id == "submit":
            await self.submit_order()
        elif event.button.id == "cancel":
            self.close()
        # Note: 'close_btn' is handled by DraggableWindow base class

    async def submit_order(self) -> None:
        if not self.order_to_edit:
            active_shift = self.db.get_active_shift()
            if not active_shift:
                self.notify(
                    "❌ Please start a shift first!",
                    severity="error",
                    timeout=5
                )
                return
        
        mode = self.order_to_edit['mode'] if self.order_to_edit else self.settings['mode']
        order_type = self.order_type_selector.value
        
        required_fields = []
        if mode == "CASH":
            required_fields = [
                (self.expected_input, "Expected Amount"), 
                (self.actual_input, "Actual Received")
            ]
            if order_type == "Restaurant":
                required_fields.insert(0, (self.paid_input, "Paid to Restaurant"))
        
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
        
        if mode == "VISA":
            tip_fields = [(self.tip_cash_input, "Tip Cash"), (self.tip_visa_input, "Tip Visa")]
            for field, field_name in tip_fields:
                value = field.value.strip()
                if value:
                    try:
                        num_value = float(value)
                        if num_value < 0: # Allow 0
                            validation_errors.append(f"{field_name} must be positive")
                            field.add_class("invalid")
                        else:
                            field.remove_class("invalid")
                    except ValueError:
                        validation_errors.append(f"{field_name} must be a valid number")
                        field.add_class("invalid")
        
        if validation_errors:
            error_msg = "Please fix:\n" + "\n".join(f"• {err}" for err in validation_errors)
            self.notify(error_msg, severity="error")
            return
            
        try:
            self.update_delivery_fee()
            delivery_fee = self.calculated_delivery_fee
            
            if mode == "CASH":
                paid = float(self.paid_input.value or 0) if order_type == "Restaurant" else 0.0
                expected = float(self.expected_input.value or 0)
                actual = float(self.actual_input.value or 0)
                tip_cash = 0.0
                tip_visa = 0.0
            else:
                paid = 0.0
                expected = 0.0
                actual = 0.0
                tip_cash = float(self.tip_cash_input.value or 0)
                tip_visa = float(self.tip_visa_input.value or 0)
            
            is_valid, error_message = AccountingEngine.validate_order_values(
                order_type, paid, expected, actual, delivery_fee
            )
            
            if not is_valid:
                self.notify(error_message, severity="error")
                return
            
            order = AccountingEngine.create_order(
                mode=mode, order_type=order_type, paid=paid,
                expected=expected, actual=actual, delivery_fee=delivery_fee,
                tip_cash=tip_cash, tip_visa=tip_visa
            )
            
            order_dict = order.to_dict()
            
            if self.order_to_edit:
                order_dict['datetime'] = self.order_to_edit['datetime']
                if await self.db.update_order(self.order_to_edit['id'], order_dict):
                    self.notify("Order updated successfully!")
                    # 🚀 Broadcast update
                    self.post_message(self.OrderAdded())
                    if self.callback:
                        self.callback()
                    self.close()
                else:
                    self.notify("Error updating order", severity="error")
            else:
                self.db.add_order(order_dict)
                profit = AccountingEngine.calculate_profit(delivery_fee, order.tip_cash, order.tip_visa)
                self.notify(f"Order added! Profit: {profit:.2f} EGP")
                # 🚀 Broadcast update to all listeners (Wallet, Dashboard, etc.)
                self.post_message(self.OrderAdded())
                if self.callback:
                    self.callback()
                self.close()
            
        except ValueError:
            self.notify("Please enter valid numbers", severity="error")
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
