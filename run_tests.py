#!/usr/bin/env python3
"""
Script para executar testes da Medical Automation API
Inclui verificação de ambiente e execução dos testes
"""
import os
import sys
import subprocess
import time
import requests
import threading
from pathlib import Path

# Colors for console output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(message, color=Colors.END):
    """Print colored message"""
    print(f"{color}{message}{Colors.END}")

def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info < (3, 8):
        print_colored("❌ Python 3.8+ is required", Colors.RED)
        return False
    
    print_colored(f"✅ Python {sys.version.split()[0]} detected", Colors.GREEN)
    return True

def install_dependencies():
    """Install required packages for testing"""
    print_colored("\n📦 Installing test dependencies...", Colors.BLUE)
    
    packages = [
        "pytest>=6.0",
        "requests>=2.25.0",
        "pytest-cov>=2.10.0",
        "pytest-html>=3.0.0"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, check=True)
            
        except subprocess.CalledProcessError as e:
            print_colored(f"⚠️ Warning: Could not install {package}", Colors.YELLOW)
            print(f"Error: {e.stderr}")
    
    print_colored("✅ Dependencies installation completed", Colors.GREEN)

def check_api_server():
    """Check if API server is running"""
    print_colored("\n🔍 Checking if API server is running...", Colors.BLUE)
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print_colored("✅ API server is running", Colors.GREEN)
            return True
        else:
            print_colored(f"⚠️ API server responded with status {response.status_code}", Colors.YELLOW)
            return False
            
    except requests.exceptions.ConnectionError:
        print_colored("❌ API server is not running", Colors.RED)
        return False
    except requests.exceptions.Timeout:
        print_colored("⚠️ API server is slow to respond", Colors.YELLOW)
        return False

def start_api_server():
    """Start API server in background"""
    print_colored("\n🚀 Starting API server...", Colors.BLUE)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    src_dir = project_dir / "src"
    
    if not src_dir.exists():
        print_colored("❌ src directory not found", Colors.RED)
        return None
    
    # Start server process
    try:
        process = subprocess.Popen([
            sys.executable, "app.py"
        ], cwd=src_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if server is running
        if check_api_server():
            print_colored("✅ API server started successfully", Colors.GREEN)
            return process
        else:
            print_colored("❌ Failed to start API server", Colors.RED)
            process.terminate()
            return None
            
    except Exception as e:
        print_colored(f"❌ Error starting API server: {e}", Colors.RED)
        return None

def run_tests(test_file=None, verbose=True, coverage=False, html_report=False):
    """Run the tests"""
    print_colored("\n🧪 Running tests...", Colors.BLUE)
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append("tests/")
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short", "--color=yes"])
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    if html_report:
        cmd.extend(["--html=test_report.html", "--self-contained-html"])
    
    # Add durations to see slowest tests
    cmd.append("--durations=10")
    
    print_colored(f"Running command: {' '.join(cmd)}", Colors.BLUE)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print_colored("\n✅ All tests passed!", Colors.GREEN)
        else:
            print_colored(f"\n❌ Tests failed with exit code {result.returncode}", Colors.RED)
        
        return result.returncode
        
    except Exception as e:
        print_colored(f"❌ Error running tests: {e}", Colors.RED)
        return 1

def run_specific_test_categories():
    """Run specific categories of tests"""
    categories = {
        "1": ("API Endpoints", "tests/test_api_integration.py::TestAPIEndpoints"),
        "2": ("Cache Service", "tests/test_api_integration.py::TestCacheService"),
        "3": ("All Integration Tests", "tests/test_api_integration.py"),
        "4": ("All Tests", None)
    }
    
    print_colored("\n📋 Test Categories:", Colors.BLUE)
    for key, (name, _) in categories.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect category (1-4) or press Enter for all: ").strip()
    
    if choice in categories:
        name, test_path = categories[choice]
        print_colored(f"\n🎯 Running {name}...", Colors.BLUE)
        return run_tests(test_path)
    else:
        return run_tests()

def generate_test_report():
    """Generate comprehensive test report"""
    print_colored("\n📊 Generating comprehensive test report...", Colors.BLUE)
    
    return run_tests(
        test_file=None,
        verbose=True,
        coverage=True,
        html_report=True
    )

def main():
    """Main function"""
    print_colored("🏥 Medical Automation API - Test Runner", Colors.BOLD)
    print_colored("=" * 50, Colors.BLUE)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install dependencies
    install_dependencies()
    
    # Check if API is running
    api_running = check_api_server()
    server_process = None
    
    if not api_running:
        print_colored("\n⚠️ API server is not running. Would you like to start it? (y/n): ", Colors.YELLOW, end="")
        if input().strip().lower() in ['y', 'yes']:
            server_process = start_api_server()
            if not server_process:
                print_colored("❌ Cannot run integration tests without API server", Colors.RED)
                print_colored("💡 You can still run unit tests", Colors.YELLOW)
    
    try:
        # Menu for test options
        print_colored("\n🎯 Test Options:", Colors.BLUE)
        print("1. Run specific test category")
        print("2. Run all tests")
        print("3. Generate comprehensive report")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            exit_code = run_specific_test_categories()
        elif choice == "2":
            exit_code = run_tests()
        elif choice == "3":
            exit_code = generate_test_report()
            if exit_code == 0:
                print_colored("\n📄 Test report generated: test_report.html", Colors.GREEN)
        elif choice == "4":
            print_colored("👋 Goodbye!", Colors.BLUE)
            exit_code = 0
        else:
            print_colored("❌ Invalid option", Colors.RED)
            exit_code = 1
        
        return exit_code
        
    finally:
        # Clean up server process
        if server_process:
            print_colored("\n🛑 Stopping API server...", Colors.BLUE)
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print_colored("✅ API server stopped", Colors.GREEN)
            except subprocess.TimeoutExpired:
                server_process.kill()
                print_colored("🔨 API server forcefully stopped", Colors.YELLOW)

if __name__ == "__main__":
    sys.exit(main())
