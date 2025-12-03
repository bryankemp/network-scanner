#!/usr/bin/env python3
"""
Network Scanner Setup Script

This script automates the setup of the Network Scanner development environment,
service installation, or container generation. It can automatically install
missing dependencies using snap (Flutter, Docker) or apt (nmap) on Ubuntu/Linux.

Usage:
    python3 setup.py dev            # Set up development environment (auto-installs tools)
    python3 setup.py install-tools  # Install missing tools only (nmap, Flutter, Docker)
    python3 setup.py service        # Install as system service (requires sudo)
    python3 setup.py docker         # Build and run Docker containers
    python3 setup.py clean          # Clean up development artifacts
    python3 setup.py test           # Run comprehensive test suite

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


def run_command(cmd, description, cwd=None, check=True, verbose=None):
    """Run a shell command and handle errors."""
    # Use global VERBOSE if verbose not explicitly set
    if verbose is None:
        verbose = VERBOSE
    
    print_info(f"Running: {description}")
    if verbose:
        cmd_str = cmd if isinstance(cmd, str) else ' '.join(cmd)
        print_info(f"Command: {cmd_str}")
        if cwd:
            print_info(f"Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
        if verbose:
            if result.stdout:
                print(f"stdout: {result.stdout}")
            if result.stderr:
                print(f"stderr: {result.stderr}")
        
        if result.returncode == 0:
            print_success(description)
            return True
        else:
            print_error(f"{description} failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout and verbose:
                print(f"Output: {result.stdout}")
            return False
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if e.stdout and verbose:
            print(f"Output: {e.stdout}")
        return False
    except Exception as e:
        print_error(f"{description} failed: {e}")
        return False


def is_tool_installed(tool_cmd):
    """Check if a tool is installed."""
    try:
        result = subprocess.run(
            tool_cmd, capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def install_nmap():
    """Install nmap using apt."""
    print_info("Installing nmap...")
    if platform.system() != "Linux":
        print_error("Automatic nmap installation only supported on Linux")
        print_info("macOS: brew install nmap")
        return False
    
    if not run_command(
        ["sudo", "apt-get", "update"],
        "Update apt package list",
        check=False,
    ):
        return False
    
    if not run_command(
        ["sudo", "apt-get", "install", "-y", "nmap"],
        "Install nmap",
    ):
        return False
    
    # Grant nmap capabilities for non-root scanning
    run_command(
        ["sudo", "setcap", "cap_net_raw,cap_net_admin+eip", "/usr/bin/nmap"],
        "Grant nmap capabilities",
        check=False,
    )
    
    print_success("nmap installed successfully")
    return True


def install_flutter():
    """Install Flutter using snap."""
    print_info("Installing Flutter via snap...")
    
    if not is_tool_installed(["snap", "--version"]):
        print_error("snapd not available. Please install Flutter manually.")
        print_info("Visit: https://flutter.dev/docs/get-started/install")
        return False
    
    if not run_command(
        ["sudo", "snap", "install", "flutter", "--classic"],
        "Install Flutter",
    ):
        return False
    
    # Add Flutter to PATH for current session
    flutter_bin = "/snap/bin/flutter"
    if os.path.exists(flutter_bin):
        os.environ["PATH"] = f"/snap/bin:{os.environ.get('PATH', '')}"
    
    # Trigger SDK download by running flutter --version
    print_info("Downloading Flutter SDK (this may take a few minutes)...")
    try:
        result = subprocess.run(
            [flutter_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for SDK download
        )
        if VERBOSE:
            if result.stdout:
                print(f"Flutter output: {result.stdout}")
            if result.stderr:
                print(f"Flutter stderr: {result.stderr}")
        
        if result.returncode == 0:
            print_success("Flutter SDK downloaded successfully")
        else:
            print_warning("Flutter SDK download may not be complete")
            if result.stderr:
                print(f"Warning: {result.stderr}")
    except subprocess.TimeoutExpired:
        print_error("Flutter SDK download timed out")
        return False
    except Exception as e:
        print_warning(f"Could not verify Flutter SDK download: {e}")
    
    print_success("Flutter installed successfully")
    print_info("You may need to restart your terminal or run: export PATH=/snap/bin:$PATH")
    return True


def install_docker():
    """Install Docker using snap."""
    print_info("Installing Docker via snap...")
    
    if not is_tool_installed(["snap", "--version"]):
        print_error("snapd not available. Please install Docker manually.")
        print_info("Visit: https://docs.docker.com/engine/install/")
        return False
    
    # Create docker group if it doesn't exist
    print_info("Ensuring docker group exists...")
    run_command(
        ["sudo", "groupadd", "-f", "docker"],
        "Create docker group",
        check=False,
    )
    
    # Add user to docker group before installing
    username = os.getenv("USER", os.getenv("USERNAME", ""))
    if username:
        if not run_command(
            ["sudo", "usermod", "-aG", "docker", username],
            f"Add {username} to docker group",
            check=False,
        ):
            print_warning(f"Could not add {username} to docker group")
    
    # Install Docker snap
    if not run_command(
        ["sudo", "snap", "install", "docker"],
        "Install Docker",
    ):
        return False
    
    # Connect docker snap to home interface for access to user files
    run_command(
        ["sudo", "snap", "connect", "docker:home"],
        "Connect Docker snap to home interface",
        check=False,
    )
    
    print_success("Docker installed successfully")
    print_warning("Docker group membership requires a new login session to take effect.")
    print_info("To use Docker immediately in this session, run: newgrp docker")
    print_info("Or log out and back in for permanent effect.")
    return True


def check_prerequisites(auto_install=False):
    """Check if required tools are installed.
    
    Args:
        auto_install: If True, attempt to install missing tools automatically
    """
    print_header("Checking Prerequisites")

    tools = {
        "python3": {"cmd": ["python3", "--version"], "installer": None},
        "nmap": {"cmd": ["nmap", "--version"], "installer": install_nmap},
        "docker": {"cmd": ["docker", "--version"], "installer": install_docker},
        "flutter": {"cmd": ["flutter", "--version"], "installer": install_flutter},
    }

    required = ["python3", "nmap"]
    optional = ["docker", "flutter"]

    all_required_present = True
    missing_tools = []

    for tool, info in tools.items():
        if is_tool_installed(info["cmd"]):
            try:
                result = subprocess.run(
                    info["cmd"], capture_output=True, timeout=5, text=True
                )
                version = result.stdout.strip().split("\n")[0]
                print_success(f"{tool}: {version}")
            except Exception:
                print_success(f"{tool}: Installed")
        else:
            if tool in required:
                print_error(f"{tool}: Not found (REQUIRED)")
                all_required_present = False
                missing_tools.append(tool)
            else:
                print_warning(f"{tool}: Not found (optional)")
                if auto_install and info["installer"]:
                    missing_tools.append(tool)

    # Attempt to install missing tools
    if auto_install and missing_tools:
        print_header("Installing Missing Tools")
        for tool in missing_tools:
            info = tools[tool]
            if info["installer"]:
                print_info(f"Attempting to install {tool}...")
                if info["installer"]():
                    if tool in required:
                        all_required_present = True
                else:
                    if tool in required:
                        print_error(f"Failed to install required tool: {tool}")
                        all_required_present = False

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
            [sys.executable, "-m", "venv", "venv"],
            "Create virtual environment",
            cwd=backend_dir,
        ):
            return False
    else:
        print_success("Virtual environment already exists")

    # Determine pip path (use absolute path)
    if platform.system() == "Windows":
        pip_path = (venv_dir / "Scripts" / "pip").resolve()
    else:
        pip_path = (venv_dir / "bin" / "pip").resolve()

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
    backend_venv_dir = Path("backend") / "venv"

    # Use the backend venv pip to install MCP dependencies
    if platform.system() == "Windows":
        pip_path = (backend_venv_dir / "Scripts" / "pip").resolve()
    else:
        pip_path = (backend_venv_dir / "bin" / "pip").resolve()

    # Install MCP server dependencies using backend venv
    if not run_command(
        [str(pip_path), "install", "-r", "requirements.txt"],
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

    # Check if Flutter is available (check snap path explicitly)
    flutter_cmd = "flutter"
    if os.path.exists("/snap/bin/flutter"):
        flutter_cmd = "/snap/bin/flutter"
    
    try:
        subprocess.run([flutter_cmd, "--version"], capture_output=True, timeout=5, check=True)
    except Exception:
        print_warning("Flutter not installed. Skipping frontend setup.")
        print_info("Install Flutter from: https://flutter.dev/docs/get-started/install")
        return True

    # Ensure web platform is configured
    run_command(
        [flutter_cmd, "create", ".", "--platforms", "web"],
        "Configure Flutter web platform",
        cwd=frontend_dir,
        check=False,  # Don't fail if already configured
    )

    # Get Flutter dependencies
    if not run_command(
        [flutter_cmd, "pub", "get"], "Get Flutter dependencies", cwd=frontend_dir
    ):
        return False

    print_success("Frontend setup complete")
    return True


def setup_dev_environment():
    """Set up complete development environment."""
    print_header("Development Environment Setup")

    # Check prerequisites and auto-install missing tools
    if not check_prerequisites(auto_install=True):
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

    # Clean up any stale Docker resources (orphaned containers, networks)
    print_info("Cleaning up stale Docker resources...")
    run_command(
        ["docker", "compose", "-f", "docker-compose.production.yml", "down", "--remove-orphans"],
        "Remove stale containers and networks",
        check=False,  # Don't fail if nothing to clean up
    )

    # Check if Flutter is available (check snap path explicitly)
    flutter_cmd = "flutter"
    if os.path.exists("/snap/bin/flutter"):
        flutter_cmd = "/snap/bin/flutter"
        print_info(f"Found Flutter at: {flutter_cmd}")
    
    try:
        # Use longer timeout in case SDK needs to download
        if VERBOSE:
            print_info(f"Checking Flutter with command: {flutter_cmd} --version")
        result = subprocess.run([flutter_cmd, "--version"], capture_output=True, timeout=600, check=True, text=True)
        has_flutter = True
        if VERBOSE and result.stdout:
            print(f"Flutter output:\n{result.stdout}")
        print_success(f"Flutter detected: {result.stdout.splitlines()[0] if result.stdout else 'version unknown'}")
    except subprocess.TimeoutExpired:
        print_error("Flutter SDK download timed out")
        print_warning("Skipping frontend build.")
        has_flutter = False
    except Exception as e:
        if VERBOSE:
            import traceback
            print(f"Flutter check exception details:\n{traceback.format_exc()}")
        print_warning(f"Flutter not available: {e}")
        print_warning("Skipping frontend build.")
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
                [flutter_cmd, "pub", "get"],
                "Get Flutter dependencies",
                cwd=frontend_dir,
            ):
                print_warning("Failed to get Flutter dependencies. Continuing anyway...")
            
            # Check for outdated packages
            run_command(
                [flutter_cmd, "pub", "outdated"],
                "Check for outdated Flutter packages",
                cwd=frontend_dir,
                check=False,  # Don't fail on outdated packages
            )
            
            # Build for web with --no-wasm-dry-run to skip WebAssembly compatibility warnings
            if not run_command(
                [flutter_cmd, "build", "web", "--release", "--no-wasm-dry-run"],
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

    # Clean up any stale backend/static directory that might interfere with Flutter build
    backend_static = Path("backend/static")
    if backend_static.exists():
        print_info("Removing stale backend/static directory...")
        import shutil
        shutil.rmtree(backend_static)
    
    # Build production image with verbose output when VERBOSE flag is set
    # Always use --no-cache to ensure Flutter build files are properly copied
    docker_build_cmd = ["docker", "build", "--no-cache", "-f", "Dockerfile.production", "-t", "network-scanner:latest"]
    if VERBOSE:
        docker_build_cmd.append("--progress=plain")
    docker_build_cmd.append(".")
    
    if not run_command(
        docker_build_cmd,
        "Build production Docker image",
    ):
        return False

    print_success("Docker image built successfully")
    print_info("\nTo run the container:")
    print("  docker compose -f docker-compose.production.yml up -d")
    print("\nOr use docker compose for development:")
    print("  docker compose up -d")

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


def install_tools_only():
    """Install required and optional tools only."""
    print_header("Installing Tools")
    return check_prerequisites(auto_install=True)


# Global verbose flag
VERBOSE = False

def main():
    """Main entry point."""
    global VERBOSE
    
    parser = argparse.ArgumentParser(
        description="Network Scanner Setup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup.py dev              # Set up development environment (auto-installs tools)
  python3 setup.py dev -v           # Set up with verbose output
  python3 setup.py install-tools    # Install missing tools only
  python3 setup.py install-tools -v # Install tools with verbose output
  python3 setup.py service          # Install as system service
  python3 setup.py docker           # Build Docker containers
  python3 setup.py docker -v        # Build Docker containers with verbose output
  python3 setup.py clean            # Clean up artifacts
  python3 setup.py test             # Run tests
  python3 setup.py test -v          # Run tests with verbose output
        """,
    )

    parser.add_argument(
        "command",
        choices=["dev", "install-tools", "service", "docker", "clean", "test"],
        help="Setup command to execute",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()
    
    # Set global verbose flag
    VERBOSE = args.verbose

    print_header("Network Scanner Setup")
    print_info(f"Platform: {platform.system()} {platform.release()}")
    print_info(f"Python: {sys.version.split()[0]}")
    if VERBOSE:
        print_info("Verbose mode enabled")

    if args.command == "dev":
        success = setup_dev_environment()
    elif args.command == "install-tools":
        success = install_tools_only()
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
