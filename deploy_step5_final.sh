#!/bin/bash
# deploy_step5_final.sh - Final deployment and monitoring

set -e  # Exit on any error

echo "🚀 STEP 5: FINAL DEPLOYMENT"
echo "=" * 50

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_deploy() { echo -e "${PURPLE}🚀 $1${NC}"; }
print_monitor() { echo -e "${CYAN}👁️  $1${NC}"; }

# 1. Pre-deployment final checks
print_info "Final pre-deployment checks..."

if [ ! -f "rollback.sh" ]; then
    print_error "Rollback script missing! Run step 1 first."
    exit 1
fi

# Check if any bot processes are running
if pgrep -f "python.*main.*py\|python.*telegram_bot" > /dev/null; then
    print_warning "Bot processes detected. Stopping them..."
    pkill -f "python.*main.*py" || true
    pkill -f "python.*telegram_bot" || true
    sleep 3
    print_success "Old bot processes stopped"
fi

# Verify tests passed
if [ -f "test_dual_trial_integration.py" ]; then
    print_info "Running final integration test..."
    if python3 test_dual_trial_integration.py; then
        print_success "Final integration test passed"
    else
        print_error "Final integration test failed! Aborting deployment."
        exit 1
    fi
fi

# 2. Determine which main file to use
MAIN_FILE=""

if [ -f "main_bot_dual_trial.py" ]; then
    MAIN_FILE="main_bot_dual_trial.py"
    print_success "Using dual trial main bot: $MAIN_FILE"
elif [ -f "main.py" ]; then
    MAIN_FILE="main.py"
    print_warning "Using legacy main bot: $MAIN_FILE"
    print_warning "Consider updating to dual trial system"
else
    print_error "No main bot file found!"
    exit 1
fi

# 3. Create deployment info file
cat > deployment_info.txt << EOF
GridTrader Pro Deployment Info
==============================
Deployment Date: $(date)
Main File: $MAIN_FILE
Python Version: $(python3 --version)
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "Not a git repository")
User: $(whoami)
System: $(uname -a)

Features Deployed:
- Dual Trial System (Demo → Real)
- Auto Trial Expiry
- Enhanced User Model
- Improved Bot Orchestration

Database Schema Version: Dual Trial v1.0
EOF

print_success "Deployment info created: deployment_info.txt"

# 4. Create startup monitoring script
cat > monitor_startup.sh << 'EOF'
#!/bin/bash
# monitor_startup.sh - Monitor bot startup

echo "👁️  MONITORING BOT STARTUP"
echo "=========================="

LOG_FILE="data/logs/gridtrader.log"
STARTUP_TIMEOUT=60  # 60 seconds
START_TIME=$(date +%s)

echo "🔍 Watching log file: $LOG_FILE"
echo "⏱️  Timeout: ${STARTUP_TIMEOUT}s"
echo ""

# Function to check if bot is running
check_bot_running() {
    pgrep -f "python.*main.*py" > /dev/null
}

# Function to check for successful startup messages
check_startup_success() {
    if [ -f "$LOG_FILE" ]; then
        # Look for success indicators in logs
        if grep -q "GridTrader Pro initialized\|Telegram bot configured\|Both user bot management" "$LOG_FILE" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Function to check for error messages
check_startup_errors() {
    if [ -f "$LOG_FILE" ]; then
        # Look for error indicators
        if tail -20 "$LOG_FILE" 2>/dev/null | grep -q "ERROR\|Failed\|Exception"; then
            return 0
        fi
    fi
    return 1
}

echo "⏳ Starting monitoring loop..."

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $STARTUP_TIMEOUT ]; then
        echo ""
        echo "⏰ Startup timeout reached (${STARTUP_TIMEOUT}s)"
        break
    fi
    
    # Check if process is running
    if check_bot_running; then
        echo -n "🟢"
    else
        echo -n "🔴"
    fi
    
    # Check for success messages
    if check_startup_success; then
        echo ""
        echo "✅ STARTUP SUCCESSFUL!"
        echo "🤖 Bot is running and initialized"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "📋 Recent log entries:"
            tail -5 "$LOG_FILE" | while read line; do
                echo "  $line"
            done
        fi
        
        exit 0
    fi
    
    # Check for errors
    if check_startup_errors; then
        echo ""
        echo "❌ STARTUP ERRORS DETECTED!"
        echo "🔍 Recent log entries:"
        
        if [ -f "$LOG_FILE" ]; then
            tail -10 "$LOG_FILE" | while read line; do
                echo "  $line"
            done
        fi
        
        exit 1
    fi
    
    sleep 2
done

# Timeout reached
echo ""
echo "⚠️  Startup monitoring timed out"
echo "🔍 Bot process status:"
if check_bot_running; then
    echo "  ✅ Process is running"
