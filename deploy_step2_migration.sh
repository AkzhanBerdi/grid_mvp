#!/bin/bash
# deploy_step2_migration.sh - Database migration

set -e  # Exit on any error

echo "🗄️  STEP 2: DATABASE MIGRATION"
echo "=" * 50

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# 1. Pre-migration checks
print_info "Running pre-migration checks..."

if [ ! -f "data/gridtrader.db" ]; then
    print_error "Database file not found!"
    echo "Expected: data/gridtrader.db"
    exit 1
fi

# Create additional backup before migration
MIGRATION_BACKUP="data/gridtrader-pre-migration-$(date +%Y%m%d-%H%M%S).db"
cp "data/gridtrader.db" "$MIGRATION_BACKUP"
print_success "Pre-migration backup: $MIGRATION_BACKUP"

# 2. Check current database schema
print_info "Analyzing current database schema..."

python3 << 'EOF'
import sqlite3
import sys

try:
    conn = sqlite3.connect('data/gridtrader.db')
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    print("📊 Current user table columns:")
    for col in columns:
        print(f"  • {col}")
    
    # Check if migration needed
    new_columns = ['demo_trial_started', 'demo_trial_expires', 'real_trial_started', 'real_trial_expires']
    missing_columns = [col for col in new_columns if col not in columns]
    
    if missing_columns:
        print(f"\n🔄 Migration needed for columns: {', '.join(missing_columns)}")
        sys.exit(0)  # Migration needed
    else:
        print("\n✅ Database already up to date!")
        sys.exit(1)  # No migration needed
        
except Exception as e:
    print(f"❌ Database check failed: {e}")
    sys.exit(2)  # Error
EOF

SCHEMA_CHECK_RESULT=$?

if [ $SCHEMA_CHECK_RESULT -eq 1 ]; then
    print_success "Database already migrated!"
    echo "🎯 Skipping to next step..."
    echo "Run: bash deploy_step3_code_update.sh"
    exit 0
elif [ $SCHEMA_CHECK_RESULT -eq 2 ]; then
    print_error "Database check failed!"
    exit 1
fi

# 3. Run migration
print_info "Starting database migration..."

# Create the migration script if it doesn't exist
if [ ! -f "dual_trial_migration.py" ]; then
    print_warning "Migration script not found. Creating it..."
    
    # You would copy the migration script content here
    # For now, we'll assume it exists
    print_error "Please ensure dual_trial_migration.py exists"
    exit 1
fi

# Run the migration
print_info "Executing migration script..."

if python3 dual_trial_migration.py; then
    print_success "Migration script completed successfully"
else
    print_error "Migration script failed!"
    echo "Restoring database from backup..."
    cp "$MIGRATION_BACKUP" "data/gridtrader.db"
    exit 1
fi

# 4. Verify migration
print_info "Verifying migration results..."

python3 << 'EOF'
import sqlite3
import sys

try:
    conn = sqlite3.connect('data/gridtrader.db')
    
    # Check new columns exist
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    required_columns = ['demo_trial_started', 'demo_trial_expires', 'real_trial_started', 'real_trial_expires']
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ Migration incomplete. Missing: {', '.join(missing_columns)}")
        sys.exit(1)
    
    print("✅ All required columns present")
    
    # Check subscription statuses
    cursor = conn.execute("SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status")
    status_counts = cursor.fetchall()
    
    print("📊 User subscription status distribution:")
    total_users = 0
    for status, count in status_counts:
        print(f"  • {status}: {count} users")
        total_users += count
    
    print(f"📈 Total users: {total_users}")
    
    # Test creating a user with new model
    from datetime import datetime, timedelta
    
    test_id = 999999998  # Different from the test user in migration
    
    # Clean up any existing test user
    conn.execute("DELETE FROM users WHERE telegram_id = ?", (test_id,))
    
    # Insert test user with new fields
    now = datetime.now()
    demo_expires = now + timedelta(days=7)
    
    conn.execute("""
        INSERT INTO users (
            telegram_id, username, first_name, subscription_status,
            demo_trial_started, demo_trial_expires, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_id, "migration_test", "Migration Test", "demo_trial",
        now.isoformat(), demo_expires.isoformat(),
        now.isoformat(), now.isoformat()
    ))
    
    # Verify the insert worked
    cursor = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (test_id,))
    test_user = cursor.fetchone()
    
    if test_user:
        print("✅ New schema test insertion successful")
        # Clean up test user
        conn.execute("DELETE FROM users WHERE telegram_id = ?", (test_id,))
        conn.commit()
    else:
        print("❌ New schema test insertion failed")
        sys.exit(1)
    
    print("✅ Migration verification complete")
    
except Exception as e:
    print(f"❌ Migration verification failed: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    print_error "Migration verification failed!"
    echo "Restoring database from backup..."
    cp "$MIGRATION_BACKUP" "data/gridtrader.db"
    exit 1
fi

# 5. Test database integrity
print_info "Testing database integrity..."

if python3 -c "
import sqlite3
conn = sqlite3.connect('data/gridtrader.db')
result = conn.execute('PRAGMA integrity_check').fetchone()[0]
print(f'Database integrity: {result}')
assert result == 'ok', f'Database integrity check failed: {result}'
"; then
    print_success "Database integrity check passed"
else
    print_error "Database integrity check failed!"
    exit 1
fi

# 6. Create migration summary
echo ""
echo "📊 MIGRATION SUMMARY"
echo "=" * 30

python3 << 'EOF'
import sqlite3

conn = sqlite3.connect('data/gridtrader.db')

# Count users by subscription status
cursor = conn.execute("SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status")
print("User Distribution:")
for status, count in cursor.fetchall():
    print(f"  📊 {status}: {count} users")

# Check for users ready for demo trial
cursor = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_status = 'none'")
none_count = cursor.fetchone()[0]
print(f"  🎮 Ready for demo trial: {none_count} users")

# Check existing trials
cursor = conn.execute("SELECT COUNT(*) FROM users WHERE demo_trial_expires IS NOT NULL")
demo_trials = cursor.fetchone()[0]
print(f"  🎮 With demo trial data: {demo_trials} users")

cursor = conn.execute("SELECT COUNT(*) FROM users WHERE real_trial_expires IS NOT NULL")
real_trials = cursor.fetchone()[0]
print(f"  🟢 With real trial data: {real_trials} users")

conn.close()
EOF

echo ""
echo "✅ Database migration completed successfully!"
echo ""
echo "📁 Backup files created:"
echo "  • Pre-migration: $MIGRATION_BACKUP"
echo "  • Full backup available in ../gridtrader-backup-*"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Run: bash deploy_step3_code_update.sh"
echo "2. Or manually update your code files"
echo ""
print_success "Step 2 complete! Database ready for dual trial system."
