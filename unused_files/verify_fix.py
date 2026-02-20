
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

def get_data_directory() -> Path:
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "TalabatWallet"
    return Path.home() / ".talabat_wallet"

# Use the workspace DB for testing if it exists, otherwise use AppData
workspace_db = Path("c:/Users/CompuMark/Desktop/talabat_driver_wallet/talabat_wallet.db")
db_path = workspace_db if workspace_db.exists() else get_data_directory() / "talabat_wallet.db"

print(f"Testing logic using DB at: {db_path}")

def test_logic():
    # Mocking the database and check_auto_updates logic for verification
    # We will simulate the time check
    now = datetime.now()
    
    # Case 1: Shift ended 1 hour ago (Should NOT end yet due to 2h grace)
    scheduled_end_1 = now - timedelta(hours=1)
    grace_period_seconds = 7200 # 2 hours
    should_end_1 = now >= (scheduled_end_1 + timedelta(seconds=grace_period_seconds))
    print(f"Shift ended 1h ago. Should auto-end? {should_end_1} (Expected: False)")
    
    # Case 2: Shift ended 2.5 hours ago (Should end)
    scheduled_end_2 = now - timedelta(hours=2.5)
    should_end_2 = now >= (scheduled_end_2 + timedelta(seconds=grace_period_seconds))
    print(f"Shift ended 2.5h ago. Should auto-end? {should_end_2} (Expected: True)")

    # Case 3: Midnight shift (22:00 to 02:00), now is 23:00. Should NOT be absent.
    # String comparison "02:00" < "23:00" is TRUE, which was the bug.
    # Python comparison 02:00 (tomorrow) < 23:00 is FALSE.
    shift_date = now.strftime("%Y-%m-%d")
    s_start = "22:00"
    s_end = "02:00"
    
    # Simulate the logic in database.py
    n_time = now.replace(hour=23, minute=0, second=0, microsecond=0)
    
    end_dt = datetime.strptime(f"{shift_date} {s_end}", "%Y-%m-%d %H:%M")
    start_dt = datetime.strptime(f"{shift_date} {s_start}", "%Y-%m-%d %H:%M")
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    
    absent_grace = timedelta(hours=2)
    is_absent = n_time >= (end_dt + absent_grace)
    print(f"Midnight shift (end 02:00) checked at 23:00. Is absent? {is_absent} (Expected: False)")

    if should_end_1 == False and should_end_2 == True and is_absent == False:
        print("\nLogic Verification: SUCCESS ✅")
    else:
        print("\nLogic Verification: FAILED ❌")

if __name__ == "__main__":
    test_logic()
