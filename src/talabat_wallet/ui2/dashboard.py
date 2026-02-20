from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Static
from textual import events, on
from datetime import datetime
from ..database import Database
from ..utils import format_arabic
from .components import CustomButton, WalletDisplay, ModeDisplay, BatchDisplay
# Import base window only
from .window import BaseWindow

class DashboardScreen(Screen):
    """شاشة لوحة التحكم الرئيسية (MDI Version)"""
    
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

    def on_mount(self) -> None:
        """تهيئة الشاشة"""
        self.db.check_auto_updates()
        self.update_wallets()
        self.update_stats()
        self.update_shift_status()
        self.set_interval(1, self.update_shift_status)
        self.set_interval(60, self.db.check_auto_updates)
        self.set_focus(None)

    @on(BaseWindow.WindowResized)
    def handle_window_resize_msg(self, event: BaseWindow.WindowResized) -> None:
        """Live feedback of focused window size in footer."""
        pass

    @on(BaseWindow.OrderAdded)
    @on(BaseWindow.DataChanged)
    @on(BaseWindow.ShiftUpdated)
    async def handle_data_update(self, event=None) -> None:
        """Update dashboard stats instantly when data is modified in a window"""
        # 🏎️ Optimize: Debounce stats update
        self.set_timer(0.2, self.update_stats)
        self.update_wallets()
        
        # 📣 Forward to ALL open windows so they refresh siblings
        sender = getattr(event, "sender", None)
        for window in self.query(BaseWindow):
            if window != sender:
                window.post_message(event)

    @on(BaseWindow.GlobalSettingsChanged)
    def handle_settings_update(self, event: BaseWindow.GlobalSettingsChanged) -> None:
        """Reactive UI: Handle settings changes (mode, batch) instantly"""
        self.settings = event.settings
        self.update_stats()
        
        # 📣 Forward to peers
        sender = getattr(event, "sender", None)
        for window in self.query(BaseWindow):
            if window != sender:
                window.post_message(event)

    def on_show(self) -> None:
        self.set_focus(None)
    
    def update_shift_status(self) -> None:
        """تحديث نص حالة الوردية والمؤقت في الهيدر"""
        data = self.db.get_dashboard_status()
        status_widget = self.query_one("#shift-status-header")
        state = data.get('state')
        
        if state == 'FINISHED':
             status_widget.update(f"🏁 [white]Shift Finished[/] — See History")

        elif state == 'BREAK':
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
            if rem <= 0:
                abs_rem = abs(rem)
                m, s = divmod(abs_rem, 60)
                h, m = divmod(m, 60)
                status_widget.update(f"🏁 [white]Finished[/] — Wrap up")
            else:
                m, s = divmod(rem, 60)
                h, m = divmod(m, 60)
                timer_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                status_widget.update(f"✅ [green]Shift Active[/] — Ends in [b]{timer_str}[/]")
            
        elif state == 'NEXT_UPCOMING':
            wait = data['wait_seconds']
            if wait > 3600:
                start_time_str = data['scheduled_start']
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts at [b]{start_time_str}[/]")
            elif wait < 0:
                abs_wait = abs(wait)
                hours_late = abs_wait // 3600
                m_late = (abs_wait % 3600) // 60
                status_widget.update(f"❌ [error]Late by {int(hours_late)}h {int(m_late)}m[/]")
            else:
                h_w, m_w = divmod(wait // 60, 60)
                s_w = wait % 60
                timer_w = f"{h_w:02d}:{m_w:02d}:{s_w:02d}" if h_w > 0 else f"{m_w:02d}:{s_w:02d}"
                status_widget.update(f"⏳ [cyan]Next Shift[/] — Starts in [b]{timer_w}[/]")
        else:
            status_widget.update("😴 [white]No Shift Today[/]")

    async def on_base_window_closed(self, message: BaseWindow.Closed) -> None:
        """Handle window closing."""
        self.call_after_refresh(self.update_window_mode)

    def update_window_mode(self) -> None:
        """Update window-mode class based on open windows."""
        windows = self.query(BaseWindow)
        if len(windows) > 0:
            self.add_class("window-mode")
        else:
            self.remove_class("window-mode")

    def open_window(self, window: BaseWindow) -> None:
        """Open a window — mounted at Screen level so it floats above everything."""
        count = len(self.query(BaseWindow))
        self.mount(window)
        # Offset each new window slightly so they cascade
        window.styles.offset = (4 + (count * 3), 3 + (count * 2))
        window.focus()
        self.update_window_mode()
        
    def on_click(self, event: events.Click) -> None:
        """Handle clicks on the dashboard and background focus"""
        # 1. Check if we should clear focus
        target, _ = self.app.screen.get_widget_at(event.screen_x, event.screen_y)
        
        # If click is on a window or its children, DO NOT clear focus
        if any(isinstance(p, BaseWindow) for p in target.ancestors_with_self):
            return

        if target in [self, self.query_one("#desktop"), self.query_one("#dashboard-layout")]:
            self.set_focus(None)
            return

        # 2. Handle header/stat clicks
        widget_id = event.widget.id
        
        if widget_id == "mode-display":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.handle_data_update, focus_section="mode"))
        elif widget_id == "batch-display":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.handle_data_update, focus_section="batch"))
        elif widget_id == "shift-status-header":
             from .shift import ShiftDetailsWindow, DayShiftsWindow
             status = self.db.get_dashboard_status()
             state = status.get('state')
             from datetime import date
             
             if state in ['SHIFT_ACTIVE', 'BREAK']:
                 curr = self.db.get_active_shift()
                 if curr:
                     self.open_window(ShiftDetailsWindow(self.db, curr, self.handle_data_update))
                 else:
                     self.notify("No active shift", severity="error")
             else:
                 today_str = date.today().strftime("%Y-%m-%d")
                 shifts = self.db.get_shifts_by_date(today_str)
                 scheduled = next((s for s in shifts if s['status'] == 'SCHEDULED'), None)
                 if scheduled:
                      self.open_window(ShiftDetailsWindow(self.db, scheduled, self.handle_data_update))
                 else:
                      self.open_window(DayShiftsWindow(self.db, today_str, self.handle_data_update))
        elif widget_id in ["wallets-row", "personal-wallet", "company-wallet"]:
             from .wallet import WalletWindow
             self.open_window(WalletWindow(self.db, on_close=self.handle_data_update))

    async def on_button_pressed(self, event: CustomButton.Pressed) -> None:
        """معالجة ضغط الأزرار"""
        btn_id = event.button.id
        
        if btn_id == "btn_add_order":
             from .add_order import AddOrderWindow
             is_allowed, msg = self.db.is_order_allowed()
             if not is_allowed:
                 self.notify(msg, severity="error")
                 return
             self.open_window(AddOrderWindow(self.db, callback=self.handle_data_update))
        elif btn_id == "btn_wallet":
             from .wallet import WalletWindow
             self.open_window(WalletWindow(self.db, on_close=self.handle_data_update))
        elif btn_id == "btn_settings":
             from .settings import SettingsWindow
             self.open_window(SettingsWindow(self.db, callback=self.handle_data_update))
        elif btn_id == "btn_shift":
             from .shift import CalendarWindow
             self.open_window(CalendarWindow(self.db))
        elif btn_id == "btn_exit":
             self.app.exit()
        elif btn_id == "btn_history":
             from .history import OrderHistoryWindow
             self.open_window(OrderHistoryWindow(self.db))
        elif btn_id == "btn_analysis":
             from .history import AnalysisWindow
             self.open_window(AnalysisWindow(self.db))
        elif btn_id == "btn_shift_history":
             from .shift import ShiftsHistoryWindow
             self.open_window(ShiftsHistoryWindow(self.db))
        elif btn_id == "btn_settlement":
             from .settlement import SettlementWindow
             self.open_window(SettlementWindow(self.db, callback=self.handle_data_update))
             
        self.handle_data_update()

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
            today_orders = self.db.get_all_orders(period="Today")
            
            today_profit = sum(o['delivery_fee'] + o['tip_cash'] + o['tip_visa'] for o in today_orders)
            
            # Determine active shift stats if available
            status_data = self.db.get_dashboard_status()
            shift_info = ""
            if status_data.get('state') == 'SHIFT_ACTIVE':
                 # Calculate elapsed time in simple terms
                 elapsed = status_data.get('elapsed_seconds', 0)
                 e_h, e_rem = divmod(elapsed, 3600)
                 e_m = e_rem // 60
                 shift_info = f" | Shift active: [b]{e_h}h {e_m}m[/]"
            
            txt = f" Today: [b]{today_profit:.2f}[/] EGP | Orders: [b]{len(today_orders)}[/]{shift_info} | Avg Day: [b]{avg:.2f}[/] EGP"
            # Stats update removed since footer is deleted
        except:
            pass
