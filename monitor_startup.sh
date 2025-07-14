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
