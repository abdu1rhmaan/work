from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static
from textual import events
from datetime import datetime
from ..database import Database
from ..utils import format_arabic
from ..ui.components import CustomButton, WalletDisplay, ModeDisplay, BatchDisplay, ShiftTimerDisplay
# Import base window only
from .window import DraggableWindow

class DashboardScreen(Screen):
    """شاشة لوحة التحكم الرئيسية (MDI Version)"""
    
    CSS = """
    #dashboard {
        layout: vertical;
        padding: 1;
        background: $surface;
    }

    #desktop {
        width: 100%;
        height: 1fr;
        position: relative;
        overflow: hidden; 
    }

    #dashboard-layout {
        width: 100%;
        height: auto;
        layout: vertical;
        align: center top;
    }

    /* --- Status Strip (Mode, Shift, Batch) --- */
    #info-row {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        background: $primary-darken-2;
        border: panel $primary;
    }

    #mode-display {
        width: 1fr;
        height: 100%;
        content-align: center middle;
        color: white;
        text-style: bold;
    }

    #batch-display {
        width: 1fr;
        height: 100%;
        content-align: center middle;
        color: white;
        text-style: bold;
    }
    
    .status-header {
        width: 1fr;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: white;
    }
    
    .status-header:hover {
        text-style: underline bold;
        color: $accent;
    }

    /* --- Wallets Strip --- */
    #wallets-row {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }
    
    /* Wallet status colors */
    .credit-balance { color: $success; }
    .debt-balance { color: $error; }

    /* --- Buttons Grid --- */
    #main-buttons {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 2;
        padding: 0;
        width: 100%;
        height: auto;
        max-height: 80%;
        align-horizontal: center;
        border: hidden;
    }

    /* --- Stats Footer --- */
    #stats-container {
        dock: bottom;
        height: 8;
        background: $panel;
        border-top: solid $primary;
        padding: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.settings = self.db.get_settings()
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        yield Header(show_clock=True)
        
        with Container(id="desktop"):
            with Vertical(id="dashboard-layout"):
                # 1. Info Row
                with Horizontal(id="info-row"):
                    yield ModeDisplay(self.settings['mode'], id="mode-display")
                    yield Static("Loading...", id="shift-status-header", classes="status-header")
                    yield BatchDisplay(self.settings['batch'], id="batch-display")
                
                # 2. Wallets Row
                with Horizontal(id="wallets-row"):
                    yield WalletDisplay("Personal Wallet", self.settings['personal_wallet'], id="personal-wallet")
                    yield WalletDisplay("Company Wallet", self.settings['company_wallet'], id="company-wallet")
                
                # 3. Main Buttons Area
                with Grid(id="main-buttons"):
                    yield CustomButton("Shift Calendar", id="btn_shift")
                    yield CustomButton("Add Order", id="btn_add_order")
                    yield CustomButton("Analysis", id="btn_analysis")
                    yield CustomButton("Order History", id="btn_history")
                    yield CustomButton("Shift History", id="btn_shift_history")
                    yield CustomButton("Wallet", id="btn_wallet")
                    yield CustomButton("Settlement", id="btn_settlement")
                    yield CustomButton("Settings", id="btn_settings")
                    yield CustomButton("Exit", id="btn_exit")
                
                # 4. Stats
                with Container(id="stats-container"):
                    yield Static(id="stats-display")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.db.check_auto_updates()
        self.update_wallets()
        self.update_stats()
        self.update_shift_status()
        self.set_interval(1, self.update_shift_status)
        self.set_interval(60, self.db.check_auto_updates)
        self.set_focus(None)

    def on_show(self) -> None:
        self.set_focus(None)
    
    def update_shift_status(self) -> None:
        """تحديث نص حالة الوردية والمؤقت في الهيدر"""
        data = self.db.get_dashboard_status()
        status_widget = self.query_one("#shift-status-header")
        state = data.get('state')
        
        if state == 'BREAK':
            elapsed = data['elapsed_seconds']
            remaining = data.get('remaining_seconds')
            m_e, s_e = divmod(elapsed, 60)
            if remaining is not None and remaining > 0:
                m_r, s_r = divmod(remaining, 60)
                status_widget.update(f"⏸ [yellow]On Break[/] — [b]{m_r:02d}:{s_r:02d}[/] left")
            else:
                status_widget.update(f"⏸ [yellow]On Break[/] — [b]{m_e:02d}:{s_e:02d}[/]")

        elif state == 'SHIFT_ACTIVE':
            rem = data['remaining_seconds']
            if rem < 0: rem = 0
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            timer_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            status_widget.update(f"✅ [green]Shift Active[/] — Ends in [b]{timer_str}[/]")
            
        elif state == 'NEXT_UPCOMING':
            wait = data['wait_seconds']
            if wait > 3600:
                start_time_str = data['scheduled_start']
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts at [b]{start_time_str}[/]")
            else:
                h_w, m_w = divmod(wait // 60, 60)
                s_w = wait % 60
                timer_w = f"{h_w:02d}:{m_w:02d}:{s_w:02d}" if h_w > 0 else f"{m_w:02d}:{s_w:02d}"
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts in [b]{timer_w}[/]")
        else:
            status_widget.update("😴 [white]No Shift Today[/]")

    async def on_draggable_window_closed(self, message: DraggableWindow.Closed) -> None:
        """Handle window closing."""
        self.call_after_refresh(self.update_window_mode)

    def update_window_mode(self) -> None:
        """Update window-mode class and interactivity based on open windows."""
        desktop = self.query_one("#desktop")
        windows = desktop.query(DraggableWindow)
        is_window_open = len(windows) > 0
        
        if is_window_open:
            self.add_class("window-mode")
        else:
            self.remove_class("window-mode")

    def open_window(self, window: DraggableWindow) -> None:
        """Open a window on the desktop."""
        desktop = self.query_one("#desktop")
        desktop.mount(window)
        count = len(desktop.query(DraggableWindow))
        window.styles.offset = (2 + (count * 3), 2 + (count * 3))
        window.focus()
        self.update_window_mode()
        
    def on_click(self, event: events.Click) -> None:
        """Handle clicks on the dashboard and background focus"""
        # 1. Check if we should clear focus
        target, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
        if target in [self, self.query_one("#desktop"), self.query_one("#dashboard-layout")]:
            self.set_focus(None)
            return

        # 2. Handle header/stat clicks
        widget_id = event.widget.id
        
        if widget_id == "mode-display":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.update_wallets, focus_section="mode"))
        elif widget_id == "batch-display":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.update_wallets, focus_section="batch"))
        elif widget_id == "shift-status-header":
             from .shift import ShiftDetailsWindow, DayShiftsWindow
             status = self.db.get_dashboard_status()
             state = status.get('state')
             from datetime import date
             
             if state in ['SHIFT_ACTIVE', 'BREAK']:
                 curr = self.db.get_active_shift()
                 if curr:
                     self.open_window(ShiftDetailsWindow(self.db, curr, self.update_shift_status))
                 else:
                     self.notify("No active shift", severity="error")
             else:
                 today_str = date.today().strftime("%Y-%m-%d")
                 shifts = self.db.get_shifts_by_date(today_str)
                 scheduled = next((s for s in shifts if s['status'] == 'SCHEDULED'), None)
                 if scheduled:
                      self.open_window(ShiftDetailsWindow(self.db, scheduled, self.update_shift_status))
                 else:
                      self.open_window(DayShiftsWindow(self.db, today_str, self.update_shift_status))
        elif widget_id in ["wallets-row", "personal-wallet", "company-wallet"]:
             from .wallet import WalletWindow
             self.open_window(WalletWindow(self.db, on_close=self.update_wallets))

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        btn_id = event.button.id
        
        if btn_id == "btn_add_order":
             from .add_order import AddOrderWindow
             is_allowed, msg = self.db.is_order_allowed()
             if not is_allowed:
                 self.notify(msg, severity="error")
                 return
             self.open_window(AddOrderWindow(self.db, callback=self.update_wallets))
        elif btn_id == "btn_wallet":
             from .wallet import WalletWindow
             self.open_window(WalletWindow(self.db, on_close=self.update_wallets))
        elif btn_id == "btn_settings":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.update_wallets))
        elif btn_id == "btn_shift":
             from .shift import CalendarWindow
             self.open_window(CalendarWindow(self.db))
        elif btn_id == "btn_exit":
             self.app.exit()
        elif btn_id == "btn_history":
             from .history import OrderHistoryWindow
             self.open_window(OrderHistoryWindow(self.db))
        elif btn_id == "btn_analysis":
             from .history import OrderHistoryWindow
             history = OrderHistoryWindow(self.db)
             history.show_chart_only = True
             self.open_window(history)
        elif btn_id == "btn_shift_history":
             from .shift import ShiftsHistoryWindow
             self.open_window(ShiftsHistoryWindow(self.db))
        elif btn_id == "btn_settlement":
             from .settlement import SettlementWindow
             self.open_window(SettlementWindow(self.db, callback=self.update_wallets))
             
        self.update_wallets()

    def update_wallets(self) -> None:
        """تحديث عرض المحافظ"""
        self.settings = self.db.get_settings()
        self.query_one("#personal-wallet").value = self.settings['personal_wallet']
        
        cw = self.query_one("#company-wallet")
        val = self.settings['company_wallet']
        cw.value = val
        cw.remove_class("credit-balance")
        cw.remove_class("debt-balance")
        if val < 0: cw.add_class("credit-balance")
        elif val > 0: cw.add_class("debt-balance")
        
        self.query_one("#mode-display").mode = self.settings['mode']
        self.query_one("#batch-display").batch = self.settings['batch']
        self.update_stats()

    def update_stats(self) -> None:
        """تحديث الإحصائيات"""
        try:
            avg = self.db.get_average_profit_per_day_with_orders()
            today = datetime.now().strftime("%Y-%m-%d")
            all_orders = self.db.get_all_orders(limit=1000)
            today_orders = [o for o in all_orders if o['datetime'].startswith(today)]
            today_profit = sum(o['delivery_fee'] + o['tip_cash'] + o['tip_visa'] for o in today_orders)
            txt = f"Today's Profit: {today_profit:.2f} EGP\nDaily Average: {avg:.2f} EGP\nTotal Orders: {len(today_orders)}"
            self.query_one("#stats-display").update(format_arabic(txt))
        except:
            self.query_one("#stats-display").update("Stats Error")
