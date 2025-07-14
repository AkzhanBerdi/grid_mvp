#!/bin/bash
# deploy_dual_trial_system.sh - Master deployment script

set -e  # Exit on any error

echo "🚀 GRIDTRADER PRO - DUAL TRIAL SYSTEM DEPLOYMENT"
echo "================================================="
echo ""
echo "This script will deploy the dual trial system with:"
echo "✅ 7-day Demo Trials"
echo "✅ 7-day Real Trading Trials"
echo "✅ Automatic trial progression"
echo "✅ Auto-stop on expiry"
echo "✅ Enhanced user experience"
echo ""

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
print_step() { echo -e "${PURPLE}🎯 $1${NC}"; }
print_deploy() { echo -e "${CYAN}🚀 $1${NC}"; }

# Check if running in interactive mode
INTERACTIVE=true
if [ "$1" == "--auto" ]; then
    INTERACTIVE=false
    print_info "Running in automatic mode"
fi

# Function to ask for confirmation
confirm_step() {
    if [ "$INTERACTIVE" = true ]; then
        echo ""
        read -p "Continue with this step? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "❌ Deployment aborted by user"
            exit 1
        fi
    fi
}

# Function to run a deployment step
run_step() {
    local step_num="$1"
    local step_name="$2"
    local step_script="$3"
    local step_desc="$4"
    
    echo ""
    echo "🎯 STEP $step_num: $step_name"
    echo "$(printf '=%.0s' {1..50})"
    echo "$step_desc"
    
    confirm_step
    
    if [ -f "$step_script" ]; then
        print_deploy "Running: $step_script"
        if bash "$step_script"; then
            print_success "Step $step_num completed successfully"
        else
            print_error "Step $step_num failed!"
            echo ""
            echo "🚨 DEPLOYMENT FAILED AT STEP $step_num"
            echo "💡 You can:"
            echo "1. Fix the issue and re-run: bash $step_script"
            echo "2. Run rollback: bash rollback.sh (if created)"
            echo "3. Get support: Check logs and documentation"
            exit 1
        fi
    else
        print_error "Step script not found: $step_script"
        exit 1
    fi
}

# Pre-deployment checks
print_info "Running pre-deployment checks..."

# Check if we're in the right directory
if [ ! -f "config.py" ] && [ ! -f "main.py" ]; then
    print_error "Not in GridTrader project directory!"
    echo "Please run this script from your GridTrader project root."
    exit 1
fi

print_success "Project directory confirmed"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python 3.8+ required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Python version: $PYTHON_VERSION"

# Check if deployment scripts exist
REQUIRED_SCRIPTS=(
    "deploy_step1_backup.sh"
    "deploy_step2_migration.sh" 
    "deploy_step3_code_update.sh"
    "deploy_step4_testing.sh"
    "deploy_step5_final.sh"
)

MISSING_SCRIPTS=()
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        MISSING_SCRIPTS+=("$script")
    fi
done

