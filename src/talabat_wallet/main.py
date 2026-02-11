import sys
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer
from .ui.dashboard import DashboardScreen

class TalabatWalletApp(App):
    """تطبيق المحفظة الرئيسي"""
    
    CSS_PATH = "styles.tcss"
    
    def __init__(self):
        super().__init__()
        self.dark = True  # استخدام الوضع المظلم للتوافق مع TCSS
        
    def on_mount(self) -> None:
        """تهيئة التطبيق عند التشغيل"""
        self.push_screen(DashboardScreen())
        
    def compose(self) -> ComposeResult:
        """بناء الواجهة"""
        yield Container(id="main-container")

def main():
    """دالة التشغيل الرئيسية"""
    app = TalabatWalletApp()
    app.run()

if __name__ == "__main__":
    main()