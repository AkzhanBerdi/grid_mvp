# startup.sh
#!/bin/bash

echo "🚀 Starting GridTrader Pro Client Service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please copy .env.example to .env and configure it."
    echo "Example: cp .env.example .env"
    exit 1
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p data/logs data/backups

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_warning "Python 3.11+ recommended. Current version: $python_version"
fi

# Setup virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
print_status "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    exit 1
fi

# Initialize database
print_status "Initializing database..."
python database/db_setup.py --init

if [ $? -ne 0 ]; then
    print_error "Database initialization failed"
    exit 1
fi

# Validate configuration
print_status "Validating configuration..."
python -c "from config import Config; assert Config.validate(), 'Invalid configuration'"

if [ $? -ne 0 ]; then
    print_error "Configuration validation failed. Check your .env file."
    exit 1
fi

# Show database stats
print_status "Database statistics..."
python database/db_setup.py --stats

# Start the main application
print_status "Starting GridTrader Pro Service..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 GridTrader Pro - Client Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 Telegram Bot: Starting..."
echo "🗄️  Database: Initialized"
echo "🔒 Security: Encrypted API storage"
echo "📊 Grid Trading: Professional service"
echo "📁 Logs: data/logs/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the application with error handling
python main.py

# Capture exit code
exit_code=$?

if [ $exit_code -ne 0 ]; then
    print_error "Service exited with code $exit_code"
    print_status "Check logs: tail -f data/logs/gridtrader_service.log"
else
    print_status "Service stopped gracefully"
fi

exit $exit_code
