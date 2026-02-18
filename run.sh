#!/bin/bash

# =========================================================
# Talabat Wallet - Termux Runner (Touch/Mouse Optimization)
# =========================================================

# Clear terminal and ensure we are in the right directory
clear

# 1. MOUSE VERIFICATION TEST
echo "---------------------------------------------------------"
echo "MOUSE VERIFICATION TEST"
echo "Please TAP or CLICK anywhere on the screen now."
echo "(Checks if Termux is passing touch events to the app)"
echo "---------------------------------------------------------"

python -c "
import sys, tty, termios
from select import select

def test_mouse():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Enable Mouse Tracking (SGR + Click)
        sys.stdout.write('\033[?1000h\033[?1006h')
        sys.stdout.flush()
        
        rlist, _, _ = select([sys.stdin], [], [], 5)
        if rlist:
            data = sys.stdin.read(10)
            if '\033[' in data:
                print('\r\n[MATCH] Mouse event detected! Proceeding...\r\n')
                return True
        
        print('\r\n[FAIL] No mouse event detected within 5 seconds.\r\n')
        return False
    finally:
        sys.stdout.write('\033[?1000l\033[?1006l')
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if not test_mouse():
    print('WARNING: Mouse/Touch events might be BLOCKED by Termux.')
    print('FIX: Long-press screen -> More -> Enable Mouse Mode.')
    print('---------------------------------------------------------')
    input('Press Enter to start anyway, or Ctrl+C to cancel...')
" || true

# 2. RUNTIME CONFIGURATION
export PYTHONPATH=$(pwd)/src

# Clear old debug logs
rm -f debug_touch.log

# Enable Mouse Tracking (Standard + Drag + SGR)
# 1002h -> Optimized for Dragging operations
printf "\033[?1000h\033[?1002h\033[?1006h"

echo "Starting Talabat Wallet..."
echo "---------------------------------------------------------"
echo "CRITICAL TOUCH TIPS (IMPORTANT):"
echo "1. DISABLE TEXT SELECTION: Long-press screen -> More -> Selection"
echo "   Uncheck 'Use long press for selection' if possible."
echo "2. USE MOUSE MODE: Long-press screen -> More -> Enable Mouse Mode."
echo "3. DRAGGING: Tap the Title Bar and move your finger QUICKLY."
echo "4. LOGS: Check 'debug_touch.log' if it doesn't move."
echo "---------------------------------------------------------"

# 3. LAUNCH APP
python -m talabat_wallet

# 4. CLEANUP
# Reset Mouse Tracking on exit
printf "\033[?1000l\033[?1002l\033[?1006l"

echo "Application closed."
