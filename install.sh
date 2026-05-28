#!/bin/bash
# Navigate to the bot directory
cd "$(dirname "$0")/boss-hiring-bot"

# Check if virtual environment exists, if not create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and install requirements
echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation complete!"
