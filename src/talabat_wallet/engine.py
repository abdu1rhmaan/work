from datetime import datetime
from typing import Tuple
from .models import ModeType, OrderType, Order

class AccountingEngine:
    """محرك المحاسبة"""
    
    @staticmethod
    def calculate_order_effects(
        mode: ModeType,
        order_type: OrderType,
        paid: float,
        expected: float,
        actual: float,
        delivery_fee: float,
        manual_tip_cash: float = 0.0,
        manual_tip_visa: float = 0.0
    ) -> Tuple[float, float, float, float]:
        """
        حساب تأثيرات الطلب على المحافظ
        
        Returns:
            (personal_effect, company_effect, tip_cash, tip_visa)
        """
        tip_cash = 0.0
        tip_visa = 0.0
        personal_effect = 0.0
        company_effect = 0.0
        
        if mode == "CASH":
            if order_type == "Restaurant":
                # Restaurant + CASH
                personal_effect = -paid + actual
                company_effect = expected - paid
                tip_cash = max(actual - expected, 0)
            else:
                # Mart / Friendly Restaurant + CASH
                personal_effect = actual
                company_effect = expected
                tip_cash = max(actual - expected, 0)
                
        elif mode == "VISA":
            # VISA MODE: يتم إدخال البقشيش مباشرة أو حسابه
            # إذا دخلت أرقام للـ manual_tips نستخدمها
            if manual_tip_cash > 0 or manual_tip_visa > 0:
                tip_cash = manual_tip_cash
                tip_visa = manual_tip_visa
            else:
                # توافق خلفي مع الطريقة القديمة إذا لم تتوفر المدخلات الجديدة
                tip_visa = actual
                tip_cash = max(paid - expected, 0)
                
            personal_effect = tip_cash
            company_effect = -tip_visa
        
        # إضافة رسوم التوصيل
        company_effect += delivery_fee
        
        return personal_effect, company_effect, tip_cash, tip_visa
    
    @staticmethod
    def create_order(
        mode: ModeType,
        order_type: OrderType,
        paid: float,
        expected: float,
        actual: float,
        delivery_fee: float = 0.0,
        tip_cash: float = 0.0,
        tip_visa: float = 0.0
    ) -> Order:
        """إنشاء طلب جديد مع حساب التأثيرات"""
        personal_effect, company_effect, tip_cash, tip_visa = \
            AccountingEngine.calculate_order_effects(
                mode, order_type, paid, expected, actual, delivery_fee,
                manual_tip_cash=tip_cash, manual_tip_visa=tip_visa
            )
        
        return Order(
            datetime=datetime.now().isoformat(),
            mode=mode,
            order_type=order_type,
            paid=paid,
            expected=expected,
            actual=actual,
            tip_cash=tip_cash,
            tip_visa=tip_visa,
            delivery_fee=delivery_fee,
            personal_wallet_effect=personal_effect,
            company_wallet_effect=company_effect
        )
    
    @staticmethod
    def calculate_profit(
        delivery_fee: float,
        tip_cash: float,
        tip_visa: float
    ) -> float:
        """حساب الربح"""
        return delivery_fee + tip_cash + tip_visa
    
    @staticmethod
    def validate_order_values(
        order_type: OrderType,
        paid: float,
        expected: float,
        actual: float,
        delivery_fee: float
    ) -> Tuple[bool, str]:
        """التحقق من صحة قيم الطلب"""
        if paid < 0:
            return False, "المبلغ المدفوع لا يمكن أن يكون سالبًا"
        if expected < 0:
            return False, "المبلغ المتوقع لا يمكن أن يكون سالبًا"
        if actual < 0:
            return False, "المبلغ الفعلي لا يمكن أن يكون سالبًا"
        if delivery_fee < 0:
            return False, "رسوم التوصيل لا يمكن أن تكون سالبة"
        
        return True, ""