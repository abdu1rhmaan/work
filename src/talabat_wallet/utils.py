import sys
import os
from pathlib import Path
from typing import Optional
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SUPPORT = True
except ImportError:
    HAS_ARABIC_SUPPORT = False

import re

def format_arabic(text: str) -> str:
    """معالجة النصوص العربية لتظهر بشكل صحيح (غير متقطعة وغير معكوسة)"""
    if not text or not HAS_ARABIC_SUPPORT:
        return text
    
    # فحص ما إذا كان النص يحتوي على حروف عربية
    if not re.search(r'[\u0600-\u06FF]', text):
        return text
        
    try:
        # معالجة الحروف لتصبح متصلة
        reshaped_text = arabic_reshaper.reshape(text)
        # معالجة اتجاه النص (Bidirectional)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        # في حالة حدوث أي خطأ، نعود للنص الأصلي لضمان عدم توقف البرنامج
        return text

def get_data_directory() -> Path:
    """الحصول على دليل البيانات"""
    if sys.platform == "linux":
        # لنظام Termux والأنظمة المشابهة
        termux_path = Path("/data/data/com.termux/files/home/.talabat_wallet")
        if termux_path.exists():
            return termux_path
        
        # لنظام Linux العادي
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / "talabat_wallet"
        
        return Path.home() / ".local" / "share" / "talabat_wallet"
    
    elif sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "TalabatWallet"
    
    else:  # macOS وغيرها
        return Path.home() / "Library" / "Application Support" / "TalabatWallet"

def format_currency(amount: float) -> str:
    """تنسيق المبلغ المالي"""
    if amount >= 0:
        return f"{amount:,.2f} SAR"
    else:
        return f"-{abs(amount):,.2f} SAR"

def validate_positive_number(value: str, field_name: str = "Value") -> Optional[float]:
    """التحقق من أن القيمة عدد موجب"""
    try:
        num = float(value)
        if num < 0:
            raise ValueError(f"{field_name} cannot be negative")
        return num
    except ValueError:
        raise ValueError(f"Invalid {field_name.lower()}. Must be a positive number.")

def truncate_text(text: str, max_length: int = 20) -> str:
    """تقليل النص إذا كان طويلاً"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def calculate_percentage(value: float, total: float) -> float:
    """حساب النسبة المئوية"""
    if total == 0:
        return 0.0
    return (value / total) * 100