"""
Simplified scan orchestrator for MVP.
Coordinates scan execution, parsing, and database persistence.
"""

from typing import Callable, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .nmap_runner import NmapRunner
from .parser import parse_nmap_xml, detect_enhanced_vm
from .report_gen import generate_html_report, generate_xlsx_report, generate_graphviz_diagram
from ..models import Scan, Host, Port, Artifact, ScanStatus, ArtifactType, HostScanStatus
from ..config import settings
from ..database import SessionLocal


class ScanOrchestrator:
    """Orchestrate complete scan workflow."""

    def __init__(self, db: Session):
        self.db = db
        self.nmap_runner = NmapRunner(output_dir=settings.scan_output_dir)

    def execute_scan(
        self,
        scan_id: int,
        networks: list,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Scan:
        """
        Execute complete scan workflow.

        Args:
            scan_id: Database scan ID
            networks: List of networks in CIDR format to scan
            progress_callback: Optional progress callback

        Returns:
            Updated Scan object
        """
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        try:
            # Update scan status
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.utcnow()
            scan.progress_percent = 0
            scan.progress_message = "Starting scan..."
            self.db.commit()

            # Process all networks
            all_live_ips = []
            all_discovery_xmls = []

            # Two-step: discovery + parallel per-host scans
            # Step 1: fast discovery across all networks
            scan.progress_message = f"Discovering hosts in {len(networks)} network(s)..."
            self.db.commit()

            for idx, network in enumerate(networks):
                progress_base = int((idx / len(networks)) * 15)  # 0-15% for discovery
                scan.progress_percent = progress_base
                scan.progress_message = f"Discovering hosts in {network}..."
                self.db.commit()

                discovery_xml, live_ips = self.nmap_runner.discover_hosts(
                    network_range=network,
                    scan_id=scan_id,
                    progress_callback=None,  # We handle progress manually
                )
                all_discovery_xmls.append(discovery_xml)
                all_live_ips.extend(live_ips)

            if not all_live_ips:
                scan.progress_message = "No live hosts discovered"
                scan.progress_percent = 100
                scan.status = ScanStatus.COMPLETED
                scan.completed_at = datetime.utcnow()
                self.db.commit()
                return scan

            # Create host records immediately with PENDING status
            from ..models import HostScanStatus

            scan.progress_percent = 18
            scan.progress_message = (
                f"Creating host records for {len(all_live_ips)} discovered host(s)..."
            )
            self.db.commit()

            host_records = {}
            for ip in all_live_ips:
                host = Host(
                    scan_id=scan.id,
                    ip=ip,
                    scan_status=HostScanStatus.PENDING,
                    scan_progress_percent=0,
                )
                self.db.add(host)
                host_records[ip] = host
            self.db.commit()

            # Step 2: parallel per-host comprehensive scans
            scan.progress_percent = 20
            scan.progress_message = f"Starting detailed scans on {len(all_live_ips)} host(s)..."
            self.db.commit()

            per_host_xmls = self._run_parallel_host_scans(scan, all_live_ips, scan_id, host_records)

            # Parse results from all XMLs
            scan.progress_percent = 50
            scan.progress_message = "Parsing scan results..."
            self.db.commit()

            hosts_data = []
            for xml_path in all_discovery_xmls + per_host_xmls:
                hosts_data.extend(parse_nmap_xml(xml_path))

            # Deduplicate hosts by IP (keep the one with most ports - from detailed scan)
            hosts_by_ip = {}
            for host_data in hosts_data:
                ip = host_data.get("ip")
                if ip:
                    # Keep host with more ports (detailed scan) or first if equal
                    if ip not in hosts_by_ip or len(host_data.get("ports", [])) > len(
                        hosts_by_ip[ip].get("ports", [])
                    ):
                        hosts_by_ip[ip] = host_data

            # Convert back to list
            hosts_data = list(hosts_by_ip.values())

            # Enhanced VM detection
            for host_data in hosts_data:
                detect_enhanced_vm(host_data)

            # Filter out false positives - only keep hosts with actual data
            # Definition of "actual data":
            # - at least one open port OR
            # - OS info present OR
            # - MAC address present
            # Note: hostname alone is NOT sufficient (drop DNS-only entries)
            filtered_hosts = []
            for host_data in hosts_data:
                has_data = (
                    len(host_data.get("ports", [])) > 0
                    or bool(host_data.get("os"))
                    or bool(host_data.get("mac"))
                )
                if has_data:
                    filtered_hosts.append(host_data)

            # Remove any pre-created Host rows that didn't pass the filter
            from ..models import Host as HostModel

            filtered_ips = {h.get("ip") for h in filtered_hosts if h.get("ip")}
            if filtered_ips:
                stale_hosts = (
                    self.db.query(HostModel)
                    .filter(HostModel.scan_id == scan.id, ~HostModel.ip.in_(list(filtered_ips)))
                    .all()
                )
                for stale in stale_hosts:
                    self.db.delete(stale)
                if stale_hosts:
                    print(f"Removed {len(stale_hosts)} host records with no meaningful data")

            hosts_data = filtered_hosts

            # Save to database
            scan.progress_percent = 60
            scan.progress_message = "Saving to database..."
            self.db.commit()

            self._save_hosts_to_db(scan, hosts_data)

            # Generate reports
            scan.progress_percent = 70
            scan.progress_message = "Generating reports..."
            self.db.commit()

            output_base = f"{settings.scan_output_dir}/scan_{scan_id}"

            # HTML report
            html_file = generate_html_report(hosts_data, f"{output_base}.html")
            self._save_artifact(scan, ArtifactType.HTML, html_file)

            # Excel report
            xlsx_file = generate_xlsx_report(hosts_data, f"{output_base}.xlsx")
            self._save_artifact(scan, ArtifactType.XLSX, xlsx_file)

            # Network diagram
            dot_file, png_file, svg_file = generate_graphviz_diagram(hosts_data, output_base)
            if dot_file:
                self._save_artifact(scan, ArtifactType.DOT, dot_file)
            if png_file:
                self._save_artifact(scan, ArtifactType.PNG, png_file)
            if svg_file:
                self._save_artifact(scan, ArtifactType.SVG, svg_file)

            # Save all discovery XMLs
            for xml_path in all_discovery_xmls:
                self._save_artifact(scan, ArtifactType.XML, xml_path)

            # Complete scan
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.progress_percent = 100
            scan.progress_message = "Scan completed successfully"
            self.db.commit()

            return scan

        except Exception as e:
            scan.status = ScanStatus.FAILED
            scan.completed_at = datetime.utcnow()
            scan.error_message = str(e)
            scan.progress_message = f"Scan failed: {str(e)}"
            self.db.commit()
            raise

    def _create_db_progress_callback(
        self, scan: Scan, user_callback: Optional[Callable] = None
    ) -> Callable:
        """Wraps a callback to update DB progress."""

        def callback(percent: int, message: str):
            scan.progress_percent = percent
            scan.progress_message = message
            self.db.commit()
            if user_callback:
                user_callback(percent, message)

        return callback

    def _run_parallel_host_scans(
        self, scan: Scan, live_ips: list, scan_id: str, host_records: dict
    ) -> list:
        """Run detailed scans on live hosts in parallel with per-host progress tracking."""
        per_host_xmls = []
        total_hosts = len(live_ips)
        completed_hosts = 0

        def scan_single_host(ip: str):
            """Scan a single host and update its status. Each thread gets its own DB session."""
            # Create thread-local database session
            thread_db = SessionLocal()

            try:
                # Query host in thread-local session
                host = thread_db.query(Host).filter(Host.scan_id == scan.id, Host.ip == ip).first()

                if host:
                    # Mark as scanning
                    host.scan_status = HostScanStatus.SCANNING
                    host.scan_started_at = datetime.utcnow()
                    host.scan_progress_percent = 50
                    thread_db.commit()

                # Run the actual nmap scan
                xml_path = self.nmap_runner.run_host_scan(ip, scan_id)

                # Parse the scan results immediately to get host details
                try:
                    parsed_hosts = parse_nmap_xml(xml_path)
                    if parsed_hosts:
                        host_data = parsed_hosts[0]  # Should only be one host
                        detect_enhanced_vm(host_data)

                        # Re-query to get latest state
                        host = (
                            thread_db.query(Host)
                            .filter(Host.scan_id == scan.id, Host.ip == ip)
                            .first()
                        )

                        # Update host with discovered details
                        if host:
                            # Try to get hostname from nmap, fallback to DNS lookup
                            hostname = host_data.get("hostname")
                            if not hostname or not hostname.strip():
                                try:
                                    import socket

                                    hostname_result = socket.gethostbyaddr(ip)
                                    hostname = hostname_result[0] if hostname_result else None
                                except (socket.herror, socket.gaierror, socket.timeout):
                                    hostname = None

                            host.hostname = hostname
                            host.mac = host_data.get("mac")
                            host.vendor = host_data.get("vendor")
                            host.os = host_data.get("os")
                            host.os_accuracy = host_data.get("os_accuracy")
                            host.is_vm = host_data.get("is_vm", False)
                            host.vm_type = host_data.get("vm_type")
                            host.ports_discovered = len(host_data.get("ports", []))

                            # Mark as completed
                            host.scan_status = HostScanStatus.COMPLETED
                            host.scan_completed_at = datetime.utcnow()
                            host.scan_progress_percent = 100
                            thread_db.commit()
                except Exception as parse_error:
                    print(f"Warning: Failed to parse {ip} immediately: {parse_error}")
                    # Still mark as completed even if parsing failed
                    host = (
                        thread_db.query(Host).filter(Host.scan_id == scan.id, Host.ip == ip).first()
                    )
                    if host:
                        host.scan_status = HostScanStatus.COMPLETED
                        host.scan_completed_at = datetime.utcnow()
                        host.scan_progress_percent = 100
                        thread_db.commit()

                return xml_path

            except Exception as e:
                # Re-query to get latest state
                host = thread_db.query(Host).filter(Host.scan_id == scan.id, Host.ip == ip).first()

                # Mark as failed
                if host:
                    host.scan_status = HostScanStatus.FAILED
                    host.scan_completed_at = datetime.utcnow()
                    host.scan_error_message = str(e)
                    host.scan_progress_percent = 0
                    thread_db.commit()

                # Log the error but don't raise - let the scan continue with other hosts
                print(f"Error scanning host {ip}: {e}")
                return None
            finally:
                # Always close the thread-local session
                thread_db.close()

        with ThreadPoolExecutor(max_workers=settings.scan_parallelism) as executor:
            # Submit all host scan jobs
            future_to_ip = {executor.submit(scan_single_host, ip): ip for ip in live_ips}

            # Collect results as they complete
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    xml_path = future.result()
                    if xml_path:  # Only add if scan succeeded
                        per_host_xmls.append(xml_path)
                    completed_hosts += 1

                    # Progress: 20-90% during host scans
                    progress = 20 + int((completed_hosts / total_hosts) * 70)
                    scan.progress_message = f"Completed {completed_hosts}/{total_hosts} hosts"
                    scan.progress_percent = progress
                    self.db.commit()
                except Exception as e:
                    print(f"Error scanning host {ip}: {e}")
                    completed_hosts += 1  # Still count as processed
                    # Continue with other hosts even if one fails

        return per_host_xmls

    def _save_hosts_to_db(self, scan: Scan, hosts_data: list):
        """Update existing host records with parsed scan data."""
        from ..models import TracerouteHop

        for host_data in hosts_data:
            ip = host_data.get("ip", "")

            # Find existing host record
            host = self.db.query(Host).filter(Host.scan_id == scan.id, Host.ip == ip).first()

            if not host:
                # Create new host if not found (shouldn't happen normally)
                host = Host(scan_id=scan.id, ip=ip)
                self.db.add(host)

            # Update host with scan results
            host.hostname = host_data.get("hostname")
            host.mac = host_data.get("mac")
            host.vendor = host_data.get("vendor")
            host.os = host_data.get("os")
            host.os_accuracy = host_data.get("os_accuracy")
            host.is_vm = host_data.get("is_vm", False)
            host.vm_type = host_data.get("vm_type")
            host.uptime_seconds = host_data.get("uptime_seconds")
            host.last_boot = host_data.get("last_boot")
            host.distance = host_data.get("distance")
            host.cpe = host_data.get("cpe")
            host.ports_discovered = len(host_data.get("ports", []))

            self.db.flush()  # Get host.id

            # Save traceroute hops
            for hop_data in host_data.get("traceroute", []):
                hop = TracerouteHop(
                    host_id=host.id,
                    hop_number=hop_data.get("ttl"),
                    ip=hop_data.get("ip"),
                    hostname=hop_data.get("hostname"),
                    rtt=hop_data.get("rtt"),
                )
                self.db.add(hop)

            # Save ports
            for port_data in host_data.get("ports", []):
                port = Port(
                    host_id=host.id,
                    port=int(port_data.get("port", 0)),
                    protocol=port_data.get("protocol", ""),
                    service=port_data.get("service"),
                    product=port_data.get("product"),
                    version=port_data.get("version"),
                    extrainfo=port_data.get("extrainfo"),
                    cpe=port_data.get("cpe"),
                    script_output=port_data.get("script_output"),
                )
                self.db.add(port)

        self.db.commit()

    def _save_artifact(self, scan: Scan, artifact_type: ArtifactType, file_path: str):
        """Save artifact to database."""
        import os

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

        artifact = Artifact(
            scan_id=scan.id, type=artifact_type, file_path=file_path, file_size=file_size
        )
        self.db.add(artifact)
        self.db.commit()
