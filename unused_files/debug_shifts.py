
import sqlite3
import sys
from pathlib import Path

def get_data_directory() -> Path:
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "TalabatWallet"
    return Path.home() / ".talabat_wallet"

workspace_db = Path("c:/Users/CompuMark/Desktop/talabat_driver_wallet/talabat_wallet.db")
db_path = workspace_db if workspace_db.exists() else get_data_directory() / "talabat_wallet.db"

print(f"Inspecting shifts at: {db_path}")

try:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get columns
        cursor.execute("PRAGMA table_info(shifts)")
        cols = cursor.fetchall()
        print("Columns:", [c[1] for c in cols])
        
        print("-" * 20)
        cursor.execute("SELECT id, shift_date, scheduled_start, scheduled_end, status FROM shifts ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(dict(row))
except Exception as e:
    print(f"Error: {e}")
