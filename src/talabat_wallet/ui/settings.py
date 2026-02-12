from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Button, Static, Input, Select
from textual import events
from ..database import Database
from .components import CustomButton, OptionSelector

class SettingsScreen(ModalScreen):
    """شاشة الإعدادات كـ Popup"""
    
    def __init__(self, db, callback=None):
        super().__init__()
        self.db = db
        self.callback = callback
        self.settings = self.db.get_settings()
        self.batch_prices = self.db.get_batch_prices()
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        with Container(id="settings-dialog", classes="modal-dialog"):
            yield Static("SETTINGS", id="title")
            
            with Vertical(id="settings-content"):
                # وضع المحاسبة
                with Vertical(id="mode-setting"):
                    yield Static("Accounting Mode:")
                    self.mode_selector = OptionSelector(
                        [("CASH", "CASH"), ("VISA", "VISA")],
                        value=self.settings['mode'],
                        id="mode-selector"
                    )
                    yield self.mode_selector
                
                # اختيار الباتش
                with Vertical(id="batch-setting"):
                    yield Static("Active Batch:")
                    batch_options = [(name, name) for name in self.batch_prices.keys()]
                    self.batch_selector = OptionSelector(
                        batch_options,
                        value=self.settings['batch'],
                        id="batch-selector"
                    )
                    yield self.batch_selector
                
                # أزرار التحكم (Grid 2x2)
                with Grid(id="settings-buttons-grid"):
                    yield CustomButton("Save", id="save", custom_width=16)
                    yield CustomButton("Edit Prices", id="edit-prices", custom_width=16)
                    yield CustomButton("Export Report", id="export-report", custom_width=16)
                    yield CustomButton("Database", id="database-mgmt", custom_width=16)
                    yield CustomButton("Close", id="back", custom_width=16)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        if event.button.id == "save":
            await self.save_settings()
        elif event.button.id == "edit-prices":
            await self.app.push_screen(BatchPricesScreen(self.db))
        elif event.button.id == "export-report":
            await self.export_report()
        elif event.button.id == "database-mgmt":
            await self.app.push_screen(DatabaseSettingsScreen(self.db, self.callback))
        elif event.button.id == "back":
            self.dismiss()
    
    async def export_report(self) -> None:
        """تصدير تقرير شامل كملف نصي"""
        try:
            from datetime import datetime
            from pathlib import Path
            
            # توليد التقرير
            report_content = self.db.generate_report()
            
            # إنشاء اسم الملف بالتاريخ والوقت
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"talabat_report_{timestamp}.txt"
            filepath = Path(filename)
            
            # حفظ الملف
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.notify(f"Report exported: {filename}", severity="information")
        except Exception as e:
            self.notify(f"Export failed: {str(e)}", severity="error")
    
    async def save_settings(self) -> None:
        """حفظ الإعدادات"""
        try:
            new_settings = {
                'mode': self.mode_selector.value,
                'batch': self.batch_selector.value,
                'personal_wallet': self.settings['personal_wallet'],
                'company_wallet': self.settings['company_wallet']
            }
            self.db.update_settings(new_settings)
            if self.callback:
                self.callback()
            self.notify("Settings saved!")
            self.dismiss()
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()

class DatabaseSettingsScreen(ModalScreen):
    """صفحة إدارة قاعدة البيانات كـ Popup"""
    
    def __init__(self, db, callback=None):
        super().__init__()
        self.db = db
        self.callback = callback
        
    def compose(self) -> ComposeResult:
        with Container(id="db-mgmt-dialog", classes="modal-dialog small-modal"):
            yield Static("DATABASE MANAGEMENT", id="title")
            with Vertical(id="settings-content"):
                yield Static("\nDatabase Tools\n", classes="section-header")
                with Vertical(classes="mgmt-group"):
                    yield Static("Permanently delete everything?")
                    yield CustomButton("Reset Database", id="reset-db")
                with Horizontal(id="dialog-buttons"):
                    yield CustomButton("Back", id="back")
                
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reset-db":
            await self.app.push_screen(ConfirmResetScreen(self.db, self.callback))
        elif event.button.id == "back":
            self.dismiss()

class ConfirmResetScreen(ModalScreen):
    """شاشة تأكيد المسح"""
    def __init__(self, db, callback=None):
        super().__init__()
        self.db = db
        self.callback = callback
    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog small-modal"):
            yield Static("RESET DATABASE?", id="title")
            yield Static("\nAre you SURE? This is permanent!\n", classes="warning-text")
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("YES", id="confirm")
                yield CustomButton("NO", id="cancel")
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.db.reset_database()
            if self.callback: self.callback()
            self.notify("Database Reset!", severity="warning")
            self.dismiss()
        else: self.dismiss()

class BatchPricesScreen(ModalScreen):
    """شاشة تحرير الأسعار كـ Popup"""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.batch_prices = self.db.get_batch_prices()
    def compose(self) -> ComposeResult:
        with Container(id="prices-dialog", classes="modal-dialog"):
            yield Static("BATCH PRICES EDITOR", id="title")
            with Vertical(id="prices-content"):
                for batch_name, prices in self.batch_prices.items():
                    with Vertical(classes="batch-group"):
                        yield Static(f"--- BATCH {batch_name} ---", classes="batch-header")
                        with Horizontal(classes="price-field"):
                            yield Static("Mart: ", classes="field-label")
                            yield Input(value=str(prices['mart']), id=f"mart-{batch_name}", type="number", validate_on=["submitted", "blur"])
                        with Horizontal(classes="price-field"):
                            yield Static("Rest: ", classes="field-label")
                            yield Input(value=str(prices['restaurant']), id=f"restaurant-{batch_name}", type="number", validate_on=["submitted", "blur"])
                with Horizontal(id="prices-buttons"):
                    yield CustomButton("Save All", id="save-prices")
                    yield CustomButton("Back", id="back-prices")
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-prices":
            await self.save_all_prices()
        elif event.button.id == "back-prices":
            self.dismiss()
    async def save_all_prices(self) -> None:
        try:
            for batch_name in self.batch_prices.keys():
                mart_price = float(self.query_one(f"#mart-{batch_name}").value or 0)
                rest_price = float(self.query_one(f"#restaurant-{batch_name}").value or 0)
                self.db.update_batch_price(batch_name, mart_price, rest_price)
            self.notify("Prices saved!")
            self.dismiss()
        except Exception as e: self.notify(str(e), severity="error")
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape": self.dismiss()