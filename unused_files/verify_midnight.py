
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add src to path to import Database
sys.path.append(os.path.abspath("src"))
from talabat_wallet.database import Database

def test_smart_midnight():
    db = Database("test_midnight.db")
    
    # Simulate current time: Feb 14, 2026 23:30 (11:30 PM)
    # We can't easily mock datetime.now() without libraries, 
    # but we can test the logic if we were to pass a mock 'now'.
    # Since add_scheduled_shift uses datetime.now() internally, 
    # we'll assume the environment time is correct (it is currently 23:17).
    
    current_now = datetime.now()
    today_str = current_now.strftime("%Y-%m-%d")
    tomorrow_str = (current_now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"Current System Time: {current_now}")
    print(f"Today is: {today_str}")
    
    # Test adding a 12 AM shift for "Today" (which should be moved to Tomorrow)
    start_time = "00:00"
    end_time = "06:00"
    
    print(f"Adding shift for {today_str} {start_time}...")
    db.add_scheduled_shift(today_str, start_time, end_time)
    
    # Verify
    with sqlite3.connect("test_midnight.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shifts ORDER BY id DESC LIMIT 1")
        shift = cursor.fetchone()
        
        print(f"Stored Shift Date: {shift['shift_date']}")
        print(f"Stored Status: {shift['status']}")
        
        if shift['shift_date'] == tomorrow_str:
            print("SUCCESS: Shift was correctly moved to tomorrow! ✅")
        elif shift['shift_date'] == today_str:
            print("FAILURE: Shift stayed on today (will be marked ABSENT). ❌")
        else:
            print(f"ERROR: Unexpected date: {shift['shift_date']}")

    # Clean up
    if os.path.exists("test_midnight.db"):
        os.remove("test_midnight.db")

if __name__ == "__main__":
    test_smart_midnight()
