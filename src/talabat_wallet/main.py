from __future__ import annotations
import sys
import os

# Add the 'src' directory to the Python path to allow running directly
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer

from talabat_wallet.ui2.dashboard import DashboardScreen
from talabat_wallet.ui2.window import BaseWindow

class TalabatWalletApp(App):
    """تطبيق المحفظة الرئيسي"""
    
    CSS_PATH = "styles.tcss"
    
    def __init__(self):
        super().__init__()
        BaseWindow.reset_registry()
        self.dark = True  # استخدام الوضع المظلم للتوافق مع TCSS
        
    def on_mount(self) -> None:
        """تهيئة التطبيق عند التشغيل"""
        self.push_screen(DashboardScreen())
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        yield Container(id="main-container")

    def on_click(self, event: events.Click) -> None:
        """إزالة التحديد عند الضغط على أي مساحة فارغة (ليس زراً أو عنصراً قابلاً للتركيز)"""
        try:
            # التحقق من العنصر الذي تم الضغط عليه
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
            if widget and not widget.can_focus:
                if self.screen.focused:
                    self.screen.set_focus(None)
        except:
            if self.screen.focused:
                self.screen.set_focus(None)

def main():
    """دالة التشغيل الرئيسية"""
    app = TalabatWalletApp()
    app.run()

if __name__ == "__main__":
    main()