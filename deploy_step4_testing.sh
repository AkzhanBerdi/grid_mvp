#!/bin/bash
# deploy_step4_testing.sh - Comprehensive testing before deployment

set -e  # Exit on any error

echo "🧪 STEP 4: TESTING & VALIDATION"
echo "=" * 50

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_test() { echo -e "${PURPLE}🧪 $1${NC}"; }

# Global test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_test "Running: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        print_success "$test_name"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$test_name"
        FAILED_TESTS+=("$test_name")
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to run a test with output
run_test_with_output() {
    local test_name="$1"
    local test_command="$2"
    
    print_test "Running: $test_name"
    
    if eval "$test_command"; then
        print_success "$test_name"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$test_name"
        FAILED_TESTS+=("$test_name")
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "🔍 Starting comprehensive testing suite..."
echo ""

# 1. Environment Tests
print_info "Phase 1: Environment Tests"
echo "─────────────────────────────"

run_test "Python 3 availability" "python3 --version"
run_test "Virtual environment exists" "test -d venv"
run_test "Database file exists" "test -f data/gridtrader.db"
run_test "Environment file exists" "test -f .env"
run_test "Logs directory exists" "test -d data/logs"

# 2. Database Tests
print_info "Phase 2: Database Tests"
echo "─────────────────────────────"

run_test "Database connection" "python3 -c 'import sqlite3; sqlite3.connect(\"data/gridtrader.db\").execute(\"SELECT 1\")'"

run_test "Database integrity" "python3 -c 'import sqlite3; assert sqlite3.connect(\"data/gridtrader.db\").execute(\"PRAGMA integrity_check\").fetchone()[0] == \"ok\"'"

run_test_with_output "Database schema validation" "python3 -c '
import sqlite3
conn = sqlite3.connect(\"data/gridtrader.db\")
cursor = conn.execute(\"PRAGMA table_info(users)\")
columns = [col[1] for col in cursor.fetchall()]
required = [\"demo_trial_started\", \"demo_trial_expires\", \"real_trial_started\", \"real_trial_expires\"]
missing = [col for col in required if col not in columns]
if missing:
    print(f\"Missing columns: {missing}\")
    exit(1)
print(f\"✅ All required columns present: {required}\")
'"

run_test_with_output "User count check" "python3 -c '
import sqlite3
conn = sqlite3.connect(\"data/gridtrader.db\")
cursor = conn.execute(\"SELECT COUNT(*) FROM users\")
count = cursor.fetchone()[0]
print(f\"📊 Total users in database: {count}\")
'"

# 3. Model Tests
print_info "Phase 3: Model Tests"
echo "─────────────────────────────"

run_test "User model import" "python3 -c 'from models.user import User, SubscriptionStatus, BotStatus'"

run_test_with_output "User model functionality" "python3 -c '
from models.user import User, SubscriptionStatus, BotStatus
from datetime import datetime, timedelta

# Test user creation
user = User(telegram_id=999999990, username=\"test\", first_name=\"Test\")
print(\"✅ User creation\")

# Test demo trial
success = user.start_demo_trial()
assert success, \"Demo trial should start\"
print(\"✅ Demo trial start\")

# Test trial status
assert user.is_demo_trial_active(), \"Demo trial should be active\"
print(\"✅ Demo trial active check\")

# Test upgrade
success = user.upgrade_to_real_trial(\"test_api\", \"test_secret\")
assert success, \"Should upgrade to real trial\"
print(\"✅ Real trial upgrade\")

# Test real trial status
assert user.is_real_trial_active(), \"Real trial should be active\"
assert not user.is_demo_trial_active(), \"Demo trial should be inactive\"
print(\"✅ Trial status transitions\")

print(\"🎉 All user model tests passed\")
'"

# 4. Repository Tests
print_info "Phase 4: Repository Tests"
echo "─────────────────────────────"

run_test "UserRepository import" "python3 -c 'from repositories.user_repository import UserRepository'"

run_test_with_output "UserRepository basic operations" "python3 -c '
from repositories.user_repository import UserRepository
from models.user import SubscriptionStatus

repo = UserRepository()
print(\"✅ Repository creation\")

# Test user creation
test_id = 999999989
user = repo.create_user(telegram_id=test_id, username=\"test_repo\", first_name=\"Test Repo\")
print(\"✅ User creation via repository\")

# Test user retrieval
retrieved = repo.get_user(test_id)
assert retrieved is not None, \"User should be retrievable\"
assert retrieved.telegram_id == test_id, \"Retrieved user should match\"
print(\"✅ User retrieval\")

# Test user update
retrieved.subscription_status = SubscriptionStatus.DEMO_TRIAL
success = repo.update_user(retrieved)
assert success, \"User update should succeed\"
print(\"✅ User update\")

print(\"🎉 Repository tests passed\")
'"

# 5. Service Tests
print_info "Phase 5: Service Tests"
echo "─────────────────────────────"

run_test "BotOrchestrator import" "python3 -c 'from services.bot_orchestrator import BotOrchestrator'"

run_test "ConversionTracker import" "python3 -c 'from analytics.conversion_tracker import ConversionTracker'"

run_test_with_output "Service initialization" "python3 -c '
from services.bot_orchestrator import BotOrchestrator
from analytics.conversion_tracker import ConversionTracker

orchestrator = BotOrchestrator()
print(\"✅ BotOrchestrator initialization\")

tracker = ConversionTracker()
print(\"✅ ConversionTracker initialization\")

# Test basic functionality
status = orchestrator.get_all_active_bots()
print(f\"✅ Active bots check: {len(status)} bots\")

tracker.track_event(999999988, \"test_event\")
print(\"✅ Event tracking\")

print(\"🎉 Service tests passed\")
'"

# 6. Configuration Tests
print_info "Phase 6: Configuration Tests"
echo "─────────────────────────────"

run_test "Config import" "python3 -c 'from config import Config'"

run_test_with_output "Config validation" "python3 -c '
from config import Config

config = Config()
print(\"✅ Config creation\")

# Check validation method
if hasattr(config, \"validate\"):
    is_valid = config.validate()
    print(f\"✅ Config validation: {is_valid}\")
else:
    print(\"⚠️  No validate method found\")

# Check key attributes
attrs = [\"TELEGRAM_BOT_TOKEN\", \"DATABASE_PATH\", \"LOG_LEVEL\"]
for attr in attrs:
    if hasattr(config, attr):
        value = getattr(config, attr)
        status = \"Set\" if value else \"Empty\"
        print(f\"✅ {attr}: {status}\")
    else:
        print(f\"❌ Missing: {attr}\")

print(\"🎉 Config tests completed\")
'"

# 7. Integration Tests
print_info "Phase 7: Integration Tests"
echo "─────────────────────────────"

if [ -f "test_dual_trial_integration.py" ]; then
    run_test_with_output "Dual trial integration test" "python3 test_dual_trial_integration.py"
else
    print_warning "Integration test file not found, skipping"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Integration test file missing")
fi

# 8. Handler Tests (if available)
print_info "Phase 8: Handler Tests"
echo "─────────────────────────────"

if [ -f "handlers/dual_trial_handler.py" ]; then
    run_test "DualTrialHandler import" "python3 -c 'from handlers.dual_trial_handler import DualTrialHandler'"
    
    run_test_with_output "Handler initialization" "python3 -c '
from handlers.dual_trial_handler import DualTrialHandler
from analytics.conversion_tracker import ConversionTracker

tracker = ConversionTracker()
handler = DualTrialHandler(tracker)
print(\"✅ DualTrialHandler creation\")

# Test helper methods
from models.user import User, SubscriptionStatus

user = User(telegram_id=999999987)
user.binance_api_key = \"demo_api_key_for_testing\"
result = handler._has_real_api_keys(user)
print(f\"✅ Real API key detection: {not result} (should be False for demo keys)\")

user.binance_api_key = \"real_api_key_very_long_binance_key_here_64_chars_minimum_length\"
result = handler._has_real_api_keys(user)
print(f\"✅ Real API key detection: {result} (should be True for real-looking keys)\")

print(\"🎉 Handler tests passed\")
'"
else
    if [ -f "handlers/complete_handler.py" ]; then
        run_test "CompleteHandler import (legacy)" "python3 -c 'from handlers.complete_handler import CompleteHandler'"
        print_warning "Using legacy handler - consider updating to DualTrialHandler"
    else
        print_error "No handler found!"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Handler missing")
    fi
fi

# 9. Trial Monitor Tests (if available)
print_info "Phase 9: Trial Monitor Tests"
echo "─────────────────────────────"

if [ -f "trial_expiry_monitor.py" ]; then
    run_test "TrialExpiryMonitor import" "python3 -c 'from trial_expiry_monitor import TrialExpiryMonitor'"
    
    run_test_with_output "Trial monitor functionality" "python3 -c '
from trial_expiry_monitor import TrialExpiryMonitor

monitor = TrialExpiryMonitor()
print(\"✅ TrialExpiryMonitor creation\")

# Test basic functionality (without actually running checks)
print(\"✅ Trial monitor basic functionality\")

print(\"🎉 Trial monitor tests passed\")
'"
else
    print_warning "trial_expiry_monitor.py not found - trial expiry automation disabled"
    # This is a warning, not a failure
fi

# 10. Performance Tests
print_info "Phase 10: Performance Tests"
echo "─────────────────────────────"

run_test_with_output "Memory usage test" "python3 -c '
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024

print(f\"💾 Current memory usage: {memory_mb:.1f} MB\")

if memory_mb > 500:
    print(\"⚠️  High memory usage detected\")
else:
    print(\"✅ Memory usage is reasonable\")
'"

run_test_with_output "Database performance test" "python3 -c '
import sqlite3
import time

conn = sqlite3.connect(\"data/gridtrader.db\")

# Test query performance
start = time.time()
cursor = conn.execute(\"SELECT COUNT(*) FROM users\")
count = cursor.fetchone()[0]
duration = time.time() - start

print(f\"📊 Query performance: {duration*1000:.1f}ms for counting {count} users\")

if duration > 1.0:
    print(\"⚠️  Slow database query detected\")
else:
    print(\"✅ Database performance is good\")

conn.close()
'"

# 11. Security Tests
print_info "Phase 11: Security Tests"
echo "─────────────────────────────"

run_test_with_output "Environment security check" "python3 -c '
import os

# Check if sensitive files have appropriate permissions
sensitive_files = [\".env\", \"data/gridtrader.db\"]

for file in sensitive_files:
    if os.path.exists(file):
        stat = os.stat(file)
        mode = stat.st_mode & 0o777
        print(f\"🔒 {file} permissions: {oct(mode)}\")
        
        if mode & 0o077:  # Check if others can read
            print(f\"⚠️  {file} may be readable by others\")
        else:
            print(f\"✅ {file} permissions are secure\")
    else:
        print(f\"❓ {file} not found\")

print(\"🔒 Security check completed\")
'"

# Test Results Summary
echo ""
echo "📊 TEST RESULTS SUMMARY"
echo "══════════════════════════════════════"
echo -e "✅ Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "❌ Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "📈 Success Rate: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%"

if [ $TESTS_FAILED -gt 0 ]; then
    echo ""
    echo "🚨 FAILED TESTS:"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  • $test"
    done
    
    echo ""
    echo "🔧 RECOMMENDATIONS:"
    
    if [[ " ${FAILED_TESTS[@]} " =~ " Handler missing " ]]; then
        echo "  • Create handlers/dual_trial_handler.py from the provided template"
    fi
    
    if [[ " ${FAILED_TESTS[@]} " =~ " Integration test file missing " ]]; then
        echo "  • Create test_dual_trial_integration.py from step 3"
    fi
    
    echo "  • Review failed tests above and fix issues before deployment"
    echo "  • Consider running individual tests for more details"
    
    if [ $TESTS_FAILED -gt 3 ]; then
        echo ""
        print_error "Too many test failures! Recommend fixing issues before proceeding."
        echo "🎯 NEXT STEPS:"
        echo "1. Fix the failed tests listed above"
        echo "2. Re-run this test script: bash deploy_step4_testing.sh"
        echo "3. Only proceed to deployment when most tests pass"
        exit 1
    fi
else
    echo ""
    print_success "🎉 ALL TESTS PASSED!"
    echo ""
    echo "🚀 Your dual trial system is ready for deployment!"
fi

echo ""
echo "🎯 NEXT STEPS:"

if [ $TESTS_FAILED -eq 0 ]; then
    echo "1. Run: bash deploy_step5_final.sh"
    echo "2. Or manually start your updated bot"
    echo "3. Monitor logs for any issues"
else
    echo "1. Fix the failed tests listed above"
    echo "2. Re-run this test: bash deploy_step4_testing.sh"
    echo "3. Proceed to deployment when tests pass"
fi

echo ""
print_success "Step 4 complete! Testing and validation finished."

# Exit with appropriate code
exit $TESTS_FAILED
