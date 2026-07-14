#!/bin/bash
# Test runner script for corpus-server-app
# Provides convenient commands for running different types of tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Default values
COVERAGE=false
PARALLEL=false
VERBOSE=false
FAST_MODE=false
HTML_COV=false

# Help function
show_help() {
    echo -e "${BLUE}Corpus Server Test Runner${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [OPTIONS] [COMMAND] [ARGS...]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  all                 Run all tests (default)"
    echo "  unit               Run unit tests only"
    echo "  integration        Run integration tests only"
    echo "  security           Run security tests only"
    echo "  auth               Run authentication-related tests"
    echo "  validation         Run validation tests"
    echo "  api                Run API endpoint tests"
    echo "  slow               Run only slow tests"
    echo "  fast               Run only fast tests (excludes slow tests)"
    echo "  failed             Re-run only failed tests from last run"
    echo "  coverage           Run tests with coverage report"
    echo "  watch [PATH]       Watch for changes and re-run tests"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  -c, --coverage     Enable coverage reporting"
    echo "  -h, --html-cov     Generate HTML coverage report"
    echo "  -p, --parallel     Run tests in parallel"
    echo "  -v, --verbose      Verbose output"
    echo "  -f, --fast         Enable fast mode (skip slow tests)"
    echo "  --help             Show this help message"
    echo ""
    echo -e "${YELLOW}Environment Variables:${NC}"
    echo "  RUN_INTEGRATION_TESTS=1    Enable integration tests"
    echo "  RUN_SECURITY_TESTS=1       Enable security tests"
    echo "  TEST_DATABASE_URL          Test database connection string"
    echo "  PYTEST_FAST_MODE=1         Skip slow tests globally"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 unit -v                 Run unit tests with verbose output"
    echo "  $0 integration -c          Run integration tests with coverage"
    echo "  $0 auth --parallel         Run auth tests in parallel"
    echo "  $0 coverage --html-cov     Run all tests with HTML coverage report"
    echo "  $0 watch tests/unit/       Watch unit tests for changes"
}

# Check if pytest is available
check_dependencies() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}Error: pytest is not installed${NC}"
        echo "Install it with: pip install pytest"
        exit 1
    fi
}

# Setup test environment
setup_environment() {
    echo -e "${BLUE}Setting up test environment...${NC}"
    
    # Set testing environment variables
    export TESTING=1
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
    
    # Set fast mode if requested
    if [ "$FAST_MODE" = true ]; then
        export PYTEST_FAST_MODE=1
    fi
    
    # Check for test database if needed
    if [ -z "$TEST_DATABASE_URL" ] && [ -z "$DATABASE_URL" ]; then
        echo -e "${YELLOW}Warning: No test database configured${NC}"
        echo "Set TEST_DATABASE_URL for database-dependent tests"
    fi
}

# Build pytest command
build_pytest_command() {
    local cmd="pytest"
    
    # Add coverage options
    if [ "$COVERAGE" = true ]; then
        cmd="$cmd --cov=app --cov-report=term-missing"
        if [ "$HTML_COV" = true ]; then
            cmd="$cmd --cov-report=html:htmlcov"
        fi
    fi
    
    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        if command -v pytest-xdist &> /dev/null; then
            cmd="$cmd -n auto"
        else
            echo -e "${YELLOW}Warning: pytest-xdist not installed, cannot run in parallel${NC}"
            echo "Install it with: pip install pytest-xdist"
        fi
    fi
    
    # Add verbose output
    if [ "$VERBOSE" = true ]; then
        cmd="$cmd -v"
    fi
    
    echo "$cmd"
}

# Run specific test category
run_tests() {
    local test_type="$1"
    local pytest_cmd
    pytest_cmd=$(build_pytest_command)
    
    echo -e "${BLUE}Running ${test_type} tests...${NC}"
    
    case "$test_type" in
        "all")
            $pytest_cmd tests/
            ;;
        "unit")
            $pytest_cmd tests/unit/
            ;;
        "integration")
            export RUN_INTEGRATION_TESTS=1
            $pytest_cmd tests/integration/
            ;;
        "security")
            export RUN_SECURITY_TESTS=1
            $pytest_cmd tests/security/
            ;;
        "auth")
            $pytest_cmd -m auth
            ;;
        "validation")
            $pytest_cmd -m validation
            ;;
        "api")
            export RUN_INTEGRATION_TESTS=1
            $pytest_cmd -m api
            ;;
        "slow")
            $pytest_cmd -m slow
            ;;
        "fast")
            $pytest_cmd -m "not slow"
            ;;
        "failed")
            $pytest_cmd --lf
            ;;
        "coverage")
            pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov tests/
            echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
            ;;
        *)
            echo -e "${RED}Unknown test type: $test_type${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Watch mode for continuous testing
run_watch() {
    local watch_path="${1:-tests/}"
    
    if ! command -v pytest-watch &> /dev/null; then
        echo -e "${YELLOW}pytest-watch not found, installing...${NC}"
        pip install pytest-watch
    fi
    
    echo -e "${BLUE}Watching $watch_path for changes...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    
    ptw --runner "pytest -x" "$watch_path"
}

# Clean up previous test artifacts
cleanup() {
    echo -e "${BLUE}Cleaning up test artifacts...${NC}"
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Show test statistics
show_stats() {
    echo -e "${BLUE}Test Statistics:${NC}"
    
    # Count test files
    local unit_tests=$(find tests/unit -name "test_*.py" | wc -l)
    local integration_tests=$(find tests/integration -name "test_*.py" | wc -l)
    local security_tests=$(find tests/security -name "test_*.py" | wc -l)
    local total_files=$((unit_tests + integration_tests + security_tests))
    
    echo "  Test files:"
    echo "    Unit:        $unit_tests files"
    echo "    Integration: $integration_tests files"
    echo "    Security:    $security_tests files"
    echo "    Total:       $total_files files"
    
    # Show fixture files
    local fixture_files=$(find tests/fixtures -name "*.py" ! -name "__init__.py" | wc -l)
    local helper_files=$(find tests/helpers -name "*.py" ! -name "__init__.py" | wc -l)
    
    echo "  Support files:"
    echo "    Fixtures:    $fixture_files files"
    echo "    Helpers:     $helper_files files"
}

# Main execution
main() {
    local command=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--coverage)
                COVERAGE=true
                shift
                ;;
            -h|--html-cov)
                HTML_COV=true
                COVERAGE=true
                shift
                ;;
            -p|--parallel)
                PARALLEL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -f|--fast)
                FAST_MODE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            clean|cleanup)
                cleanup
                exit 0
                ;;
            stats)
                show_stats
                exit 0
                ;;
            watch)
                shift
                check_dependencies
                setup_environment
                run_watch "$1"
                exit 0
                ;;
            all|unit|integration|security|auth|validation|api|slow|fast|failed|coverage)
                command="$1"
                shift
                break
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default to running all tests
    if [ -z "$command" ]; then
        command="all"
    fi
    
    # Check dependencies and setup
    check_dependencies
    setup_environment
    
    # Run the tests
    echo -e "${BLUE}Corpus Server Test Suite${NC}"
    echo -e "${BLUE}========================${NC}"
    
    local start_time=$(date +%s)
    
    if run_tests "$command"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}✅ Tests completed successfully in ${duration}s${NC}"
        
        if [ "$COVERAGE" = true ] && [ "$HTML_COV" = true ]; then
            echo -e "${GREEN}📊 Coverage report: file://$PROJECT_ROOT/htmlcov/index.html${NC}"
        fi
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}❌ Tests failed after ${duration}s${NC}"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"