if [ ${#MISSING_SCRIPTS[@]} -gt 0 ]; then
    print_error "Missing deployment scripts:"
    for script in "${MISSING_SCRIPTS[@]}"; do
        echo "  • $script"
    done
    echo ""
    echo "Please ensure all deployment scripts are in the current directory."
    exit 1
fi

print_success "All deployment scripts found"

# Show deployment plan
echo ""
echo "📋 DEPLOYMENT PLAN"
echo "=================="
echo "Step 1: Backup & Preparation"
echo "  • Create full system backup"
echo "  • Verify environment"
echo "  • Create rollback script"
echo ""
echo "Step 2: Database Migration"
echo "  • Add dual trial columns"
echo "  • Migrate existing users"
echo "  • Verify schema"
echo ""
echo "Step 3: Code Updates"
echo "  • Update User model"
echo "  • Test new functionality"
echo "  • Verify integrations"
echo ""
echo "Step 4: Testing & Validation"
echo "  • Run comprehensive tests"
echo "  • Validate all components"
echo "  • Performance checks"
echo ""
echo "Step 5: Final Deployment"
echo "  • Start new system"
echo "  • Monitor startup"
echo "  • Verify operation"
echo ""

if [ "$INTERACTIVE" = true ]; then
    echo "⚠️  IMPORTANT NOTES:"
    echo "• This process will modify your database"
    echo "• Your bot will be temporarily stopped"
    echo "• Backups will be created automatically"
    echo "• You can rollback if needed"
    echo ""
    
    read -p "Ready to proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled by user"
        exit 1
    fi
fi

# Record deployment start
DEPLOYMENT_START=$(date)
echo "🕐 Deployment started: $DEPLOYMENT_START" | tee deployment.log

# Execute deployment steps
run_step "1" "Backup & Preparation" "deploy_step1_backup.sh" \
    "Creates comprehensive backups and prepares environment"

run_step "2" "Database Migration" "deploy_step2_migration.sh" \
    "Migrates database to support dual trial system"

run_step "3" "Code Updates" "deploy_step3_code_update.sh" \
    "Updates models and core functionality"

run_step "4" "Testing & Validation" "deploy_step4_testing.sh" \
    "Runs comprehensive test suite"

run_step "5" "Final Deployment" "deploy_step5_final.sh" \
    "Deploys and starts the updated system"

# Deployment completed successfully
DEPLOYMENT_END=$(date)
echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "===================================="
echo "🕐 Started:  $DEPLOYMENT_START"
echo "🕐 Finished: $DEPLOYMENT_END"
echo ""
echo "✅ Dual Trial System Features Active:"
echo "  • 7-day Demo Trials for new users"
echo "  • 7-day Real Trading Trials (upgrade from demo)"
echo "  • Automatic trial expiry handling"
echo "  • Enhanced user progression"
echo "  • Backwards compatibility maintained"
echo ""
echo "🎯 IMMEDIATE NEXT STEPS:"
echo "1. Test your bot: Send /start to your Telegram bot"
echo "2. Monitor logs: tail -f data/logs/gridtrader.log"
echo "3. Watch deployment: ./monitor_deployment.sh"
echo ""
echo "📱 TEST SCENARIOS:"
echo "• New user registration → Demo trial"
echo "• Demo trial → Real trial upgrade"
echo "• Trading functionality in both modes"
echo "• Trial expiry behavior"
echo ""
echo "🛠️  MANAGEMENT:"
echo "• Check status: ps aux | grep python"
echo "• View logs: tail -f data/logs/gridtrader.log"
echo "• Stop bot: kill \$(cat bot.pid)"
echo "• Emergency rollback: ./rollback.sh"
echo ""
echo "📊 MONITORING:"
echo "• Live dashboard: ./monitor_deployment.sh"
echo "• Database health: sqlite3 data/gridtrader.db"
echo "• User analytics: Check conversion funnel"
echo ""

# Create quick reference
cat > DEPLOYMENT_QUICK_REFERENCE.md << EOF
# GridTrader Pro Dual Trial System - Quick Reference

## Deployment Info
- **Deployed:** $DEPLOYMENT_END
- **Features:** Dual Trial System (Demo → Real)
- **Status:** Active

## Key Files
- **Main Bot:** \`$(ls main*.py | head -1)\`
- **Database:** \`data/gridtrader.db\`
- **Logs:** \`data/logs/gridtrader.log\`
- **Rollback:** \`./rollback.sh\`

## Management Commands
\`\`\`bash
# Check status
ps aux | grep python

# View logs  
tail -f data/logs/gridtrader.log

# Stop bot
kill \$(cat bot.pid)

# Restart bot
python3 $(ls main*.py | head -1)

# Emergency rollback
./rollback.sh

# Live monitoring
./monitor_deployment.sh
\`\`\`

## User Journey
1. **New User** → 7-day Demo Trial (automatic)
2. **Demo User** → Can upgrade to 7-day Real Trial
3. **Real Trial** → Expires automatically, prompts for subscription
4. **Paid User** → Unlimited access

## Testing Checklist
- [ ] New user gets demo trial
- [ ] Demo trial works (virtual trading)
- [ ] Upgrade to real trial works
- [ ] Real trial works (actual API keys)
- [ ] Trial expiry stops trading
- [ ] Notifications work
- [ ] Dashboard shows correct status

## Support
- Check logs for errors
- Use rollback if critical issues
- Monitor user feedback
- Track conversion metrics

---
*Deployed: $DEPLOYMENT_END*
EOF

print_success "Quick reference created: DEPLOYMENT_QUICK_REFERENCE.md"
echo ""
print_success "🚀 GridTrader Pro Dual Trial System is now LIVE!"
echo ""
echo "💡 Don't forget to:"
echo "  • Test the user flows"
echo "  • Monitor the first few users"
echo "  • Check conversion metrics"
echo "  • Gather user feedback"
echo ""
print_success "Happy trading! 🎉"
