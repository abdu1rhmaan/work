#!/bin/bash

# =========================================================
# Talabat Wallet - Termux Runner (Touch Optimization)
# =========================================================

# Clear terminal and ensure we are in the right directory
clear

# Enable SGR Mouse Tracking (supports coordinates > 223)
# \033[?1006h -> Enable SGR mode
# \033[?1003h -> Enable all mouse events (clicks + movement)
printf "\033[?1006h\033[?1003h"

echo "Starting Talabat Wallet with Touch Support..."
echo "Tip: Drag windows using the title bar."

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
