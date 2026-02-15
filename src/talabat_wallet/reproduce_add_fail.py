
import sqlite3
from pathlib import Path
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))
from talabat_wallet.database import Database

def test_add():
    db = Database("talabat_wallet.db")
    print("Attempting to add shift...")
    res = db.add_scheduled_shift("2026-02-16", "10:00", "16:00")
    print(f"Result: {res}")

if __name__ == "__main__":
    test_add()
