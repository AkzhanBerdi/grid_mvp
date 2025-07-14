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
