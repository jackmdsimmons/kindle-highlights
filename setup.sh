#!/bin/bash
echo "=== Kindle Highlights Setup ==="
echo

# Check for Python
if ! command -v python3 &>/dev/null; then
    echo "Python not found. Please install it from https://www.python.org/downloads/"
    exit 1
else
    echo "Python found: $(python3 --version)"
fi

echo
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
fi

echo
echo "Installing Playwright browser..."
python3 -m playwright install chromium
if [ $? -ne 0 ]; then
    echo "Failed to install Playwright browser."
    exit 1
fi

echo
echo "Setup complete!"
echo
read -p "Run the script now? (y/n): " run
if [[ "$run" == "y" || "$run" == "Y" ]]; then
    python3 kindle_to_csv.py
fi
