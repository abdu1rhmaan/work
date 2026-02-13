import re
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Label, Input, Select, DataTable, ListItem
from textual.strip import Strip
from rich.segment import Segment
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.message import Message
from textual import events
from typing import Optional, Callable, Dict, Any
from ..utils import format_arabic

class CustomButton(Button):
    """زر مخصص يحافظ على الحجم الثابت"""
    
    def __init__(self, label: str, id: Optional[str] = None, custom_width: int = 30, **kwargs):
        super().__init__(label, id=id, **kwargs)
        self.custom_width = custom_width
    
    def render(self) -> str:
        """رسم الزر بسمك عمودي حقيقي باستخدام خطوط طرفية متعددة"""
        label = self.label.plain
        formatted_label = format_arabic(label)
        
        # قص النص إذا كان طويلاً جداً
        if len(formatted_label) > self.custom_width:
            formatted_label = formatted_label[:self.custom_width-3] + "..."
        
        # حساب الحشو الأفقي
        width = self.custom_width
        h_padding = (width - len(formatted_label)) // 2
        left_pad = " " * h_padding
        right_pad = " " * (width - len(formatted_label) - h_padding)
        
        # السطر النصي الأساسي
        text_line = f"{left_pad}{formatted_label}{right_pad}"
        
        # الحصول على الارتفاع من CSS styles
        # نستخدم قيمة محسوبة أو قيمة افتراضية معقولة
        try:
            height_style = self.styles.height
            if height_style is not None and hasattr(height_style, 'value'):
                # إذا كان الارتفاع معرفاً في CSS
                if hasattr(height_style, 'unit') and height_style.unit == 'cells':
                    height = int(height_style.value)
                else:
                    # fallback للقيم العددية المباشرة
                    height = int(float(height_style.value))
            else:
                # fallback إلى size.height إذا كان معقولاً
                height = self.size.height if self.size.height >= 2 else 1
        except (ValueError, TypeError, AttributeError):
            # في حالة الخطأ، نستخدم القيمة الافتراضية
            height = 1
        
        # إذا كان الارتفاع أقل من 2، نستخدم الرسم العادي (سطر واحد)
        if height < 2:
            content = text_line
        else:
            # بناء الزر بسمك عمودي حقيقي (2-3 خطوط كحد أقصى للمain buttons)
            # نحد الارتفاع الأقصى لتجنب الإفراط في الحجم
            max_height = min(height, 3)  # أقصى ارتفاع 3 خطوط
            lines = []
            empty_line = " " * width
            # وضع النص في المنتصف عمودياً
            text_line_index = max_height // 2
            
            for row in range(max_height):
                if row == text_line_index:
                    lines.append(text_line)
                else:
                    lines.append(empty_line)
            
            content = "\n".join(lines)
            
        # تطبيق حالة التركيز
        if self.has_focus:
            # عند التركيز، نطبق الـ reverse على كل سطر
            if "\n" in content:
                focused_lines = [f"[reverse]{line}[/]" for line in content.split("\n")]
                return "\n".join(focused_lines)
            else:
                return f"[reverse]{content}[/]"
        else:
            return content

