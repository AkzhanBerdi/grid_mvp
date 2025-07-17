#!/bin/bash
# run_production_tests.sh
# Comprehensive production testing script for GridTrader Pro

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_CMD="python3"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/test_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create log directory
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

# Function to check Python environment
check_python_env() {
    print_status "Checking Python environment..."
    
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Found $PYTHON_VERSION"
    
    # Check required packages
    print_status "Checking required packages..."
    
    REQUIRED_PACKAGES=(
        "telegram"
        "python-binance" 
        "cryptography"
        "requests"
        "aiohttp"
    )
    
    MISSING_PACKAGES=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! $PYTHON_CMD -c "import ${package//-/_}" 2>/dev/null; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        print_warning "Missing packages detected: ${MISSING_PACKAGES[*]}"
        print_status "Installing missing packages..."
        
        for package in "${MISSING_PACKAGES[@]}"; do
            pip install "$package" || {
                print_error "Failed to install $package"
                exit 1
            }
        done
        
        print_success "All packages installed"
    else
        print_success "All required packages are installed"
    fi
}

# Function to check project structure
check_project_structure() {
    print_status "Checking project structure..."
    
    REQUIRED_DIRS=(
        "database"
        "handlers"
        "models"
        "repositories"
        "services"
        "utils"
        "analytics"
        "integration"
        "data"
    )
    
    REQUIRED_FILES=(
        "main.py"
        "config.py"
        "requirements.txt"
    )
    
    # Check directories
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$PROJECT_DIR/$dir" ]; then
            print_error "Required directory missing: $dir"
            exit 1
        fi
    done
    
    # Check files
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$PROJECT_DIR/$file" ]; then
            print_error "Required file missing: $file"
            exit 1
        fi
    done
    
    print_success "Project structure is valid"
}

