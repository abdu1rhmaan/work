
import sqlite3
from pathlib import Path

db_path = Path("talabat_wallet.db")

def scan_all_shifts():
    if not db_path.exists():
        print("DB not found")
        return

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM shifts ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        
        if not rows:
            print("No shifts found.")
            return

        cols = rows[0].keys()
        header = " | ".join(cols)
        print(header)
        print("-" * len(header))
        for row in rows:
            print(" | ".join(str(row[c]) for c in cols))

if __name__ == "__main__":
    scan_all_shifts()
