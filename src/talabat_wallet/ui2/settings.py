from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Button, Static
from textual import events
from ..database import Database
from ..ui.components import CustomButton, OptionSelector, ArabicInput
from .window import DraggableWindow

class ConfirmResetWindow(DraggableWindow):
    """نافذة تأكيد المسح"""
    def __init__(self, db, callback=None):
        super().__init__(title="RESET DATABASE?")
        self.db = db
        self.callback = callback

    def compose_content(self) -> ComposeResult:
        yield Static("\nAre you SURE? This is permanent!\n", classes="warning-text")
        with Horizontal(id="dialog-buttons"):
            yield CustomButton("YES", id="confirm")
            yield CustomButton("NO", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.db.reset_database()
            if self.callback: self.callback()
            self.notify("Database Reset!", severity="warning")
            self.close()
        elif event.button.id == "cancel":
            self.close()

class DatabaseSettingsWindow(DraggableWindow):
    """صفحة إدارة قاعدة البيانات"""
    def __init__(self, db, callback=None):
        super().__init__(title="DATABASE MANAGEMENT")
        self.db = db
        self.callback = callback

    def compose_content(self) -> ComposeResult:
        with Vertical(id="settings-content"):
            yield Static("\nDatabase Tools\n", classes="section-header")
            with Vertical(classes="mgmt-group"):
                yield Static("Permanently delete everything?")
                yield CustomButton("Reset Database", id="reset-db")
            with Horizontal(id="dialog-buttons"):
                yield CustomButton("Back", id="back")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reset-db":
             if hasattr(self.app.screen, "open_window"):
                 self.app.screen.open_window(ConfirmResetWindow(self.db, self.callback))
        elif event.button.id == "back":
            self.close()

class BatchPricesWindow(DraggableWindow):
    """شاشة تحرير الأسعار"""
    def __init__(self, db):
        super().__init__(title="BATCH PRICES EDITOR")
        self.db = db
        self.batch_prices = self.db.get_batch_prices()

    def compose_content(self) -> ComposeResult:
        with Vertical(id="prices-content"):
            for batch_name, prices in self.batch_prices.items():
                with Vertical(classes="batch-group"):
                    yield Static(f"--- BATCH {batch_name} ---", classes="batch-header")
                    with Horizontal(classes="price-field"):
                        yield Static("Mart: ", classes="field-label")
                        yield ArabicInput(value=str(prices['mart']), id=f"mart-{batch_name}", min_value=0)
                    with Horizontal(classes="price-field"):
                        yield Static("Rest: ", classes="field-label")
                        yield ArabicInput(value=str(prices['restaurant']), id=f"restaurant-{batch_name}", min_value=0)
            with Horizontal(id="prices-buttons"):
                yield CustomButton("Save All", id="save-prices", custom_width=14)
                yield CustomButton("Back", id="back-prices", custom_width=12)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-prices":
            await self.save_all_prices()
        elif event.button.id == "back-prices":
            self.close()

    async def save_all_prices(self) -> None:
        has_error = False
        for batch_name in self.batch_prices.keys():
            mart_input = self.query_one(f"#mart-{batch_name}")
            try:
                float(mart_input.value or 0)
                mart_input.remove_class("invalid")
            except ValueError:
                mart_input.add_class("invalid")
                has_error = True
            
            rest_input = self.query_one(f"#restaurant-{batch_name}")
            try:
                float(rest_input.value or 0)
                rest_input.remove_class("invalid")
            except ValueError:
                rest_input.add_class("invalid")
                has_error = True

        if has_error:
            self.notify("Please fix invalid price values", severity="error")
            return

        try:
            for batch_name in self.batch_prices.keys():
                mart_price = float(self.query_one(f"#mart-{batch_name}").value or 0)
                rest_price = float(self.query_one(f"#restaurant-{batch_name}").value or 0)
                self.db.update_batch_price(batch_name, mart_price, rest_price)
            self.notify("Prices saved!")
            self.close()
        except Exception as e: self.notify(str(e), severity="error")


class SettingsWindow(DraggableWindow):
    """شاشة الإعدادات"""
    def __init__(self, db, callback=None, focus_section=None):
        super().__init__(title="SETTINGS")
        self.db = db
        self.callback = callback
        self.focus_section = focus_section
        self.settings = self.db.get_settings()
        self.batch_prices = self.db.get_batch_prices()

    def compose_content(self) -> ComposeResult:
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
            
            # أزرار التحكم (Grid)
            with Grid(id="settings-buttons-grid"):
                yield CustomButton("Save", id="save", custom_width=16)
                yield CustomButton("Edit Prices", id="edit-prices", custom_width=16)
                yield CustomButton("Export Report", id="export-report", custom_width=16)
                yield CustomButton("Database", id="database-mgmt", custom_width=16)
                yield CustomButton("Close", id="back", custom_width=16)

    def on_mount(self) -> None:
        if self.focus_section == "mode":
             self.set_timer(0.1, lambda: self.query_one("#mode-selector").focus())
        elif self.focus_section == "batch":
             self.set_timer(0.1, lambda: self.query_one("#batch-selector").focus())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            await self.save_settings()
        elif event.button.id == "edit-prices":
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(BatchPricesWindow(self.db))
        elif event.button.id == "export-report":
            await self.export_report()
        elif event.button.id == "database-mgmt":
            if hasattr(self.app.screen, "open_window"):
                self.app.screen.open_window(DatabaseSettingsWindow(self.db, self.callback))
        elif event.button.id == "back":
            self.close()

    async def export_report(self) -> None:
        try:
            from datetime import datetime
            from pathlib import Path
            
            report_content = self.db.generate_report()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"talabat_report_{timestamp}.txt"
            filepath = Path(filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.notify(f"Report exported: {filename}", severity="information")
        except Exception as e:
            self.notify(f"Export failed: {str(e)}", severity="error")

    async def save_settings(self) -> None:
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
            self.close()
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")
