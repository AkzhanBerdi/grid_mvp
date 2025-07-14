#!/bin/bash
# deploy_step1_backup.sh - Backup and prepare for deployment

set -e  # Exit on any error

echo "🔄 STEP 1: BACKUP & PREPARATION"
echo "=" * 50

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# 1. Create timestamped backup
BACKUP_DIR="../gridtrader-backup-$(date +%Y%m%d-%H%M%S)"
print_info "Creating backup in: $BACKUP_DIR"

if cp -r . "$BACKUP_DIR"; then
    print_success "Complete backup created"
else
    print_error "Backup failed!"
    exit 1
fi

# 2. Backup database specifically
DB_BACKUP="data/gridtrader-backup-$(date +%Y%m%d-%H%M%S).db"
if [ -f "data/gridtrader.db" ]; then
    if cp "data/gridtrader.db" "$DB_BACKUP"; then
        print_success "Database backup created: $DB_BACKUP"
    else
        print_error "Database backup failed!"
        exit 1
    fi
else
    print_warning "No existing database found - fresh installation"
fi

# 3. Check current system status
print_info "Checking current system status..."

# Check if bot is running
if pgrep -f "python.*main.py\|python.*telegram_bot.py" > /dev/null; then
    print_warning "Bot appears to be running. You should stop it before proceeding."
    echo "Run: pkill -f 'python.*main.py' or use Ctrl+C in the bot terminal"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "No bot processes detected"
fi

# 4. Verify Python environment
print_info "Checking Python environment..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
    print_success "Python version: $PYTHON_VERSION"
else
    print_error "Python3 not found!"
    exit 1
fi

# 5. Check virtual environment
if [ -d "venv" ]; then
    print_success "Virtual environment exists"
    if [ -f "venv/bin/activate" ]; then
        print_success "Virtual environment appears valid"
    else
        print_warning "Virtual environment may be corrupted"
    fi
else
    print_warning "No virtual environment found"
fi

# 6. Verify configuration
print_info "Checking configuration..."

if [ -f ".env" ]; then
    print_success ".env file exists"
    
    # Check for required variables (without showing values)
    if grep -q "TELEGRAM_BOT_TOKEN=" .env; then
        print_success "Telegram bot token configured"
    else
        print_warning "Telegram bot token not found in .env"
    fi
    
    if grep -q "ENCRYPTION_KEY=" .env; then
        print_success "Encryption key configured"
    else
        print_warning "Encryption key not found in .env"
    fi
else
    print_error ".env file not found!"
    echo "Create .env file with your configuration before proceeding"
    exit 1
fi

# 7. Check disk space
DISK_USAGE=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    print_error "Disk usage is ${DISK_USAGE}% - free up space before deploying"
    exit 1
else
    print_success "Disk usage: ${DISK_USAGE}%"
fi

# 8. Test database connection
if [ -f "data/gridtrader.db" ]; then
    if python3 -c "import sqlite3; sqlite3.connect('data/gridtrader.db').execute('SELECT 1').fetchone()"; then
        print_success "Database connection test passed"
    else
        print_error "Database connection test failed"
        exit 1
    fi
fi

# 9. Create rollback script
cat > rollback.sh << 'EOF'
#!/bin/bash
# Auto-generated rollback script

echo "🔄 ROLLING BACK TO PREVIOUS VERSION"

# Stop any running processes
pkill -f "python.*main" || true

# Restore from backup
LATEST_BACKUP=$(ls -td ../gridtrader-backup-* | head -1)
echo "Restoring from: $LATEST_BACKUP"

# Restore database
LATEST_DB_BACKUP=$(ls -t data/gridtrader-backup-*.db | head -1)
if [ -f "$LATEST_DB_BACKUP" ]; then
    cp "$LATEST_DB_BACKUP" data/gridtrader.db
    echo "✅ Database restored"
fi

# Restore key files
if [ -d "$LATEST_BACKUP" ]; then
    cp "$LATEST_BACKUP/models/user.py" models/user.py 2>/dev/null || true
    cp "$LATEST_BACKUP/handlers/complete_handler.py" handlers/complete_handler.py 2>/dev/null || true
    cp "$LATEST_BACKUP/main.py" main.py 2>/dev/null || true
    echo "✅ Code files restored"
fi

echo "✅ Rollback complete. You can now start the old system."
EOF

chmod +x rollback.sh
print_success "Rollback script created: ./rollback.sh"

# 10. Summary
echo ""
echo "📊 BACKUP SUMMARY"
echo "=" * 30
echo "✅ Full backup: $BACKUP_DIR"
echo "✅ Database backup: $DB_BACKUP"
echo "✅ Rollback script: ./rollback.sh"
echo "✅ System checks passed"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Run: bash deploy_step2_migration.sh"
echo "2. Or continue with manual migration"
echo ""
print_success "Step 1 complete! Ready for database migration."
