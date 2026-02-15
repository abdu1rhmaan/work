
import sqlite3
from pathlib import Path

db_path = Path("c:/Users/CompuMark/Desktop/talabat_driver_wallet/talabat_wallet.db")

print(f"Checking DB at: {db_path}")

try:
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check shifts table
        cursor.execute("PRAGMA table_info(shifts)")
        columns = cursor.fetchall()
        print("\nShifts Table Schema:")
        print(f"{'ID':<3} | {'Name':<20} | {'Type':<10} | {'NotNull':<8} | {'Default':<10} | {'PK':<3}")
        print("-" * 65)
        for col in columns:
            print(f"{col[0]:<3} | {col[1]:<20} | {col[2]:<10} | {col[3]:<8} | {str(col[4]):<10} | {col[5]:<3}")
            
except Exception as e:
    print(f"Error: {e}")
