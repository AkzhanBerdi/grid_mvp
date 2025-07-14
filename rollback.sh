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
