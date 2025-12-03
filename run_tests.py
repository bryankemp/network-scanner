#!/usr/bin/env python3
"""
Network Scanner Self-Test Runner

Comprehensive test suite runner with reporting and health checks.
Can be used for local development, CI/CD, or deployment verification.
"""
import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def run_command(cmd, description, cwd=None):
    """
    Run a shell command and return success status.
    
    Args:
        cmd: Command to run (list or string)
        description: Human-readable description
        cwd: Working directory for command (optional)
        
    Returns:
        bool: True if command succeeded
    """
    print(f"\n{Colors.BOLD}Running: {description}{Colors.RESET}")
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=cwd
        )
        
        if result.returncode == 0:
            print_success(f"{description} passed")
            if result.stdout.strip():
                print(f"  Output: {result.stdout[:200]}")
            return True
        else:
            print_error(f"{description} failed (exit code: {result.returncode})")
            if result.stderr:
                print(f"  Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out")
        return False
    except Exception as e:
        print_error(f"{description} error: {e}")
        return False


def check_dependencies():
    """Check that required dependencies are installed."""
    print_header("DEPENDENCY CHECK")
    
    checks = {
        "Python": ["python3", "--version"],
        "Pytest": ["python3", "-m", "pytest", "--version"],
        "Docker": ["docker", "--version"],
        "nmap": ["nmap", "--version"],
    }
    
    all_passed = True
    for name, cmd in checks.items():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print_success(f"{name}: {version}")
            else:
                print_error(f"{name}: Not found")
                all_passed = False
        except Exception:
            print_error(f"{name}: Not found")
            all_passed = False
    
    return all_passed


def run_unit_tests():
    """Run pytest unit tests."""
    print_header("UNIT TESTS")
    
    # Run backend tests
    backend_passed = run_command(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"],
        "Backend unit tests"
    )
    
    # Run MCP server tests
    mcp_passed = run_command(
        ["python3", "-m", "pytest", "mcp_server/test_mcp_server.py", "-v", "--tb=short"],
        "MCP server tests"
    )
    
    # Run Flutter frontend tests
    frontend_passed = True
    try:
        subprocess.run(["flutter", "--version"], capture_output=True, timeout=5, check=True)
        frontend_passed = run_command(
            ["flutter", "test"],
            "Flutter frontend tests",
            cwd="frontend"
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print_warning("Flutter not installed, skipping frontend tests")
    
    return backend_passed and mcp_passed and frontend_passed


def run_linting():
    """Run code linting checks."""
    print_header("CODE QUALITY")
    
    results = []
    
    # Check if ruff is available
    try:
        subprocess.run(["ruff", "--version"], capture_output=True, timeout=5)
        results.append(run_command(
            ["ruff", "check", "backend/app/", "--target-version", "py38"],
            "Ruff linting"
        ))
    except FileNotFoundError:
        print_warning("Ruff not installed, skipping lint check")
    
    # Check if black is available
    try:
        subprocess.run(["black", "--version"], capture_output=True, timeout=5)
        results.append(run_command(
            ["black", "backend/", "--check", "--line-length", "100"],
            "Black formatting check"
        ))
    except FileNotFoundError:
        print_warning("Black not installed, skipping format check")
    
    return all(results) if results else True


def check_health_endpoint():
    """Check if the health endpoint is accessible."""
    print_header("HEALTH CHECK")
    
    try:
        import requests
        
        # Try to connect to local or production endpoint
        endpoints = [
            "http://localhost:8000/api/health",
            "http://slag.kempville.com:8000/api/health"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"Health endpoint accessible: {endpoint}")
                    print(f"  Status: {data.get('status')}")
                    print(f"  Version: {data.get('version')}")
                    return True
            except requests.RequestException:
                continue
        
        print_warning("Health endpoint not accessible (service may not be running)")
        return False
        
    except ImportError:
        print_warning("Requests library not installed, skipping health check")
        return True


def generate_report(results):
    """Generate test report summary."""
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"Total checks: {total}")
    print(f"Passed: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"Failed: {Colors.RED}{failed}{Colors.RESET}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED ✓{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}SOME TESTS FAILED ✗{Colors.RESET}")
        print("\nFailed checks:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")
        return 1


def main():
    """Main test runner."""
    print(f"\n{Colors.BOLD}Network Scanner Self-Test Suite{Colors.RESET}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    results = {}
    
    # Run all test suites
    results["Dependencies"] = check_dependencies()
    results["Unit Tests"] = run_unit_tests()
    results["Code Quality"] = run_linting()
    results["Health Check"] = check_health_endpoint()
    
    # Generate final report
    exit_code = generate_report(results)
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
