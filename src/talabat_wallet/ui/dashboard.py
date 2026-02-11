from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static
from textual import events
from datetime import datetime
from ..database import Database
from ..utils import format_arabic
from .components import CustomButton, WalletDisplay, ModeDisplay, BatchDisplay
from .add_order import AddOrderScreen
from .history import HistoryScreen
from .settings import SettingsScreen
from .settlement import SettlementScreen
from .wallet import WalletScreen
from .shift import ShiftSummaryScreen, ShiftsHistoryScreen

class DashboardScreen(Screen):
    """شاشة لوحة التحكم الرئيسية"""
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.settings = self.db.get_settings()
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        yield Header(show_clock=True)
        
        with Container(id="dashboard"):
            # صف المعلومات العلوي
            with Horizontal(id="info-row"):
                yield ModeDisplay(self.settings['mode'], id="mode-display")
                yield BatchDisplay(self.settings['batch'], id="batch-display")
            
            # عرض المحافظ
            with Horizontal(id="wallets-row"):
                yield WalletDisplay(
                    "Personal Wallet", 
                    self.settings['personal_wallet'],
                    id="personal-wallet"
                )
                yield WalletDisplay(
                    "Company Wallet", 
                    self.settings['company_wallet'],
                    id="company-wallet"
                )
            
            # الأزرار الرئيسية
            with Grid(id="main-buttons"):
                yield CustomButton("", id="shift-toggle")
                yield CustomButton("Add Order", id="add-order")
                yield CustomButton("Analysis", id="profit-chart")
                yield CustomButton("History", id="history")
                yield CustomButton("Shifts", id="shifts-history")
                yield CustomButton("Wallet", id="wallet-btn")
                yield CustomButton("Settlement", id="settlement")
                yield CustomButton("Settings", id="settings")
                yield CustomButton("Exit", id="exit")
            
            # الإحصائيات
            with Container(id="stats-container"):
                yield Static(id="stats-display")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.update_wallets()
        self.update_stats()
        
        # تحديث زر الوردية
        active_shift = self.db.get_active_shift()
        shift_button = self.query_one("#shift-toggle")
        shift_button.label = "End Shift" if active_shift else "Start Shift"
    
    def update_stats(self) -> None:
        """تحديث الإحصائيات"""
        avg_profit = self.db.get_average_profit_per_day_with_orders()
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = self.db.get_orders_by_date_range(today + " 00:00:00", today + " 23:59:59")
        
        today_profit = sum(
            order['delivery_fee'] + order['tip_cash'] + order['tip_visa']
            for order in today_orders
        )
        
        stats_text = (
            f"Today's Profit: {today_profit:.2f} EGP\n"
            f"Daily Average: {avg_profit:.2f} EGP\n"
            f"Total Orders: {len(self.db.get_all_orders())}"
        )
        
        self.query_one("#stats-display").update(format_arabic(stats_text))
    
    def update_wallets(self) -> None:
        """تحديث عرض المحافظ"""
        self.settings = self.db.get_settings()
        
        personal_wallet = self.query_one("#personal-wallet")
        company_wallet = self.query_one("#company-wallet")
        mode_display = self.query_one("#mode-display")
        batch_display = self.query_one("#batch-display")
        
        personal_wallet.value = self.settings['personal_wallet']
        
        # تلوين ديناميكي لمحفظة الشركة
        val = self.settings['company_wallet']
        company_wallet.value = val
        
        company_wallet.remove_class("credit-balance")
        company_wallet.remove_class("debt-balance")
        
        if val < 0:
            company_wallet.add_class("credit-balance")
        elif val > 0:
            company_wallet.add_class("debt-balance")
            
        mode_display.mode = self.settings['mode']
        batch_display.batch = self.settings['batch']
        
        self.update_stats()
    
    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        button_id = event.button.id
        
        if button_id == "shift-toggle":
            await self.toggle_shift()
        elif button_id == "add-order":
            await self.app.push_screen(AddOrderScreen(self.db, self.update_wallets))
        elif button_id == "profit-chart":
            chart_screen = HistoryScreen(self.db)
            chart_screen.show_chart_only = True
            await self.app.push_screen(chart_screen)
        elif button_id == "history":
            await self.app.push_screen(HistoryScreen(self.db))
        elif button_id == "shifts-history":
            await self.app.push_screen(ShiftsHistoryScreen(self.db))
        elif button_id == "settlement":
            await self.app.push_screen(SettlementScreen(self.db, self.update_wallets))
        elif button_id == "wallet-btn":
            await self.app.push_screen(WalletScreen(self.db, self.update_wallets))
        elif button_id == "settings":
            await self.app.push_screen(SettingsScreen(self.db, self.update_wallets))
        elif button_id == "exit":
            self.app.exit()
        
        self.update_stats()
    
    async def toggle_shift(self) -> None:
        """تبديل حالة الوردية (بدء/إنهاء)"""
        active_shift = self.db.get_active_shift()
        shift_button = self.query_one("#shift-toggle")
        
        if active_shift:
            # إنهاء الوردية
            summary = self.db.end_shift()
            if summary:
                await self.app.push_screen(ShiftSummaryScreen(summary))
                self.notify("Shift ended successfully!", severity="information")
                shift_button.label = "Start Shift"
        else:
            # بدء وردية جديدة
            shift_id = self.db.start_shift()
            if shift_id:
                self.notify("Shift started!", severity="information")
                shift_button.label = "End Shift"
            else:
                self.notify("Failed to start shift", severity="error")
    
    def on_key(self, event: events.Key) -> None:
        """معالجة ضغطات المفاتيح"""
        if event.key == "q":
            self.app.exit()