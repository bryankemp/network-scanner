#!/usr/bin/env python3
"""
Network Scanner Setup Script

This script automates the setup of the Network Scanner development environment,
service installation, or container generation.

Usage:
    python3 setup.py dev       # Set up development environment
    python3 setup.py service   # Install as system service (requires sudo)
    python3 setup.py docker    # Build and run Docker containers
    python3 setup.py clean     # Clean up development artifacts
    python3 setup.py test      # Run comprehensive test suite

Author: Bryan Kemp <bryan@kempville.com>
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


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


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def run_command(cmd, description, cwd=None, check=True):
    """Run a shell command and handle errors."""
    print_info(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
        if result.returncode == 0:
            print_success(description)
            return True
        else:
            print_error(f"{description} failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print_error(f"{description} failed: {e}")
        return False


def check_prerequisites():
    """Check if required tools are installed."""
    print_header("Checking Prerequisites")

    tools = {
        "python3": ["python3", "--version"],
        "nmap": ["nmap", "--version"],
        "docker": ["docker", "--version"],
        "flutter": ["flutter", "--version"],
    }

    required = ["python3", "nmap"]
    optional = ["docker", "flutter"]

    all_required_present = True

    for tool, cmd in tools.items():
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.decode().strip().split("\n")[0]
                print_success(f"{tool}: {version}")
            else:
                if tool in required:
                    print_error(f"{tool}: Not found (REQUIRED)")
                    all_required_present = False
                else:
                    print_warning(f"{tool}: Not found (optional)")
        except Exception:
            if tool in required:
                print_error(f"{tool}: Not found (REQUIRED)")
                all_required_present = False
            else:
                print_warning(f"{tool}: Not found (optional)")

    return all_required_present


def setup_backend():
    """Set up Python backend environment."""
    print_header("Setting Up Backend")

    backend_dir = Path("backend")
    venv_dir = backend_dir / "venv"

    # Create virtual environment
    if not venv_dir.exists():
        print_info("Creating Python virtual environment...")
        if not run_command(
            [sys.executable, "-m", "venv", str(venv_dir)],
            "Create virtual environment",
            cwd=backend_dir,
        ):
            return False
    else:
        print_success("Virtual environment already exists")

    # Determine pip path (use absolute path)
    if platform.system() == "Windows":
        pip_path = (Path.cwd() / venv_dir / "Scripts" / "pip").resolve()
    else:
        pip_path = (Path.cwd() / venv_dir / "bin" / "pip").resolve()

    # Upgrade pip
    run_command(
        [str(pip_path), "install", "--upgrade", "pip"],
        "Upgrade pip",
    )

    # Install dependencies
    if not run_command(
        [str(pip_path), "install", "-r", "requirements.txt"],
        "Install backend dependencies",
        cwd=backend_dir,
    ):
        return False

    # Install development dependencies
    run_command(
        [str(pip_path), "install", "ruff", "black", "pytest"],
        "Install development tools",
        cwd=backend_dir,
        check=False,
    )

    print_success("Backend setup complete")
    return True


def setup_mcp_server():
    """Set up MCP server environment."""
    print_header("Setting Up MCP Server")

    mcp_dir = Path("mcp_server")

    # Install MCP server dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Install MCP server dependencies",
        cwd=mcp_dir,
    ):
        return False

    print_success("MCP server setup complete")
    return True


def setup_frontend():
    """Set up Flutter frontend environment."""
    print_header("Setting Up Frontend")

    frontend_dir = Path("frontend")

    # Check if Flutter is available
    try:
        subprocess.run(["flutter", "--version"], capture_output=True, timeout=5, check=True)
    except Exception:
        print_warning("Flutter not installed. Skipping frontend setup.")
        print_info("Install Flutter from: https://flutter.dev/docs/get-started/install")
        return True

    # Get Flutter dependencies
    if not run_command(
        ["flutter", "pub", "get"], "Get Flutter dependencies", cwd=frontend_dir
    ):
        return False

    print_success("Frontend setup complete")
    return True


def setup_dev_environment():
    """Set up complete development environment."""
    print_header("Development Environment Setup")

    if not check_prerequisites():
        print_error("Missing required prerequisites. Please install them and try again.")
        return False

    success = True
    success = setup_backend() and success
    success = setup_mcp_server() and success
    success = setup_frontend() and success

    if success:
        print_header("Setup Complete!")
        print_success("Development environment is ready")
        print_info("\nNext steps:")
        print("  1. Start backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload")
        print("  2. Start frontend: cd frontend && flutter run -d chrome")
        print("  3. Run tests: python3 run_tests.py")
    else:
        print_error("Setup encountered errors. Please check the output above.")

    return success


def install_service():
    """Install Network Scanner as a system service."""
    print_header("Installing System Service")

    system = platform.system()

    if system == "Darwin":  # macOS
        install_launchd_service()
    elif system == "Linux":
        install_systemd_service()
    else:
        print_error(f"Service installation not supported on {system}")
        return False


def install_launchd_service():
    """Install as macOS launchd service."""
    print_info("Installing macOS launchd service...")

    project_dir = Path.cwd()
    plist_path = Path.home() / "Library/LaunchAgents/com.kempville.network-scanner.plist"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kempville.network-scanner</string>
    <key>ProgramArguments</key>
    <array>
        <string>{project_dir}/backend/venv/bin/uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_dir}/backend</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{project_dir}/network-scanner.log</string>
    <key>StandardErrorPath</key>
    <string>{project_dir}/network-scanner-error.log</string>
</dict>
</plist>
"""

    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist_content)
    print_success(f"Created service file: {plist_path}")

    # Load the service
    run_command(
        ["launchctl", "load", str(plist_path)],
        "Load launchd service",
    )

    print_success("Service installed successfully")
    print_info(f"Service will start automatically at login")
    print_info(f"Logs: {project_dir}/network-scanner.log")