# Function to check environment variables
check_environment() {
    print_status "Checking environment configuration..."
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_warning ".env file not found"
        print_status "Creating template .env file..."
        
        cat > "$PROJECT_DIR/.env.template" << 'EOF'
# GridTrader Pro Environment Configuration
# Copy this to .env and fill in your values

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_id_here

# Environment
ENVIRONMENT=production

# Database
DATABASE_PATH=data/gridtrader_clients.db

# Security
ENCRYPTION_KEY=your_32_character_encryption_key_here

# Logging
LOG_LEVEL=INFO
EOF
        
        print_warning "Template created: .env.template"
        print_warning "Copy to .env and configure before production deployment"
    else
        print_success "Environment file found"
    fi
    
    # Check critical environment variables (if .env exists)
    if [ -f "$PROJECT_DIR/.env" ]; then
        source "$PROJECT_DIR/.env"
        
        if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_telegram_bot_token_here" ]; then
            print_warning "TELEGRAM_BOT_TOKEN not configured"
        fi
        
        if [ -z "$ENCRYPTION_KEY" ] || [ "$ENCRYPTION_KEY" = "your_32_character_encryption_key_here" ]; then
            print_warning "ENCRYPTION_KEY not configured"
        fi
        
        if [ ${#ENCRYPTION_KEY} -lt 32 ]; then
            print_warning "ENCRYPTION_KEY should be at least 32 characters"
        fi
    fi
}

# Function to run quick validation
run_quick_validation() {
    print_status "Running quick validation..."
    
    LOG_FILE="$LOG_DIR/quick_validation_$TIMESTAMP.log"
    
    cd "$PROJECT_DIR"
    
    if $PYTHON_CMD final_fixed_test_runner.py > "$LOG_FILE" 2>&1; then
        print_success "Quick validation passed"
        return 0
    else
        print_error "Quick validation failed"
        print_status "Check log file: $LOG_FILE"
        return 1
    fi
}

# Function to run full test suite
run_full_test_suite() {
    print_status "Running comprehensive test suite..."
    
    LOG_FILE="$LOG_DIR/full_test_suite_$TIMESTAMP.log"
    
    cd "$PROJECT_DIR"
    
    if $PYTHON_CMD test_production_suite.py > "$LOG_FILE" 2>&1; then
        print_success "Full test suite passed"
        return 0
    else
        print_error "Full test suite failed"
        print_status "Check log file: $LOG_FILE"
        return 1
    fi
}

# Function to run component tests
run_component_tests() {
    print_status "Testing individual components..."
    
    LOG_FILE="$LOG_DIR/component_tests_$TIMESTAMP.log"
    
    cd "$PROJECT_DIR"
    
    $PYTHON_CMD quick_test_runner.py --components > "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Component tests completed"
    else
        print_warning "Some component tests failed - check log"
    fi
}

# Function to run stress tests
run_stress_tests() {
    print_status "Running stress tests..."
    
    LOG_FILE="$LOG_DIR/stress_tests_$TIMESTAMP.log"
    
    cd "$PROJECT_DIR"
    
    $PYTHON_CMD quick_test_runner.py --stress > "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Stress tests passed"
    else
        print_warning "Stress tests failed - check log"
    fi
}

# Function to generate test report
generate_test_report() {
    print_status "Generating test report..."
    
    REPORT_FILE="$LOG_DIR/test_report_$TIMESTAMP.md"
    
    cat > "$REPORT_FILE" << EOF
# GridTrader Pro - Production Test Report

**Generated:** $(date)
**Project Directory:** $PROJECT_DIR

## Test Summary

EOF
    
    # Add quick validation results
    if [ -f "$LOG_DIR/quick_validation_$TIMESTAMP.log" ]; then
        echo "### Quick Validation" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        tail -20 "$LOG_DIR/quick_validation_$TIMESTAMP.log" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
    
    # Add full test results
    if [ -f "$LOG_DIR/full_test_suite_$TIMESTAMP.log" ]; then
        echo "### Full Test Suite" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        tail -50 "$LOG_DIR/full_test_suite_$TIMESTAMP.log" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
    
    # Add deployment checklist
    echo "### Deployment Checklist" >> "$REPORT_FILE"
    $PYTHON_CMD quick_test_runner.py --checklist >> "$REPORT_FILE" 2>/dev/null || true
    
    print_success "Test report generated: $REPORT_FILE"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --quick         Run quick validation only"
    echo "  --full          Run full test suite"
    echo "  --components    Test individual components"
    echo "  --stress        Run stress tests"
    echo "  --all           Run all tests (default)"
    echo "  --check-env     Check environment only"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 --quick           # Quick validation only"
    echo "  $0 --full            # Full comprehensive tests"
    echo "  $0 --check-env       # Check environment setup"
}

# Main execution
main() {
    echo "🚀 GridTrader Pro - Production Test Runner"
    echo "=========================================="
    echo ""
    
    # Parse command line arguments
    QUICK_ONLY=false
    FULL_ONLY=false
    COMPONENTS_ONLY=false
    STRESS_ONLY=false
    CHECK_ENV_ONLY=false
    RUN_ALL=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_ONLY=true
                RUN_ALL=false
                shift
                ;;
            --full)
                FULL_ONLY=true
                RUN_ALL=false
                shift
                ;;
            --components)
                COMPONENTS_ONLY=true
                RUN_ALL=false
                shift
                ;;
            --stress)
                STRESS_ONLY=true
                RUN_ALL=false
                shift
                ;;
            --check-env)
                CHECK_ENV_ONLY=true
                RUN_ALL=false
                shift
                ;;
            --all)
                RUN_ALL=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Always check environment first
    check_python_env
    check_project_structure
    check_environment
    
    if [ "$CHECK_ENV_ONLY" = true ]; then
        print_success "Environment check completed"
        exit 0
    fi
    
    echo ""
    print_status "Starting test execution..."
    
    # Track overall success
    OVERALL_SUCCESS=true
    
    # Run selected tests
    if [ "$QUICK_ONLY" = true ] || [ "$RUN_ALL" = true ]; then
        if ! run_quick_validation; then
            OVERALL_SUCCESS=false
        fi
    fi
    
    if [ "$COMPONENTS_ONLY" = true ] || [ "$RUN_ALL" = true ]; then
        run_component_tests
    fi
    
    if [ "$STRESS_ONLY" = true ] || [ "$RUN_ALL" = true ]; then
        run_stress_tests
    fi
    
    if [ "$FULL_ONLY" = true ] || [ "$RUN_ALL" = true ]; then
        if ! run_full_test_suite; then
            OVERALL_SUCCESS=false
        fi
    fi
    
    # Generate report
    generate_test_report
    
    echo ""
    echo "=========================================="
    
    if [ "$OVERALL_SUCCESS" = true ]; then
        print_success "ALL TESTS COMPLETED SUCCESSFULLY!"
        echo ""
        print_status "🎉 Your application is ready for production deployment"
        print_status "📋 Review the deployment checklist in the test report"
        print_status "📊 Check detailed logs in: $LOG_DIR"
        exit 0
    else
        print_error "SOME TESTS FAILED"
        echo ""
        print_status "❌ Fix failing tests before production deployment"
        print_status "📊 Check detailed logs in: $LOG_DIR"
        print_status "🔧 Run individual test components to debug issues"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
