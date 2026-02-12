from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static
from textual import events
from datetime import datetime
from ..database import Database
from ..utils import format_arabic
from .components import CustomButton, WalletDisplay, ModeDisplay, BatchDisplay, ShiftTimerDisplay
from .add_order import AddOrderScreen
from .history import HistoryScreen
from .settings import SettingsScreen
from .settlement import SettlementScreen
from .wallet import WalletScreen
from .shift import ShiftSummaryScreen, ShiftsHistoryScreen
from .calendar_screen import CalendarScreen
# from .shift_dialogs import ShiftDetailsDialog # Removed invalid import

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
                # yield ShiftTimerDisplay(id="shift-timer") # Removed old timer, replaced with status text
                yield Static("Loading Status...", id="shift-status-header", classes="status-header")
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
                # yield CustomButton("", id="shift-toggle") # Replaced
                yield CustomButton("Shift Calendar", id="shift-calendar")
                yield CustomButton("Add Order", id="add-order")
                yield CustomButton("Analysis", id="profit-chart")
                yield CustomButton("Order History", id="history")
                yield CustomButton("Shift History", id="shifts-history")
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
        self.db.check_auto_updates() # Run once on mount
        self.update_wallets()
        self.update_stats()
        self.update_shift_status()
        self.set_interval(1, self.update_shift_status) # Update status every second for timer
        self.set_interval(60, self.db.check_auto_updates) # Periodic check every minute
    
    def update_shift_status(self) -> None:
        """تحديث نص حالة الوردية والمؤقت في الهيدر"""
        # التحقق من التحديثات التلقائية (انتهاء الوردية تلقائياً)
        ended_summary = self.db.check_auto_updates()
        if ended_summary:
            from .shift import ShiftSummaryScreen
            self.app.push_screen(ShiftSummaryScreen(ended_summary))
            self.notify("🏁 Shift finished automatically!", severity="information")
        
        status_widget = self.query_one("#shift-status-header")
        data = self.db.get_dashboard_status()
        
        # Safe references for click handling
        self.status_data = data
        
        state = data.get('state')
        
        if state == 'BREAK':
            # Neon Yellow for Break
            elapsed = data['elapsed_seconds']
            remaining = data.get('remaining_seconds')
            
            m_e, s_e = divmod(elapsed, 60)
            elapsed_str = f"{m_e:02d}:{s_e:02d}"
            
            if remaining is not None and remaining > 0:
                m_r, s_r = divmod(remaining, 60)
                status_widget.update(f"⏸ [yellow]On Break[/] — [b]{m_r:02d}:{s_r:02d}[/] left")
            else:
                status_widget.update(f"⏸ [yellow]On Break[/] — [b]{elapsed_str}[/]")
            return # Block upcoming

        elif state == 'SHIFT_ACTIVE':
            # Neon Green for Active
            rem = data['remaining_seconds']
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            
            timer_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            status_widget.update(f"✅ [green]Shift Active[/] — Ends in [b]{timer_str}[/]")
            return # Block upcoming
            
        elif state == 'NEXT_UPCOMING':
            # Neon Blue/Cyan for Upcoming
            wait = data['wait_seconds']
            
            # Smart Timer Logic: 
            # If wait > 1 hour (3600 seconds), show fixed time.
            # If wait <= 1 hour, show countdown timer.
            if wait > 3600:
                start_time_str = data['scheduled_start']
                try:
                    # Format as AM/PM for easier reading
                    formatted_time = datetime.strptime(start_time_str, "%H:%M").strftime("%I:%M %p")
                except:
                    formatted_time = start_time_str
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts at [b]{formatted_time}[/]")
            else:
                h_w, m_w = divmod(wait // 60, 60)
                s_w = wait % 60
                timer_w = f"{h_w:02d}:{m_w:02d}:{s_w:02d}" if h_w > 0 else f"{m_w:02d}:{s_w:02d}"
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts in [b]{timer_w}[/]")
            
        else:
            status_widget.update("😴 [white]No Shift Today[/]")

    async def on_click(self, event: events.Click) -> None:
        """عند الضغط على الهيدر لإدارة الوردية"""
        try:
            # Safe access to the widget that was clicked
            # In Textual, Click events usually have the widget or can be traced
            widget = getattr(event, "widget", None)
            if not widget:
                 # Fallback to get_widget_at if event.widget is missing
                 widget, _ = self.app.get_widget_at(event.screen_x, event.screen_y)
            
            curr = widget
            while curr:
                if curr.id and curr.id in ["info-row", "shift-status-header", "mode-display", "batch-display"]:
                    await self.manage_shift_from_header()
                    return
                if curr == self: break
                curr = getattr(curr, "parent", None)
        except:
             pass

    async def manage_shift_from_header(self) -> None:
        """فتح بوب إدارة الوردية من الهيدر"""
        from .calendar_screen import ShiftDetailsDialog
        
        status = getattr(self, "status_data", {})
        shift_id = status.get('shift_id')
        
        if shift_id:
            shift = self.db.get_shift_summary(shift_id)
            if shift:
                await self.app.push_screen(ShiftDetailsDialog(self.db, shift, self.on_shift_change))
            else:
                await self.app.push_screen(CalendarScreen(self.db))
        else:
            await self.app.push_screen(CalendarScreen(self.db))

    def on_shift_change(self) -> None:
        """تحديث الواجهة بعد تغيير حالة الوردية"""
        self.update_shift_status()
        self.update_wallets()
    
    def update_stats(self) -> None:
        """تحديث الإحصائيات"""
        avg_profit = self.db.get_average_profit_per_day_with_orders()
        
        # ✅ FIX: Get today's date in proper format to match database
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get all orders and filter for today
        # Database stores datetime as ISO format (YYYY-MM-DDTHH:MM:SS)
        all_orders = self.db.get_all_orders(limit=1000)  # Get enough orders
        today_orders = [
            order for order in all_orders 
            if order['datetime'].startswith(today)
        ]
        
        # Calculate today's profit from delivery fees and tips
        today_profit = sum(
            order['delivery_fee'] + order['tip_cash'] + order['tip_visa']
            for order in today_orders
        )
        
        stats_text = (
            f"Today's Profit: {today_profit:.2f} EGP\n"
            f"Daily Average: {avg_profit:.2f} EGP\n"
            f"Total Orders: {len(all_orders)}"
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
        
        if button_id == "shift-calendar":
            await self.app.push_screen(CalendarScreen(self.db))
        elif button_id == "add-order":
            # CHECK ORDER RESTRICTION
            is_allowed, msg = self.db.is_order_allowed()
            if not is_allowed:
                 self.notify(msg, severity="error")
                 return
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
        self.update_shift_status() # Refresh status
    
    def on_key(self, event: events.Key) -> None:
        """معالجة ضغطات المفاتيح"""
        if event.key == "q":
            self.app.exit()
