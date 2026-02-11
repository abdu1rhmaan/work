from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime

ModeType = Literal["CASH", "VISA"]
OrderType = Literal["Restaurant", "Mart", "Friendly Restaurant"]

@dataclass
class Settings:
    """نمط الإعدادات"""
    mode: ModeType = "CASH"
    batch: str = "1"
    personal_wallet: float = 0.0
    company_wallet: float = 0.0

@dataclass
class BatchPrice:
    """نمط أسعار الباتش"""
    batch_name: str
    mart_price: float
    restaurant_price: float

@dataclass
class Order:
    """نمط الطلب"""
    id: Optional[int] = None
    datetime: str = ""
    mode: ModeType = "CASH"
    order_type: OrderType = "Restaurant"
    paid: float = 0.0
    expected: float = 0.0
    actual: float = 0.0
    tip_cash: float = 0.0
    tip_visa: float = 0.0
    delivery_fee: float = 0.0
    personal_wallet_effect: float = 0.0
    company_wallet_effect: float = 0.0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """إنشاء طلب من قاموس"""
        return cls(
            id=data.get('id'),
            datetime=data.get('datetime', ''),
            mode=data.get('mode', 'CASH'),
            order_type=data.get('order_type', 'Restaurant'),
            paid=data.get('paid', 0.0),
            expected=data.get('expected', 0.0),
            actual=data.get('actual', 0.0),
            tip_cash=data.get('tip_cash', 0.0),
            tip_visa=data.get('tip_visa', 0.0),
            delivery_fee=data.get('delivery_fee', 0.0),
            personal_wallet_effect=data.get('personal_wallet_effect', 0.0),
            company_wallet_effect=data.get('company_wallet_effect', 0.0)
        )
    
    def to_dict(self) -> dict:
        """تحويل الطلب إلى قاموس"""
        return {
            'id': self.id,
            'datetime': self.datetime,
            'mode': self.mode,
            'order_type': self.order_type,
            'paid': self.paid,
            'expected': self.expected,
            'actual': self.actual,
            'tip_cash': self.tip_cash,
            'tip_visa': self.tip_visa,
            'delivery_fee': self.delivery_fee,
            'personal_wallet_effect': self.personal_wallet_effect,
            'company_wallet_effect': self.company_wallet_effect
        }