class WalletDisplay(Static):
    """عرض المحفظة"""
    
    value = reactive(0.0)
    
    def __init__(self, label: str, value: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
    
    def watch_value(self, value: float) -> None:
        """تحديث العرض عند تغيير القيمة"""
        formatted_value = f"{value:,.2f} EGP"
        if value >= 0:
            display_text = f"{self.label}: {formatted_value}"
        else:
            display_text = f"{self.label}: -{formatted_value[1:]}"
        
        self.update(format_arabic(display_text))

class ModeDisplay(Static):
    """عرض وضع المحاسبة"""
    
    mode = reactive("CASH")
    
    def __init__(self, mode: str = "CASH", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
    
    def watch_mode(self, mode: str) -> None:
        """تحديث العرض عند تغيير الوضع"""
        if mode == "CASH":
            self.update("[ Mode: CASH ]")
        else:
            self.update("[ Mode: VISA ]")

class BatchDisplay(Static):
    """عرض الباتش الحالي"""
    
    batch = reactive("1")
    
    def __init__(self, batch: str = "1", **kwargs):
        super().__init__(**kwargs)
        self.batch = batch
    
    def watch_batch(self, batch: str) -> None:
        """تحديث العرض عند تغيير الباتش"""
        self.update(f"[ Batch: {batch} ]")

class HistoryTable(DataTable):
    """جدول التاريخ التفاعلي مع دعم الاختيار المتعدد"""
    
    class RowClicked(Message, bubble=True):
        """رسالة عند الضغط على سطر (ضغطة واحدة)"""
        def __init__(self, row_key):
            super().__init__()
            self.row_key = row_key

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        # إضافة عمود الاختيار في البداية مع مفاتيح للأعمدة
        self.add_column("✓", key="sel")
        self.add_column("ID", key="id")
        self.add_column("Date", key="date")
        self.add_column("Type", key="type")
        self.add_column("Paid", key="paid")
        self.add_column("Expected", key="expected")
        self.add_column("Actual", key="actual")
        self.add_column("Profit", key="profit")
    
    def on_mouse_down(self, event: events.MouseDown) -> None:
        """اكتشاف الضغط بالماوس على السطر فوراً"""
        try:
            # محاولة الحصول على السطر بناءً على الإحداثيات
            row_index = self.get_row_at(event.y)
            
            # Fallback في حال كانت الاحداثيات خارج النطاق المباشر (لأن الهيدر له مكان)
            if row_index is None:
                # حساب يدوي: (Y بالنسبة للويدجت - 1 للهيدر) + السكرول
                row_index = (event.y - 1) + self.scroll_y
            
            if 0 <= row_index < self.row_count:
                row_key = self.get_row_key_at(row_index)
                self.post_message(self.RowClicked(row_key))
        except Exception:
            pass
    
class HistoryRow(ListItem):
    """سطر تاريخ يحتوي على زر حقيقي للاختيار"""
    
    class ToggleSelection(Message):
        """رسالة عند ضغط زر السيلكت"""
        def __init__(self, order_id: str):
            super().__init__()
            self.order_id = order_id

    def __init__(self, order: Dict[str, Any], display_id: int, is_selected: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.order = order
        self.display_id = display_id
        self.is_selected = is_selected
        self.order_id = str(order.get('id', ''))

    def compose(self):
        with Horizontal(classes="history-row-content"):
            # استخدام Label بدل Button للتحكم الكامل في العرض بدون أي مسافات زائدة
            btn_text = "[●]" if self.is_selected else "[ ]"
            yield Label(btn_text, id=f"sel-{self.order_id}", classes="row-sel-toggle " + ("selected" if self.is_selected else ""))
            
            # بيانات السطر
            yield Label(str(self.display_id), classes="col-id")
            yield Label(self.order.get('datetime', '')[:10], classes="col-date")
            yield Label(format_arabic(self.order.get('order_type', '')), classes="col-type")
            
            profit = (self.order.get('delivery_fee', 0) + 
                     self.order.get('tip_cash', 0) + 
                     self.order.get('tip_visa', 0))
            yield Label(f"{profit:.2f}", classes="col-profit")

    def on_click(self, event: events.Click) -> None:
        # إذا كانت الضغطة على المربع (Label [ ])
        # نستخدم event.control أو id للوصول الدقيق
        if event.control and event.control.id == f"sel-{self.order_id}":
            self.post_message(self.ToggleSelection(self.order_id))
            event.stop() # منع وصول الضغطة للـ ListView
            event.prevent_default()
        elif "row-sel-toggle" in event.style.meta.get("classes", []):
            self.post_message(self.ToggleSelection(self.order_id))
            event.stop()
            event.prevent_default()

class OptionSelector(Static):
    """مكون لاختيار خيار من مجموعة أزرار"""
    
    class Selected(Message):
        """رسالة عند اختيار قيمة"""
        def __init__(self, selector: "OptionSelector", value: str):
            super().__init__()
            self.selector = selector
            self.value = value

    def __init__(self, options: list[tuple[str, str]], value: str, id: str = None):
        super().__init__(id=id)
        self.options = options
        self.value = value
        self.buttons = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="option-selector"):
            for label, val in self.options:
                btn = Button(format_arabic(label), id=f"opt-{val}", classes="option-button")
                if val == self.value:
                    btn.add_class("active")
                self.buttons[val] = btn
                yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار لتغيير القيمة النشطة"""
        event.stop()
        new_val = event.button.id.replace("opt-", "")
        
        # إزالة الكلاس النشط من الجميع وإضافته للمختار
        for btn in self.buttons.values():
            btn.remove_class("active")
        
        self.buttons[new_val].add_class("active")
        self.value = new_val
        
        # إرسال رسالة بتغيير القيمة
        self.post_message(self.Selected(self, new_val))

class AppInput(Input):
    """Custom Input that forces keyboard reopen on mobile"""
    
    async def on_click(self) -> None:
        """Force keyboard reopen on mobile by toggling focus"""
        # This hack forces the soft keyboard to reappear on Termux/Android
        if self.has_focus:
            self.blur()
            self.focus()
        
    def _show_keyboard(self) -> None:
        # Legacy method kept for compatibility if needed, but on_click logic is primary now
        try:
            import subprocess
            import platform
            if platform.system() == "Linux":
                subprocess.run(["termux-keyboard-show"], capture_output=True, check=False)
        except Exception:
            pass

class ArabicInput(AppInput):
    """حقل إدخال يدعم اللغة العربية بشكل صحيح أثناء الكتابة مع محاذاة تلقائية"""
    
    def __init__(self, *args, required: bool = False, min_value: float = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = required
        self.min_value = min_value
        self._is_invalid = False
    
    def _render_line(self, y: int) -> Strip:
        """تخصيص رسم السطر لدعم العربي والمحاذاة المباشرة"""
        # استدعاء الرسم الأصلي للحصول على الـ Strip (الذي يحتوي على النص والمؤشر)
        strip = super()._render_line(y)
        
        # إذا لم يكن هناك نص، نعود بالرسم الأصلي
        if not self.value and not self.placeholder:
            return strip

        # معالجة النص الظاهر (سواء كان القيمة أو الـ placeholder)
        display_text = self.value if self.value else self.placeholder
        
        # فحص اللغة وحساب المحاذاة
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in display_text)
        
        if is_arabic:
            # معالجة العربي
            formatted_text = format_arabic(display_text)
            
            # حساب الفراغ للمحاذاة لليمين
            padding = max(0, self.size.width - len(formatted_text) - 4) # -4 للهوامش الداخلية
            
            # إنشاء سطر جديد محاذى لليمين
            segments = []
            if padding > 0:
                segments.append(Segment(" " * padding))
            segments.append(Segment(formatted_text, self.rich_style))
            
            return Strip(segments)
            
        return strip

    def watch_value(self, value: str) -> None:
        """تحديث الواجهة عند كل تغيير"""
        self.refresh()
        
    def validate_input(self) -> bool:
        """التحقق من صحة الإدخال"""
        value = self.value.strip()
        
        # إذا كان الحقل غير مطلوب وفارغ، فهو صحيح
        if not self.required and not value:
            self._is_invalid = False
            self.remove_class("invalid")
            return True
            
        # إذا كان الحقل مطلوب وفارغ
        if self.required and not value:
            self._is_invalid = True
            self.add_class("invalid")
            return False
            
        # التحقق من القيم العددية
        if self.min_value is not None:
            try:
                num_value = float(value)
                if num_value <= self.min_value:
                    self._is_invalid = True
                    self.add_class("invalid")
                    return False
            except ValueError:
                self._is_invalid = True
                self.add_class("invalid")
                return False
                
        # الإدخال صحيح
        self._is_invalid = False
        self.remove_class("invalid")
        return True
        
    def on_blur(self) -> None:
        """لا ن-validatع عند فقدان التركيز - فقط عند الإرسال"""
        pass
        
    def on_focus(self) -> None:
        """إزالة حالة الخطأ عند التركيز وطلب الكيبورد"""
        if self.has_class("invalid"):
            self.remove_class("invalid")

class ShiftTimerDisplay(Static):
    """عرض مؤقت الوردية"""
    
    start_time = reactive(None)
    
    def __init__(self, start_time: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.start_time = start_time
        self.timer = None
        
    def on_mount(self) -> None:
        """بدء التحديث الدوري"""
        self.timer = self.set_interval(1.0, self.update_timer)
        
    def update_timer(self) -> None:
        """تحديث الوقت المنقضي"""
        if not self.start_time:
            self.update("")
            return
            
        try:
            from datetime import datetime
            start = datetime.strptime(self.start_time, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = now - start
            
            total_seconds = int(diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.update(f"[b]SHIFT TIME: {time_str}[/b]")
        except Exception:
            self.update("Error")

    def watch_start_time(self, start_time: Optional[str]) -> None:
        """مراقبة تغيير وقت البدء"""
        self.update_timer()
