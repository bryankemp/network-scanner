"""
nmap runner for executing network scans.
"""

import subprocess
import os
from typing import Optional, Callable, List, Tuple
import xml.etree.ElementTree as ET


class NmapRunner:
    """Execute nmap scans and manage output files."""

    def __init__(self, output_dir: str = "/tmp"):
        """
        Initialize nmap runner.

        Args:
            output_dir: Directory to store scan output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_scan(
        self,
        network_range: str,
        scan_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Run monolithic nmap scan on the specified network range.
        Prefer using discover_hosts + run_host_scan for faster parallel scans.

        Args:
            network_range: Network range to scan (e.g., "192.168.1.0/24")
            scan_id: Scan ID for output file naming
            progress_callback: Optional callback function(percent, message) for progress updates

        Returns:
            Path to the generated XML output file

        Raises:
            subprocess.CalledProcessError: If nmap command fails
            FileNotFoundError: If nmap is not installed
        """
        xml_output = os.path.join(self.output_dir, f"scan_{scan_id}.xml")

        # nmap command with comprehensive scanning
        # -sn: Host discovery only (faster)
        # -sV: Version detection
        # -O: OS detection
        # -T4: Aggressive timing
        # --privileged: Run with elevated privileges (required for some scans)

        if progress_callback:
            progress_callback(5, "Starting nmap scan...")

        # First, do a quick host discovery
        try:
            host_discovery_cmd = [
                "nmap",
                "-sn",  # Ping scan (no port scan)
                "-oX",
                xml_output,
                network_range,
            ]

            if progress_callback:
                progress_callback(10, "Discovering hosts...")

            subprocess.run(host_discovery_cmd, check=True, capture_output=True)

            if progress_callback:
                progress_callback(40, "Host discovery complete. Starting service scan...")

            # Now do comprehensive scan with service and OS detection
            comprehensive_cmd = [
                "nmap",
                "-sV",  # Service version detection
                "-O",  # OS detection
                "-T4",  # Aggressive timing
                "--traceroute",  # Enable traceroute
                "--script=banner,ssl-cert,http-title,http-headers",  # Useful NSE scripts
                "-oX",
                xml_output,
                network_range,
            ]

            if progress_callback:
                progress_callback(50, "Scanning services and OS...")

            # Run the comprehensive scan
            subprocess.run(comprehensive_cmd, check=True, capture_output=True, text=True)

            if progress_callback:
                progress_callback(90, "Scan complete, processing results...")

        except FileNotFoundError:
            raise FileNotFoundError(
                "nmap not found. Please install nmap: brew install nmap (macOS) or apt-get install nmap (Linux)"
            )
        except subprocess.CalledProcessError as e:
            error_msg = f"nmap scan failed: {e.stderr if e.stderr else str(e)}"
            if progress_callback:
                progress_callback(0, error_msg)
            raise subprocess.CalledProcessError(
                returncode=e.returncode, cmd=e.cmd, output=e.output, stderr=error_msg
            )

        if progress_callback:
            progress_callback(95, "Validating scan results...")

        # Verify output file was created
        if not os.path.exists(xml_output):
            raise FileNotFoundError(f"nmap output file not created: {xml_output}")

        if progress_callback:
            progress_callback(100, "Scan completed successfully")

        return xml_output

    def run_quick_scan(
        self,
        network_range: str,
        scan_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Run quick host discovery scan (no port scanning).

        Args:
            network_range: Network range to scan
            scan_id: Scan ID for output file naming
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the generated XML output file
        """
        xml_output = os.path.join(self.output_dir, f"scan_{scan_id}.xml")

        if progress_callback:
            progress_callback(10, "Starting quick host discovery...")

        cmd = ["nmap", "-sn", "-oX", xml_output, network_range]  # Ping scan only

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            if progress_callback:
                progress_callback(100, "Quick scan completed")

        except subprocess.CalledProcessError as e:
            error_msg = f"Quick scan failed: {e.stderr if e.stderr else str(e)}"
            if progress_callback:
                progress_callback(0, error_msg)
            raise

        return xml_output

    # New in parallel mode
    def discover_hosts(
        self,
        network_range: str,
        scan_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Run a fast discovery scan with top ports check to find truly responsive hosts.
        Returns list of up host IPs and xml path.
        """
        xml_output = os.path.join(self.output_dir, f"scan_{scan_id}_discovery.xml")
        # Use light port scan on top ports instead of just -sn (ping)
        # This gives more accurate results, especially from Docker environments
        # -F: Fast mode (100 most common ports)
        # --max-retries 1: Quick scan
        # --host-timeout 30s: Don't spend too long on any single host
        cmd = [
            "nmap",
            "-F",  # Fast scan (top 100 ports)
            "--max-retries",
            "1",
            "--host-timeout",
            "30s",
            "-T4",  # Aggressive timing
            "-oX",
            xml_output,
            network_range,
        ]
        if progress_callback:
            progress_callback(5, "Discovering live hosts...")
        subprocess.run(cmd, check=True, capture_output=True)
        if progress_callback:
            progress_callback(15, "Parsing discovery results...")
        # Parse XML for up hosts - only include hosts that have at least one open port or OS info
        ips: List[str] = []
        tree = ET.parse(xml_output)
        root = tree.getroot()
        for host in root.findall("host"):
            status = host.find("status")
            if status is not None and status.get("state") == "up":
                # Check if host has at least one open port or interesting data
                ports_elem = host.find("ports")
                has_open_port = False
                if ports_elem is not None:
                    for port in ports_elem.findall("port"):
                        port_state = port.find("state")
                        if port_state is not None and port_state.get("state") == "open":
                            has_open_port = True
                            break
                
                # Only add hosts with open ports (actual services)
                if has_open_port:
                    addr = host.find('address[@addrtype="ipv4"]')
                    if addr is not None:
                        ips.append(addr.get("addr"))
        return xml_output, ips

    def run_host_scan(self, ip: str, scan_id: int) -> str:
        """
        Run comprehensive scan against a single host IP. Returns xml path.
        Includes OS detection, hostname resolution, and MAC vendor lookup.

        Args:
            ip: IP address to scan
            scan_id: Scan ID for output file naming

        Returns:
            Path to the generated XML output file

        Raises:
            subprocess.TimeoutExpired: If scan takes longer than 5 minutes
            subprocess.CalledProcessError: If nmap fails
            FileNotFoundError: If nmap doesn't create output file
        """
        xml_output = os.path.join(self.output_dir, f"scan_{scan_id}_{ip.replace('.', '_')}.xml")
        comprehensive_cmd = [
            "nmap",
            "-sV",  # Service version detection
            "-O",  # OS detection (requires root/CAP_NET_RAW)
            "-R",  # Force DNS resolution for all targets
            "--osscan-guess",  # Guess OS more aggressively
            "-T4",  # Aggressive timing for faster scans
            "--version-intensity",
            "2",  # Lower intensity for faster version detection
            "--max-rtt-timeout",
            "200ms",  # Faster timeout
            "--max-retries",
            "1",  # Reduce retries
            "--min-rate",
            "100",  # Minimum packet rate
            "--max-os-tries",
            "1",  # Limit OS detection attempts for speed
            "--host-timeout",
            "240s",  # Kill scan if host takes > 4 minutes
            "-oX",
            xml_output,
            ip,
        ]

        try:
            # Add 5-minute timeout to subprocess call (includes nmap's 4-minute host-timeout plus overhead)
            subprocess.run(
                comprehensive_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes max
            )

            # Verify output file was created
            if not os.path.exists(xml_output):
                raise FileNotFoundError(f"nmap did not create output file: {xml_output}")

            return xml_output

        except subprocess.TimeoutExpired as e:
            # Clean up partial output file if it exists
            if os.path.exists(xml_output):
                os.remove(xml_output)
            raise subprocess.TimeoutExpired(
                cmd=e.cmd, timeout=e.timeout, output=f"Host scan timeout for {ip} after 5 minutes"
            )
        except subprocess.CalledProcessError as e:
            # Log the error details
            stderr = e.stderr if e.stderr else "No error output"
            raise subprocess.CalledProcessError(
                returncode=e.returncode,
                cmd=e.cmd,
                output=e.output,
                stderr=f"Host scan failed for {ip}: {stderr}",
            )

    def cleanup_scan_file(self, xml_file: str) -> None:
        """
        Remove temporary scan XML file.

        Args:
            xml_file: Path to XML file to remove
        """
        try:
            if os.path.exists(xml_file):
                os.remove(xml_file)
        except Exception as e:
            print(f"Warning: Failed to cleanup scan file {xml_file}: {e}")
