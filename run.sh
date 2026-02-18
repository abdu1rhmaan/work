#!/bin/bash

# =========================================================
# Talabat Wallet - Termux Runner (Touch Optimization)
# =========================================================

# Clear terminal and ensure we are in the right directory
clear

# Enable Mouse Tracking (Standard + Drag + SGR)
# \033[?1000h -> Basic click tracking
# \033[?1002h -> Drag tracking (crucial for window moving)
# \033[?1006h -> SGR mode (extended coordinates)
printf "\033[?1000h\033[?1002h\033[?1006h"

echo "Starting Talabat Wallet with Touch Support..."
echo "Tip: Long-press slightly on the title bar before dragging."

# Run the app
# Using -m (module mode) to support relative imports
export PYTHONPATH=$(pwd)/src

# Quick check to ensure imports work
echo "Verifying environment..."
python -c "import talabat_wallet.main; print('Import check: OK')" || { echo "Error: Import failed. Please check your setup."; exit 1; }

python -m talabat_wallet

# Reset Mouse Tracking on exit
# \033[?1003l -> Disable all mouse events
# \033[?1006l -> Disable SGR mode
printf "\033[?1003l\033[?1006l"

echo "Application closed."