def install_systemd_service():
    """Install as Linux systemd service."""
    print_info("Installing systemd service...")

    project_dir = Path.cwd()
    service_path = Path("/etc/systemd/system/network-scanner.service")

    service_content = f"""[Unit]
Description=Network Scanner Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={project_dir}/backend
ExecStart={project_dir}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    print_warning("This requires sudo privileges...")
    try:
        subprocess.run(
            ["sudo", "tee", str(service_path)],
            input=service_content.encode(),
            check=True,
        )
        print_success(f"Created service file: {service_path}")

        run_command(["sudo", "systemctl", "daemon-reload"], "Reload systemd")
        run_command(
            ["sudo", "systemctl", "enable", "network-scanner"],
            "Enable service",
        )
        run_command(
            ["sudo", "systemctl", "start", "network-scanner"],
            "Start service",
        )

        print_success("Service installed and started")
        print_info("Check status: sudo systemctl status network-scanner")
        print_info("View logs: sudo journalctl -u network-scanner -f")
    except Exception as e:
        print_error(f"Failed to install service: {e}")


def build_docker():
    """Build and optionally run Docker containers."""
    print_header("Building Docker Containers")

    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=5, check=True)
    except Exception:
        print_error("Docker is not installed")
        return False

    # Check if Flutter is available
    try:
        subprocess.run(["flutter", "--version"], capture_output=True, timeout=5, check=True)
        has_flutter = True
    except Exception:
        print_warning("Flutter not installed. Skipping frontend build.")
        has_flutter = False

    # Build Flutter web frontend if Flutter is available
    if has_flutter:
        frontend_dir = Path("frontend")
        build_dir = frontend_dir / "build" / "web"
        
        # Check if rebuild is needed by comparing timestamps
        needs_rebuild = True
        if build_dir.exists():
            # Get most recent modification time of source files
            lib_dir = frontend_dir / "lib"
            pubspec_file = frontend_dir / "pubspec.yaml"
            
            source_files = list(lib_dir.rglob("*.dart")) if lib_dir.exists() else []
            source_files.append(pubspec_file) if pubspec_file.exists() else None
            
            if source_files:
                newest_source = max(f.stat().st_mtime for f in source_files if f.exists())
                oldest_build = min(
                    f.stat().st_mtime for f in build_dir.rglob("*") if f.is_file()
                ) if any(build_dir.rglob("*")) else 0
                
                if oldest_build > newest_source:
                    needs_rebuild = False
                    print_success("Flutter web build is up to date, skipping rebuild")
        
        if needs_rebuild:
            # Get dependencies first
            if not run_command(
                ["flutter", "pub", "get"],
                "Get Flutter dependencies",
                cwd=frontend_dir,
            ):
                print_warning("Failed to get Flutter dependencies. Continuing anyway...")
            
            # Build for web
            if not run_command(
                ["flutter", "build", "web", "--release"],
                "Build Flutter web app",
                cwd=frontend_dir,
            ):
                print_error("Failed to build Flutter frontend")
                return False
            
            print_success("Flutter web build complete")
    else:
        # Create empty static directory to avoid Docker build failure
        static_dir = Path("frontend/build/web")
        static_dir.mkdir(parents=True, exist_ok=True)
        (static_dir / "index.html").write_text(
            "<html><body><h1>Frontend not available - Flutter not installed</h1></body></html>"
        )
        print_warning("Created placeholder static directory")

    # Build production image
    if not run_command(
        ["docker", "build", "-f", "Dockerfile.production", "-t", "network-scanner:latest", "."],
        "Build production Docker image",
    ):
        return False

    print_success("Docker image built successfully")
    print_info("\nTo run the container:")
    print("  docker-compose -f docker-compose.production.yml up -d")
    print("\nOr use docker-compose for development:")
    print("  docker-compose up -d")

    return True


def clean_artifacts():
    """Clean up development artifacts."""
    print_header("Cleaning Development Artifacts")

    patterns = [
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "frontend/build",
        "frontend/.dart_tool",
        "scan_outputs",
    ]

    for pattern in patterns:
        if "*" in pattern:
            # Find and delete files matching pattern
            run_command(
                f'find . -name "{pattern}" -type f -delete',
                f"Remove {pattern}",
                check=False,
            )
        else:
            # Find and delete directories
            run_command(
                f'find . -name "{pattern}" -type d -exec rm -rf {{}} + 2>/dev/null || true',
                f"Remove {pattern} directories",
                check=False,
            )

    print_success("Cleanup complete")


def run_tests():
    """Run comprehensive test suite."""
    print_header("Running Tests")

    if not Path("run_tests.py").exists():
        print_error("Test runner not found")
        return False

    return run_command(
        [sys.executable, "run_tests.py"],
        "Run comprehensive test suite",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Network Scanner Setup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup.py dev         # Set up development environment
  python3 setup.py service     # Install as system service
  python3 setup.py docker      # Build Docker containers
  python3 setup.py clean       # Clean up artifacts
  python3 setup.py test        # Run tests
        """,
    )

    parser.add_argument(
        "command",
        choices=["dev", "service", "docker", "clean", "test"],
        help="Setup command to execute",
    )

    args = parser.parse_args()

    print_header("Network Scanner Setup")
    print_info(f"Platform: {platform.system()} {platform.release()}")
    print_info(f"Python: {sys.version.split()[0]}")

    if args.command == "dev":
        success = setup_dev_environment()
    elif args.command == "service":
        success = install_service()
    elif args.command == "docker":
        success = build_docker()
    elif args.command == "clean":
        clean_artifacts()
        success = True
    elif args.command == "test":
        success = run_tests()
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