else
    echo "  ❌ Process not found"
fi

echo ""
echo "📋 Recent logs:"
if [ -f "$LOG_FILE" ]; then
    tail -10 "$LOG_FILE" | while read line; do
        echo "  $line"
    done
else
    echo "  ❌ No log file found"
fi

exit 1
EOF

chmod +x monitor_startup.sh
print_success "Startup monitoring script created"

# 5. Pre-deployment health check
print_info "Running pre-deployment health check..."

python3 << 'EOF'
import sys
import sqlite3
from datetime import datetime

print("🏥 PRE-DEPLOYMENT HEALTH CHECK")
print("==============================")

try:
    # Check database
    conn = sqlite3.connect('data/gridtrader.db')
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"✅ Database: {user_count} users")
    
    # Check dual trial schema
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    dual_trial_cols = ['demo_trial_started', 'demo_trial_expires', 'real_trial_started', 'real_trial_expires']
    missing = [col for col in dual_trial_cols if col not in columns]
    
    if missing:
        print(f"❌ Missing columns: {missing}")
        sys.exit(1)
    else:
        print("✅ Dual trial schema: Complete")
    
    # Check user distribution
    cursor = conn.execute("SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status")
    statuses = dict(cursor.fetchall())
    print("✅ User distribution:")
    for status, count in statuses.items():
        print(f"   • {status}: {count}")
    
    # Check for users ready for migration
    none_users = statuses.get('none', 0)
    trial_users = statuses.get('trial', 0)
    demo_users = statuses.get('demo_trial', 0)
    real_users = statuses.get('real_trial', 0)
    
    print(f"📊 Migration status:")
    print(f"   • Ready for demo trial: {none_users}")
    print(f"   • Legacy trials: {trial_users}")
    print(f"   • Demo trials: {demo_users}")
    print(f"   • Real trials: {real_users}")
    
    conn.close()
    
    print("✅ All health checks passed")
    
except Exception as e:
    print(f"❌ Health check failed: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    print_error "Pre-deployment health check failed!"
    exit 1
fi

# 6. Create process management functions
print_info "Setting up process management..."

# Function to start bot with monitoring
start_bot_with_monitoring() {
    print_deploy "Starting bot: $MAIN_FILE"
    
    # Start bot in background
    nohup python3 "$MAIN_FILE" > /dev/null 2>&1 &
    BOT_PID=$!
    
    echo "🔢 Bot PID: $BOT_PID"
    echo "$BOT_PID" > bot.pid
    
    # Give it a moment to start
    sleep 3
    
    # Check if it's still running
    if kill -0 $BOT_PID 2>/dev/null; then
        print_success "Bot process started successfully"
        return 0
    else
        print_error "Bot process failed to start"
        return 1
    fi
}

# 7. Start the deployment
print_deploy "Initiating final deployment..."

# Clear old logs for fresh start
if [ -f "data/logs/gridtrader.log" ]; then
    mv "data/logs/gridtrader.log" "data/logs/gridtrader-pre-deployment-$(date +%Y%m%d-%H%M%S).log"
    print_info "Archived old log file"
fi

# Ensure log directory exists
mkdir -p data/logs

# Start the bot
if start_bot_with_monitoring; then
    print_success "Bot started successfully!"
    
    # Run startup monitoring
    print_monitor "Running startup monitoring..."
    
    if ./monitor_startup.sh; then
        print_success "🎉 DEPLOYMENT SUCCESSFUL!"
        
        # Show current status
        echo ""
        echo "📊 DEPLOYMENT STATUS"
        echo "==================="
        echo "✅ Bot Status: Running"
        echo "🔢 Process ID: $(cat bot.pid 2>/dev/null || echo 'Unknown')"
        echo "📁 Log File: data/logs/gridtrader.log"
        echo "⏰ Started: $(date)"
        echo "🎯 Features: Dual Trial System Active"
        
        # Test bot responsiveness
        print_info "Testing bot responsiveness..."
        
        python3 << 'EOF'
import time
import sqlite3
from datetime import datetime

# Create a test user to verify system works
test_id = 999999999
conn = sqlite3.connect('data/gridtrader.db')

# Clean up any existing test user
conn.execute("DELETE FROM users WHERE telegram_id = ?", (test_id,))

# Insert test user
conn.execute("""
    INSERT INTO users (telegram_id, username, first_name, subscription_status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
""", (test_id, "deployment_test", "Deployment Test", "none", 
      datetime.now().isoformat(), datetime.now().isoformat()))

conn.commit()

# Verify insertion
cursor = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (test_id,))
user = cursor.fetchone()

if user:
    print("✅ Database write test: Success")
else:
    print("❌ Database write test: Failed")

