import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

class Database:
    """فئة لإدارة قاعدة البيانات"""
    
    def __init__(self, db_path: str = "talabat_wallet.db"):
        """تهيئة قاعدة البيانات"""
        self.db_path = Path(db_path)
        self.init_database()
        self.migrate_database()
        
    def migrate_database(self) -> None:
        """تحديث هيكل قاعدة البيانات إذا لزم الأمر"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # تحقق من وجود عمود type في جدول expenses
            cursor.execute("PRAGMA table_info(expenses)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'type' not in columns:
                cursor.execute("ALTER TABLE expenses ADD COLUMN type TEXT NOT NULL DEFAULT 'OUT'")
            
            # تحقق من وجود عمود shift_id في جدول orders
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'shift_id' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN shift_id INTEGER")
            
            # تحقق من وجود عمود shift_id في جدول expenses
            cursor.execute("PRAGMA table_info(expenses)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'shift_id' not in columns:
                cursor.execute("ALTER TABLE expenses ADD COLUMN shift_id INTEGER")
            
            conn.commit()

    def add_expense(self, description: str, amount: float, txn_type: str = 'OUT') -> bool:
        """إضافة مصروف أو إيداع جديد"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # الحصول على الوردية النشطة إن وجدت
                cursor.execute("SELECT id FROM shifts WHERE is_active = 1")
                active_shift = cursor.fetchone()
                shift_id = active_shift[0] if active_shift else None
                
                cursor.execute(
                    "INSERT INTO expenses (datetime, description, amount, type, shift_id) VALUES (?, ?, ?, ?, ?)",
                    (now, description, amount, txn_type, shift_id)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_all_expenses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """الحصول على جميع العمليات (مصاريف وإيداعات)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM expenses ORDER BY datetime DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_wallet_stats(self) -> Dict[str, float]:
        """إحصائيات إجمالي المصاريف والإيداعات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN type = 'IN' THEN amount ELSE 0 END) as total_in,
                        SUM(CASE WHEN type = 'OUT' THEN amount ELSE 0 END) as total_out
                    FROM expenses
                """)
                row = cursor.fetchone()
                total_in = row[0] or 0.0
                total_out = row[1] or 0.0
                return {
                    'total_in': total_in,
                    'total_out': total_out,
                    'net': total_in - total_out
                }
        except Exception:
            return {'total_in': 0.0, 'total_out': 0.0, 'net': 0.0}

    def get_unique_descriptions(self, prefix: str = "") -> List[str]:
        """الحصول على أوصاف فريدة سابقة للاقتراحات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = "SELECT DISTINCT description FROM expenses"
                params = ()
                if prefix:
                    query += " WHERE description LIKE ?"
                    params = (f"{prefix}%",)
                query += " ORDER BY description LIMIT 5"
                cursor.execute(query, params)
                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []
        
    def init_database(self) -> None:
        """تهيئة جداول قاعدة البيانات"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # جدول الإعدادات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL DEFAULT 'CASH',
                    batch TEXT NOT NULL DEFAULT '1',
                    personal_wallet REAL NOT NULL DEFAULT 0.0,
                    company_wallet REAL NOT NULL DEFAULT 0.0
                )
            """)
            
            # جدول أسعار الباتشات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_prices (
                    batch_name TEXT PRIMARY KEY,
                    mart_price REAL NOT NULL,
                    restaurant_price REAL NOT NULL
                )
            """)
            
            # جدول الطلبات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    paid REAL NOT NULL,
                    expected REAL NOT NULL,
                    actual REAL NOT NULL,
                    tip_cash REAL NOT NULL DEFAULT 0.0,
                    tip_visa REAL NOT NULL DEFAULT 0.0,
                    delivery_fee REAL NOT NULL DEFAULT 0.0,
                    personal_wallet_effect REAL NOT NULL,
                    company_wallet_effect REAL NOT NULL
                )
            """)
            
            # إنشاء الفهارس
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_datetime ON orders(datetime)")
            
            # جدول المصاريف (Expenses)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL DEFAULT 'OUT',
                    shift_id INTEGER
                )
            """)
            
            # جدول الورديات (Shifts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    is_active INTEGER DEFAULT 1,
                    total_orders INTEGER DEFAULT 0,
                    total_income REAL DEFAULT 0.0,
                    total_expenses REAL DEFAULT 0.0,
                    net_profit REAL DEFAULT 0.0
                )
            """)
            
            # إدخال الإعدادات الافتراضية إذا لم تكن موجودة
            cursor.execute("SELECT COUNT(*) FROM settings")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO settings (mode, batch, personal_wallet, company_wallet)
                    VALUES ('CASH', '1', 0.0, 0.0)
                """)
            
            # إدخال أسعار الباتشات الافتراضية
            default_prices = [
                ('1', 20.0, 22.0),
                ('2', 18.0, 20.0),
                ('3', 16.0, 18.0),
                ('4', 14.0, 16.0),
                ('New', 12.0, 14.0)
            ]
            
            cursor.execute("SELECT COUNT(*) FROM batch_prices")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT OR REPLACE INTO batch_prices (batch_name, mart_price, restaurant_price)
                    VALUES (?, ?, ?)
                """, default_prices)
            
            conn.commit()
    
    def get_settings(self) -> Dict[str, Any]:
        """الحصول على الإعدادات الحالية"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """تحديث الإعدادات"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE settings 
                SET mode = ?, batch = ?, personal_wallet = ?, company_wallet = ?
                WHERE id = 1
            """, (
                settings['mode'],
                settings['batch'],
                settings['personal_wallet'],
                settings['company_wallet']
            ))
            conn.commit()
    
    def get_batch_prices(self) -> Dict[str, Dict[str, float]]:
        """الحصول على أسعار الباتشات"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_prices ORDER BY batch_name")
            rows = cursor.fetchall()
            
            prices = {}
            for row in rows:
                prices[row['batch_name']] = {
                    'mart': row['mart_price'],
                    'restaurant': row['restaurant_price']
                }
            return prices
    
    def update_batch_price(self, batch_name: str, mart_price: float, restaurant_price: float) -> None:
        """تحديث سعر الباتش"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO batch_prices (batch_name, mart_price, restaurant_price)
                VALUES (?, ?, ?)
            """, (batch_name, mart_price, restaurant_price))
            conn.commit()
    
    def add_order(self, order_data: Dict[str, Any]) -> int:
        """إضافة طلب جديد"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # الحصول على الوردية النشطة إن وجدت
            cursor.execute("SELECT id FROM shifts WHERE is_active = 1")
            active_shift = cursor.fetchone()
            shift_id = active_shift[0] if active_shift else None
            
            cursor.execute("""
                INSERT INTO orders (
                    datetime, mode, order_type, paid, expected, actual,
                    tip_cash, tip_visa, delivery_fee,
                    personal_wallet_effect, company_wallet_effect, shift_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data['datetime'],
                order_data['mode'],
                order_data['order_type'],
                order_data['paid'],
                order_data['expected'],
                order_data['actual'],
                order_data.get('tip_cash', 0.0),
                order_data.get('tip_visa', 0.0),
                order_data.get('delivery_fee', 0.0),
                order_data['personal_wallet_effect'],
                order_data['company_wallet_effect'],
                shift_id
            ))
            
            order_id = cursor.lastrowid
            
            # تحديث المحافظ
            settings = self.get_settings()
            new_personal = settings['personal_wallet'] + order_data['personal_wallet_effect']
            new_company = settings['company_wallet'] + order_data['company_wallet_effect']
            
            cursor.execute("""
                UPDATE settings 
                SET personal_wallet = ?, company_wallet = ?
                WHERE id = 1
            """, (new_personal, new_company))
            
            conn.commit()
            return order_id
    
    def delete_order(self, order_id: int) -> bool:
        """حذف طلب وإعادة حساب المحافظ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # الحصول على تأثير الطلب
            cursor.execute("""
                SELECT personal_wallet_effect, company_wallet_effect 
                FROM orders WHERE id = ?
            """, (order_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            personal_effect, company_effect = row
            
            # حذف الطلب
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            
            # تحديث المحافظ (عكس التأثير)
            settings = self.get_settings()
            new_personal = settings['personal_wallet'] - personal_effect
            new_company = settings['company_wallet'] - company_effect
            
            cursor.execute("""
                UPDATE settings 
                SET personal_wallet = ?, company_wallet = ?
                WHERE id = 1
            """, (new_personal, new_company))
            
            conn.commit()
            return True
    
    def get_all_orders(self, limit: int = 100, order_type: Optional[str] = None, period: Optional[str] = None) -> List[Dict[str, Any]]:
        """الحصول على جميع الطلبات مع دعم الفلترة"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if order_type and order_type != "All":
                query += " AND order_type = ?"
                params.append(order_type)
                
            if period and period != "All":
                now = datetime.now()
                if period == "Today":
                    start_date = now.strftime("%Y-%m-%d 00:00:00")
                    query += " AND datetime >= ?"
                    params.append(start_date)
                elif period == "Yesterday":
                    from datetime import timedelta
                    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                    query += " AND datetime >= ? AND datetime <= ?"
                    params.append(f"{yesterday} 00:00:00")
                    params.append(f"{yesterday} 23:59:59")
                elif period == "Week":
                    from datetime import timedelta
                    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
                    query += " AND datetime >= ?"
                    params.append(week_start)
                elif period == "Month":
                    month_start = now.strftime("%Y-%m-01 00:00:00")
                    query += " AND datetime >= ?"
                    params.append(month_start)
            
            query += " ORDER BY datetime DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على طلب محدد بواسطة المعرف"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """الحصول على الطلبات حسب النطاق الزمني"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders 
                WHERE datetime BETWEEN ? AND ?
                ORDER BY datetime
            """, (start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_daily_profit(self, days: int = 14) -> List[Dict[str, Any]]:
        """الحصول على الأرباح اليومية"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    DATE(datetime) as date,
                    SUM(delivery_fee + tip_cash + tip_visa) as profit,
                    COUNT(*) as orders_count
                FROM orders
                WHERE datetime >= DATE('now', ? || ' days')
                  AND mode != 'SETTLEMENT'
                GROUP BY DATE(datetime)
                ORDER BY date
            """, (f"-{days}",))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_analysis_stats(self, period: str = "DAILY") -> Dict[str, Any]:
        """الحصول على إحصائيات التحليل المتقدمة لفترة محددة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # تعريف فواصل الزمن بناءً على الفترة
                if period == "DAILY":
                    range_sql = "DATE(datetime) = DATE('now')"
                elif period == "WEEKLY":
                    range_sql = "datetime >= DATE('now', 'weekday 0', '-7 days')"
                elif period == "MONTHLY":
                    range_sql = "datetime >= DATE('now', 'start of month')"
                else:  # YEARLY
                    range_sql = "datetime >= DATE('now', 'start of year')"
                
                # حساب الدخل من الطلبات
                cursor.execute(f"""
                    SELECT 
                        SUM(delivery_fee) as delivery_income,
                        SUM(tip_cash) as tip_cash,
                        SUM(tip_visa) as tip_visa,
                        COUNT(*) as orders_count
                    FROM orders 
                    WHERE {range_sql} AND mode != 'SETTLEMENT'
                """)
                order_row = cursor.fetchone()
                
                # حساب المصاريف من جدول المحفظة
                cursor.execute(f"SELECT SUM(amount) FROM expenses WHERE {range_sql} AND type = 'OUT'")
                expense_row = cursor.fetchone()
                
                # تجميع البيانات
                delivery_income = order_row['delivery_income'] or 0.0
                tip_cash = order_row['tip_cash'] or 0.0
                tip_visa = order_row['tip_visa'] or 0.0
                total_tips = tip_cash + tip_visa
                total_income = delivery_income + total_tips
                total_expenses = expense_row[0] or 0.0
                orders_count = order_row['orders_count'] or 0
                
                # إحصائيات إضافية للشهري والسنوي
                best_month = ""
                daily_avg = 0.0
                
                if period == "MONTHLY":
                    # حساب المتوسط اليومي للشهر الحالي
                    import calendar
                    now = datetime.now()
                    # المتوسط يكون بناءً على الأيام المنقضية من الشهر حتى الآن
                    daily_avg = total_income / now.day if now.day > 0 else 0.0
                elif period == "YEARLY":
                    # الحصول على أفضل شهر
                    import calendar
                    cursor.execute("""
                        SELECT strftime('%m', datetime) as month_num, 
                               SUM(delivery_fee + tip_cash + tip_visa) as monthly_profit
                        FROM orders 
                        WHERE datetime >= DATE('now', 'start of year') AND mode != 'SETTLEMENT'
                        GROUP BY month_num ORDER BY monthly_profit DESC LIMIT 1
                    """)
                    best_month_row = cursor.fetchone()
                    if best_month_row:
                        m_idx = int(best_month_row['month_num'])
                        best_month = calendar.month_name[m_idx]
                    else:
                        best_month = "N/A"

                return {
                    'delivery_income': delivery_income,
                    'tip_cash': tip_cash,
                    'tip_visa': tip_visa,
                    'total_tips': total_tips,
                    'total_income': total_income,
                    'total_expenses': total_expenses,
                    'net_profit': total_income - total_expenses,
                    'orders_count': orders_count,
                    'daily_avg': daily_avg,
                    'best_month': best_month
                }
        except Exception as e:
            print(f"Error in get_analysis_stats: {e}")
            return {
                'delivery_income': 0.0, 'tip_cash': 0.0, 'tip_visa': 0.0,
                'total_tips': 0.0, 'total_income': 0.0, 'total_expenses': 0.0,
                'net_profit': 0.0, 'orders_count': 0, 'daily_avg': 0.0, 'best_month': "N/A"
            }

    async def update_order(self, order_id: int, new_data: dict) -> bool:
        """تحديث طلب موجود وتعديل المحافظ بناءً على الفروقات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 1. الحصول على البيانات القديمة لعكس تأثيرها
                cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
                old_order = cursor.fetchone()
                if not old_order:
                    return False
                
                # 2. عكس تأثير الطلب القديم على المحافظ
                cursor.execute("""
                    UPDATE settings SET 
                        personal_wallet = personal_wallet - ?,
                        company_wallet = company_wallet - ?
                """, (old_order['personal_wallet_effect'], old_order['company_wallet_effect']))
                
                # 3. تحديث بيانات الطلب (مع الحفاظ على التاريخ الأصلي)
                cursor.execute("""
                    UPDATE orders SET 
                        mode = ?, order_type = ?, paid = ?, expected = ?, actual = ?, 
                        delivery_fee = ?, tip_cash = ?, tip_visa = ?, 
                        personal_wallet_effect = ?, company_wallet_effect = ?
                    WHERE id = ?
                """, (
                    new_data['mode'], new_data['order_type'], new_data['paid'],
                    new_data['expected'], new_data['actual'], new_data['delivery_fee'],
                    new_data['tip_cash'], new_data['tip_visa'],
                    new_data['personal_wallet_effect'], new_data['company_wallet_effect'],
                    order_id
                ))
                
                # 4. تطبيق تأثير البيانات الجديدة على المحافظ
                cursor.execute("""
                    UPDATE settings SET 
                        personal_wallet = personal_wallet + ?,
                        company_wallet = company_wallet + ?
                """, (new_data['personal_wallet_effect'], new_data['company_wallet_effect']))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating order: {e}")
            return False

    def get_average_profit_per_day_with_orders(self) -> float:
        """حساب متوسط الربح اليومي للأيام التي تحتوي على طلبات فقط"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        SUM(delivery_fee + tip_cash + tip_visa) as total_profit,
                        COUNT(DISTINCT DATE(datetime)) as days_with_orders
                    FROM orders
                    WHERE mode != 'SETTLEMENT'
                """)
                row = cursor.fetchone()
                if not row or not row[0] or not row[1] or row[1] == 0:
                    return 0.0
                return row[0] / row[1]
        except Exception:
            return 0.0

    def reset_database(self) -> bool:
        """مسح جميع البيانات وإعادة ضبط قاعدة البيانات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM orders")
                cursor.execute("DELETE FROM expenses")
                cursor.execute("UPDATE settings SET personal_wallet = 0.0, company_wallet = 0.0")
                conn.commit()
            return True
        except Exception:
            return False
    
    def generate_report(self) -> str:
        """توليد تقرير شامل عن البرنامج بصيغة نصية منسقة"""
        from datetime import datetime
        
        lines = []
        lines.append("=" * 60)
        lines.append("           TALABAT DRIVER WALLET - COMPREHENSIVE REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        # الإعدادات الحالية
        settings = self.get_settings()
        lines.append("\n### CURRENT SETTINGS ###")
        lines.append(f"Accounting Mode:      {settings['mode']}")
        lines.append(f"Active Batch:         {settings['batch']}")
        lines.append(f"Personal Wallet:      {settings['personal_wallet']:.2f} EGP")
        lines.append(f"Company Wallet:       {settings['company_wallet']:.2f} EGP")
        lines.append(f"Combined Balance:     {settings['personal_wallet'] + settings['company_wallet']:.2f} EGP")
        
        # إحصائيات الطلبات
        lines.append("\n### ORDER STATISTICS ###")
        all_orders = self.get_all_orders(limit=9999)
        total_orders = len(all_orders)
        lines.append(f"Total Orders:         {total_orders}")
        
        if total_orders > 0:
            total_delivery = sum(o.get('delivery_fee', 0) for o in all_orders)
            total_tips = sum(o.get('tip_cash', 0) + o.get('tip_visa', 0) for o in all_orders)
            total_income = total_delivery + total_tips
            
            lines.append(f"Total Delivery Fees:  {total_delivery:.2f} EGP")
            lines.append(f"Total Tips:           {total_tips:.2f} EGP")
            lines.append(f"Total Income:         {total_income:.2f} EGP")
            
            # تفصيل حسب النوع
            types_count = {}
            for order in all_orders:
                order_type = order.get('order_type', 'Unknown')
                types_count[order_type] = types_count.get(order_type, 0) + 1
            
            lines.append("\nOrders by Type:")
            for order_type, count in sorted(types_count.items()):
                lines.append(f"  {order_type:15} {count:5} orders")
        
        # إحصائيات المصاريف
        wallet_stats = self.get_wallet_stats()
        lines.append("\n### PERSONAL ACCOUNTING ###")
        lines.append(f"Total Income:         +{wallet_stats['total_in']:.2f} EGP")
        lines.append(f"Total Expenses:       -{wallet_stats['total_out']:.2f} EGP")
        lines.append(f"Net Balance:          {wallet_stats['net']:.2f} EGP")
        
        # أسعار الباتشات
        batch_prices = self.get_batch_prices()
        lines.append("\n### BATCH PRICING ###")
        for batch, prices in batch_prices.items():
            lines.append(f"Batch {batch}:")
            lines.append(f"  Mart Price:         {prices['mart']:.2f} EGP")
            lines.append(f"  Restaurant Price:   {prices['restaurant']:.2f} EGP")
        
        # آخر 20 طلب
        lines.append("\n### RECENT ORDERS (Last 20) ###")
        recent_orders = self.get_all_orders(limit=20)
        if recent_orders:
            lines.append(f"{'ID':<5} {'Date':<12} {'Type':<12} {'Income':<10} {'Profit':<10}")
            lines.append("-" * 55)
            for order in recent_orders:
                order_id = order.get('id', 'N/A')
                date = order.get('datetime', 'N/A')[:10]
                order_type = order.get('order_type', 'N/A')[:12]
                income = order.get('delivery_fee', 0) + order.get('tip_cash', 0) + order.get('tip_visa', 0)
                profit = income
                lines.append(f"{order_id:<5} {date:<12} {order_type:<12} {income:<10.2f} {profit:<10.2f}")
        else:
            lines.append("No orders recorded yet.")
        
        # آخر 10 عمليات شخصية
        lines.append("\n### RECENT PERSONAL TRANSACTIONS (Last 10) ###")
        recent_expenses = self.get_all_expenses(limit=10)
        if recent_expenses:
            lines.append(f"{'Date':<12} {'Type':<8} {'Description':<25} {'Amount':<10}")
            lines.append("-" * 60)
            for exp in recent_expenses:
                date = exp.get('datetime', 'N/A')[5:16]
                txn_type = exp.get('type', 'OUT')
                desc = exp.get('description', 'N/A')[:25]
                amount = exp.get('amount', 0)
                sign = "+" if txn_type == "IN" else "-"
                lines.append(f"{date:<12} {txn_type:<8} {desc:<25} {sign}{amount:<9.2f}")
        else:
            lines.append("No personal transactions recorded yet.")
        
        lines.append("\n" + "=" * 60)
        lines.append("                      END OF REPORT")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    # Shift Management Methods
    
    def start_shift(self) -> Optional[int]:
        """بدء وردية جديدة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # التحقق من عدم وجود وردية نشطة بالفعل
                cursor.execute("SELECT id FROM shifts WHERE is_active = 1")
                if cursor.fetchone():
                    return None  # يوجد وردية نشطة بالفعل
                
                # إنشاء وردية جديدة
                cursor.execute("""
                    INSERT INTO shifts (start_time, is_active)
                    VALUES (?, 1)
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
                
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None
    
    def end_shift(self) -> Optional[Dict[str, Any]]:
        """إنهاء الوردية النشطة وحساب الإحصائيات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # الحصول على الوردية النشطة
                cursor.execute("SELECT * FROM shifts WHERE is_active = 1")
                shift = cursor.fetchone()
                if not shift:
                    return None
                
                shift_id = shift['id']
                
                # حساب إحصائيات الطلبات في هذه الوردية
                cursor.execute("""
                    SELECT COUNT(*) as count,
                           SUM(delivery_fee + tip_cash + tip_visa) as income
                    FROM orders
                    WHERE shift_id = ?
                """, (shift_id,))
                orders_stats = cursor.fetchone()
                
                # حساب المصاريف في هذه الوردية
                cursor.execute("""
                    SELECT SUM(amount) as total_expenses
                    FROM expenses
                    WHERE shift_id = ? AND type = 'OUT'
                """, (shift_id,))
                expenses_row = cursor.fetchone()
                
                total_orders = orders_stats['count'] or 0
                total_income = orders_stats['income'] or 0.0
                total_expenses = expenses_row['total_expenses'] or 0.0
                net_profit = total_income - total_expenses
                
                # تحديث الوردية
                cursor.execute("""
                    UPDATE shifts
                    SET end_time = ?,
                        is_active = 0,
                        total_orders = ?,
                        total_income = ?,
                        total_expenses = ?,
                        net_profit = ?
                    WHERE id = ?
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    total_orders,
                    total_income,
                    total_expenses,
                    net_profit,
                    shift_id
                ))
                
                conn.commit()
                
                # إرجاع ملخص الوردية
                return {
                    'id': shift_id,
                    'start_time': shift['start_time'],
                    'end_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'total_orders': total_orders,
                    'total_income': total_income,
                    'total_expenses': total_expenses,
                    'net_profit': net_profit
                }
        except Exception:
            return None
    
    def get_active_shift(self) -> Optional[Dict[str, Any]]:
        """الحصول على الوردية النشطة إن وجدت"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM shifts WHERE is_active = 1")
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None
    
    def get_shift_summary(self, shift_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على ملخص تفصيلي لوردية معينة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None
    
    def get_all_shifts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """الحصول على سجل الورديات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM shifts
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []