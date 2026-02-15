
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath("src"))
from talabat_wallet.database import Database

def test_overlaps():
    db_file = "test_overlap.db"
    if os.path.exists(db_file): os.remove(db_file)
    db = Database(db_file)
    
    date_str = "2026-03-01"
    
    print("Step 1: Adding base shift (10:00 - 14:00)")
    success, _, _ = db.add_scheduled_shift(date_str, "10:00", "14:00")
    print(f"Result: {success}")
    
    print("\nStep 2: Adding exact duplicate (10:00 - 14:00)")
    success, _, err = db.add_scheduled_shift(date_str, "10:00", "14:00")
    print(f"Result: {success}, Error: {err}")
    
    print("\nStep 3: Adding partial overlap (12:00 - 16:00)")
    success, _, err = db.add_scheduled_shift(date_str, "12:00", "16:00")
    print(f"Result: {success}, Error: {err}")
    
    print("\nStep 4: Adding non-overlap (14:00 - 18:00) - Border cases")
    success, _, err = db.add_scheduled_shift(date_str, "14:00", "18:00")
    print(f"Result: {success}, Error: {err}")
    
    print("\nStep 5: Midnight crossing overlap check")
    print("Adding crossing shift (Feb 28, 22:00 - 02:00)")
    db.add_scheduled_shift("2026-02-28", "22:00", "02:00")
    print("Checking overlap on March 01, 01:00 - 03:00")
    success, _, err = db.add_scheduled_shift("2026-03-01", "01:00", "03:00")
    print(f"Result: {success}, Error: {err}")

    if os.path.exists(db_file): os.remove(db_file)

if __name__ == "__main__":
    test_overlaps()