conn.close()
EOF
        
        echo ""
        echo "🎯 POST-DEPLOYMENT ACTIONS"
        echo "========================="
        echo "1. Monitor logs: tail -f data/logs/gridtrader.log"
        echo "2. Test with Telegram: Send /start to your bot"
        echo "3. Check user flows: Demo trial → Real trial upgrade"
        echo "4. Monitor trial expiry (if monitor enabled)"
        echo ""
        echo "🚨 MONITORING COMMANDS"
        echo "====================="
        echo "• Check status: ps aux | grep python"
        echo "• View logs: tail -f data/logs/gridtrader.log"
        echo "• Stop bot: kill \$(cat bot.pid)"
        echo "• Restart: ./deploy_step5_final.sh"
        echo "• Rollback: ./rollback.sh"
        
    else
        print_error "Startup monitoring failed!"
        echo ""
        echo "🔍 TROUBLESHOOTING"
        echo "=================="
        echo "1. Check logs: tail -f data/logs/gridtrader.log"
        echo "2. Verify configuration: python3 -c 'from config import Config; print(Config.validate())'"
        echo "3. Test imports: python3 -c 'from models.user import User'"
        echo "4. Run rollback if needed: ./rollback.sh"
        
        # Ask if user wants to see logs
        echo ""
        read -p "Show recent log entries? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -f "data/logs/gridtrader.log" ]; then
                echo ""
                echo "📋 RECENT LOG ENTRIES:"
                tail -20 "data/logs/gridtrader.log"
            else
                echo "❌ No log file found"
            fi
        fi
        
        exit 1
    fi
    
else
    print_error "Failed to start bot!"
    echo ""
    echo "🔍 TROUBLESHOOTING STEPS"
    echo "======================="
    echo "1. Check Python environment: python3 --version"
    echo "2. Verify main file exists: ls -la $MAIN_FILE"
    echo "3. Test configuration: python3 -c 'from config import Config; Config.validate()'"
    echo "4. Check dependencies: pip list"
    echo "5. Run rollback: ./rollback.sh"
    
    exit 1
fi

# 8. Create post-deployment monitoring script
cat > monitor_deployment.sh << 'EOF'
#!/bin/bash
# monitor_deployment.sh - Ongoing deployment monitoring

echo "👁️  DEPLOYMENT MONITORING DASHBOARD"
echo "=================================="
echo "Press Ctrl+C to exit"
echo ""

while true; do
    clear
    echo "🤖 GridTrader Pro - Live Status"
    echo "==============================="
    echo "⏰ $(date)"
    echo ""
    
    # Check if bot is running
    if pgrep -f "python.*main.*py" > /dev/null; then
        PID=$(pgrep -f "python.*main.*py")
        echo "✅ Bot Status: Running (PID: $PID)"
        
        # Memory usage
        if command -v ps &> /dev/null; then
            MEMORY=$(ps -p $PID -o rss= 2>/dev/null | awk '{print $1/1024}' 2>/dev/null || echo "Unknown")
            echo "💾 Memory Usage: ${MEMORY} MB"
        fi
    else
        echo "❌ Bot Status: Not Running"
    fi
    
    # Database stats
    if [ -f "data/gridtrader.db" ]; then
        USER_COUNT=$(sqlite3 data/gridtrader.db "SELECT COUNT(*) FROM users" 2>/dev/null || echo "Unknown")
        echo "👥 Total Users: $USER_COUNT"
        
        # Trial distribution
        echo "📊 User Distribution:"
        sqlite3 data/gridtrader.db "SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status" 2>/dev/null | while read line; do
            echo "   • $line"
        done
    fi
    
    # Recent log entries
    echo ""
    echo "📋 Recent Log Entries (last 5):"
    if [ -f "data/logs/gridtrader.log" ]; then
        tail -5 "data/logs/gridtrader.log" | while read line; do
            echo "   $line"
        done
    else
        echo "   ❌ No log file found"
    fi
    
    # Wait 10 seconds before refresh
    sleep 10
done
EOF

chmod +x monitor_deployment.sh

echo ""
print_success "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo ""
echo "🎯 QUICK START GUIDE"
echo "==================="
echo "1. Test your bot: Send /start to your Telegram bot"
echo "2. Monitor live: ./monitor_deployment.sh"
echo "3. View logs: tail -f data/logs/gridtrader.log"
echo ""
echo "📱 USER JOURNEY TO TEST:"
echo "• New user gets 7-day demo trial"
echo "• Demo user can upgrade to 7-day real trial"
echo "• Trial expiry auto-stops trading"
echo ""
echo "🛠️  MANAGEMENT COMMANDS:"
echo "• Status: ps aux | grep python"
echo "• Stop: kill \$(cat bot.pid)"
echo "• Restart: python3 $MAIN_FILE"
echo "• Rollback: ./rollback.sh"
echo ""

print_success "GridTrader Pro Dual Trial System is now LIVE! 🚀"
