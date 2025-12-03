#!/usr/bin/env python3
"""
Network Scanner MCP Server (v2)
Modern implementation using FastMCP following the official MCP specification.

Provides AI assistants with tools to query network scan data through a clean,
standardized Model Context Protocol interface.
"""
import os
import sys
from typing import Any
from datetime import datetime, timedelta

# Add backend to path for model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

# Import models
from app.models import (
    Scan, Host, Port, Artifact, TracerouteHop,
    ScanStatus, HostScanStatus, ArtifactType
)
from app.config import settings

# Database setup
db_url = os.environ.get("DATABASE_URL", settings.database_url)

# Ensure absolute path for sqlite URLs
if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    try:
        from pathlib import Path
        if db_url.startswith("sqlite:///./"):
            # Get the actual project root directory
            project_root = Path(__file__).parent.parent
            db_path = project_root / db_url.split("sqlite:///./", 1)[1]
            db_url = f"sqlite:///{db_path.as_posix()}"
    except Exception:
        pass

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize FastMCP server
mcp = FastMCP(name="network-scanner")


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


# ========== TOOLS ==========

@mcp.tool()
def list_scans(
    status: str | None = None,
    limit: int = 10
) -> str:
    """List all network scans with optional filtering by status.
    
    Args:
        status: Filter by scan status (pending, running, completed, failed, cancelled)
        limit: Maximum number of scans to return (default: 10)
    
    Returns:
        Formatted list of scans with their details
    """
    db = get_db()
    try:
        query = db.query(Scan)
        
        if status:
            try:
                status_enum = ScanStatus(status.lower())
                query = query.filter(Scan.status == status_enum)
            except ValueError:
                return f"Invalid status: {status}. Valid options: pending, running, completed, failed, cancelled"
        
        scans = query.order_by(Scan.created_at.desc()).limit(limit).all()
        
        if not scans:
            return "No scans found."
        
        result = f"Found {len(scans)} scan(s):\n\n"
        
        for scan in scans:
            result += f"Scan ID: {scan.id}\n"
            result += f"  Network: {scan.network_range}\n"
            result += f"  Status: {scan.status.value}\n"
            result += f"  Created: {scan.created_at}\n"
            
            if scan.started_at:
                result += f"  Started: {scan.started_at}\n"
            if scan.completed_at:
                result += f"  Completed: {scan.completed_at}\n"
                duration = (scan.completed_at - scan.started_at).total_seconds()
                result += f"  Duration: {duration:.1f}s\n"
            if scan.progress_message:
                result += f"  Message: {scan.progress_message}\n"
            
            host_count = len(scan.hosts)
            result += f"  Hosts Found: {host_count}\n"
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_scan_details(scan_id: int) -> str:
    """Get detailed information about a specific scan including all discovered hosts.
    
    Args:
        scan_id: The ID of the scan to retrieve
    
    Returns:
        Detailed scan information with host summaries
    """
    db = get_db()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        
        if not scan:
            return f"Scan {scan_id} not found"
        
        result = f"Scan Details (ID: {scan.id})\n"
        result += "=" * 50 + "\n\n"
        result += f"Network Range: {scan.network_range}\n"
        result += f"Status: {scan.status.value}\n"
        result += f"Created: {scan.created_at}\n"
        
        if scan.started_at:
            result += f"Started: {scan.started_at}\n"
        if scan.completed_at:
            result += f"Completed: {scan.completed_at}\n"
            duration = (scan.completed_at - scan.started_at).total_seconds()
            result += f"Duration: {duration:.1f} seconds\n"
        
        if scan.error_message:
            result += f"Error: {scan.error_message}\n"
        
        result += f"\nHosts Discovered: {len(scan.hosts)}\n"
        result += "-" * 50 + "\n\n"
        
        for host in scan.hosts:
            result += f"Host: {host.ip}\n"
            if host.hostname:
                result += f"  Hostname: {host.hostname}\n"
            if host.mac:
                result += f"  MAC: {host.mac}\n"
            if host.vendor:
                result += f"  Vendor: {host.vendor}\n"
            if host.os:
                result += f"  OS: {host.os}\n"
            if host.is_vm:
                result += f"  VM Type: {host.vm_type}\n"
            
            if host.ports:
                result += f"  Open Ports: {len(host.ports)}\n"
                for port in host.ports[:5]:  # Show first 5 ports
                    result += f"    - {port.port}/{port.protocol}: {port.service or 'unknown'}\n"
                if len(host.ports) > 5:
                    result += f"    ... and {len(host.ports) - 5} more\n"
            
            result += "\n"
        
        # Show artifacts
        if scan.artifacts:
            result += f"\nAvailable Artifacts:\n"
            for artifact in scan.artifacts:
                result += f"  - {artifact.type.value}: {artifact.file_path}\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def query_hosts(
    ip: str | None = None,
    hostname: str | None = None,
    is_vm: bool | None = None,
    limit: int = 20
) -> str:
    """Search for hosts by IP address, hostname, or other properties.
    
    Args:
        ip: Filter by IP address (partial match supported)
        hostname: Filter by hostname (partial match supported)
        is_vm: Filter for VMs/containers only (true/false)
        limit: Maximum number of hosts to return (default: 20)
    
    Returns:
        List of matching hosts with their details
    """
    db = get_db()
    try:
        query = db.query(Host)
        
        if ip:
            query = query.filter(Host.ip.like(f"%{ip}%"))
        if hostname:
            query = query.filter(Host.hostname.like(f"%{hostname}%"))
        if is_vm is not None:
            query = query.filter(Host.is_vm == is_vm)
        
        hosts = query.limit(limit).all()
        
        if not hosts:
            return "No hosts found matching the criteria."
        
        result = f"Found {len(hosts)} host(s):\n\n"
        
        for host in hosts:
            result += f"Host ID: {host.id}\n"
            result += f"  IP: {host.ip}\n"
            if host.hostname:
                result += f"  Hostname: {host.hostname}\n"
            if host.mac:
                result += f"  MAC: {host.mac} ({host.vendor or 'unknown vendor'})\n"
            if host.os:
                result += f"  OS: {host.os}\n"
            if host.is_vm:
                result += f"  Type: Virtual Machine ({host.vm_type})\n"
            
            result += f"  Services: {len(host.ports)} open port(s)\n"
            result += f"  Scan ID: {host.scan_id}\n"
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_host_services(host_id: int) -> str:
    """Get all services (open ports) for a specific host.
    
    Args:
        host_id: The ID of the host
    
    Returns:
        Detailed list of all services running on the host
    """
    db = get_db()
    try:
        host = db.query(Host).filter(Host.id == host_id).first()
        
        if not host:
            return f"Host {host_id} not found"
        
        result = f"Services on {host.ip}"
        if host.hostname:
            result += f" ({host.hostname})"
        result += "\n" + "=" * 50 + "\n\n"
        
        if not host.ports:
            result += "No open ports detected.\n"
        else:
            result += f"Total Open Ports: {len(host.ports)}\n\n"
            
            for port in host.ports:
                result += f"Port {port.port}/{port.protocol}:\n"
                result += f"  Service: {port.service or 'unknown'}\n"
                if port.product:
                    result += f"  Product: {port.product}\n"
                if port.version:
                    result += f"  Version: {port.version}\n"
                if port.extrainfo:
                    result += f"  Info: {port.extrainfo}\n"
                result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_network_stats() -> str:
    """Get overall network statistics including total hosts, VMs, scans, etc.
    
    Returns:
        Summary statistics about all network scans
    """
    db = get_db()
    try:
        total_scans = db.query(func.count(Scan.id)).scalar() or 0
        total_hosts = db.query(func.count(Host.id)).scalar() or 0
        total_vms = db.query(func.count(Host.id)).filter(Host.is_vm == True).scalar() or 0
        total_services = db.query(func.count(Port.id)).scalar() or 0
        
        completed_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatus.COMPLETED).scalar() or 0
        failed_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatus.FAILED).scalar() or 0
        running_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatus.RUNNING).scalar() or 0
        
        # Recent scans (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_scans = db.query(func.count(Scan.id)).filter(Scan.created_at >= yesterday).scalar() or 0
        
        # Most common services
        top_services = db.query(
            Port.service,
            func.count(Port.id).label('count')
        ).filter(
            Port.service.isnot(None)
        ).group_by(Port.service).order_by(func.count(Port.id).desc()).limit(10).all()
        
        result = "Network Statistics\n"
        result += "=" * 50 + "\n\n"
        result += f"Total Scans: {total_scans}\n"
        result += f"  - Completed: {completed_scans}\n"
        result += f"  - Failed: {failed_scans}\n"
        result += f"  - Running: {running_scans}\n"
        result += f"  - Recent (24h): {recent_scans}\n\n"
        
        result += f"Total Hosts Discovered: {total_hosts}\n"
        if total_hosts > 0:
            vm_percent = (total_vms / total_hosts) * 100
            result += f"  - Virtual Machines: {total_vms} ({vm_percent:.1f}%)\n"
            result += f"  - Physical Devices: {total_hosts - total_vms}\n\n"
        else:
            result += "\n"
        
        result += f"Total Services: {total_services}\n\n"
        
        if top_services:
            result += "Most Common Services:\n"
            for service, count in top_services:
                result += f"  - {service}: {count} instance(s)\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def list_vms(
    vm_type: str | None = None,
    limit: int = 50
) -> str:
    """List all detected virtual machines and containers.
    
    Args:
        vm_type: Filter by VM type (e.g., VMware, Docker, LXC, VirtualBox)
        limit: Maximum number of VMs to return (default: 50)
    
    Returns:
        List of virtual machines grouped by type
    """
    db = get_db()
    try:
        query = db.query(Host).filter(Host.is_vm == True)
        
        if vm_type:
            query = query.filter(Host.vm_type.like(f"%{vm_type}%"))
        
        vms = query.limit(limit).all()
        
        if not vms:
            return "No virtual machines or containers found."
        
        result = f"Found {len(vms)} virtual machine(s)/container(s):\n\n"
        
        # Group by VM type
        by_type: dict[str, list] = {}
        for vm in vms:
            vm_type_key = vm.vm_type or "Unknown"
            if vm_type_key not in by_type:
                by_type[vm_type_key] = []
            by_type[vm_type_key].append(vm)
        
        for vm_type_key, vm_list in by_type.items():
            result += f"{vm_type_key} ({len(vm_list)}):\n"
            for vm in vm_list:
                result += f"  - {vm.ip}"
                if vm.hostname:
                    result += f" ({vm.hostname})"
                result += f" - {len(vm.ports)} service(s)\n"
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def search_service(
    service_name: str,
    port: int | None = None
) -> str:
    """Find all hosts running a specific service.
    
    Args:
        service_name: Service name to search for (e.g., ssh, http, https, mysql)
        port: Optional port number to filter by
    
    Returns:
        List of hosts running the specified service
    """
    db = get_db()
    try:
        query = db.query(Port).join(Host).filter(
            Port.service.like(f"%{service_name}%")
        )
        
        if port:
            query = query.filter(Port.port == port)
        
        ports = query.all()
        
        if not ports:
            return f"No hosts found running service '{service_name}'"
        
        # Group by host
        by_host: dict[int, dict[str, Any]] = {}
        for port_obj in ports:
            host = port_obj.host
            if host.id not in by_host:
                by_host[host.id] = {"host": host, "ports": []}
            by_host[host.id]["ports"].append(port_obj)
        
        result = f"Found '{service_name}' on {len(by_host)} host(s):\n\n"
        
        for host_data in by_host.values():
            host = host_data["host"]
            ports_list = host_data["ports"]
            
            result += f"Host: {host.ip}"
            if host.hostname:
                result += f" ({host.hostname})"
            result += "\n"
            
            for port_obj in ports_list:
                result += f"  Port {port_obj.port}/{port_obj.protocol}: {port_obj.service}"
                if port_obj.product:
                    result += f" - {port_obj.product}"
                if port_obj.version:
                    result += f" {port_obj.version}"
                result += "\n"
            
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_network_topology(host_id: int) -> str:
    """Get network topology and traceroute information for a host.
    
    Args:
        host_id: The ID of the host to get traceroute for
    
    Returns:
        Network topology information including traceroute hops
    """
    db = get_db()
    try:
        host = db.query(Host).filter(Host.id == host_id).first()
        
        if not host:
            return f"Host {host_id} not found"
        
        result = f"Network Topology for {host.ip}"
        if host.hostname:
            result += f" ({host.hostname})"
        result += "\n" + "=" * 50 + "\n\n"
        
        if host.distance:
            result += f"Network Distance: {host.distance} hop(s)\n\n"
        
        if host.uptime_seconds:
            days = host.uptime_seconds // 86400
            hours = (host.uptime_seconds % 86400) // 3600
            result += f"Uptime: {days} days, {hours} hours\n"
            if host.last_boot:
                result += f"Last Boot: {host.last_boot}\n"
            result += "\n"
        
        # Get traceroute hops
        hops = db.query(TracerouteHop).filter(
            TracerouteHop.host_id == host_id
        ).order_by(TracerouteHop.hop_number).all()
        
        if hops:
            result += "Traceroute Path:\n"
            result += "-" * 50 + "\n"
            for hop in hops:
                result += f"Hop {hop.hop_number}: {hop.ip}"
                if hop.hostname:
                    result += f" ({hop.hostname})"
                if hop.rtt:
                    result += f" - {hop.rtt:.2f}ms"
                result += "\n"
        else:
            result += "No traceroute data available.\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def start_scan(
    networks: list[str] | None = None
) -> str:
    """Start a new network scan.
    
    Args:
        networks: List of networks to scan in CIDR format (e.g., ["192.168.1.0/24"])
                  If omitted or empty, auto-detects current network.
    
    Returns:
        Scan ID and status information for the newly created scan
    """
    import ipaddress
    import threading
    
    db = get_db()
    try:
        # Validate networks if provided
        if networks:
            for network in networks:
                try:
                    ipaddress.ip_network(network, strict=False)
                except ValueError as e:
                    return f"Invalid CIDR network '{network}': {e}"
        
        # Auto-detect network if not specified
        if not networks or len(networks) == 0:
            from app.scanner.network_detection import detect_current_network
            detected_network = detect_current_network()
            if detected_network:
                networks = [detected_network]
            else:
                return "Error: Could not auto-detect network. Please specify networks manually (e.g., ['192.168.1.0/24'])"
        
        # Store networks as comma-separated string for display
        network_range = ", ".join(networks)
        
        # Create scan record
        scan = Scan(
            network_range=network_range,
            status=ScanStatus.PENDING,
            progress_percent=0,
            progress_message="Scan queued"
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        
        scan_id = scan.id
        
        # Execute scan in background thread
        def run_scan_background(scan_id: int, networks: list):
            """Background task to execute scan with its own database session."""
            from app.scanner.orchestrator import ScanOrchestrator
            db_bg = get_db()
            try:
                orchestrator = ScanOrchestrator(db_bg)
                orchestrator.execute_scan(scan_id, networks)
            except Exception as e:
                # Update scan with error
                scan_obj = db_bg.query(Scan).filter(Scan.id == scan_id).first()
                if scan_obj:
                    scan_obj.status = ScanStatus.FAILED
                    scan_obj.error_message = str(e)
                    db_bg.commit()
            finally:
                db_bg.close()
        
        thread = threading.Thread(target=run_scan_background, args=(scan_id, networks), daemon=True)
        thread.start()
        
        result = f"Scan started successfully!\n\n"
        result += f"Scan ID: {scan_id}\n"
        result += f"Networks: {network_range}\n"
        result += f"Status: {scan.status.value}\n"
        result += f"Progress: {scan.progress_percent}%\n"
        result += f"Message: {scan.progress_message}\n\n"
        result += f"Use 'get_scan_details({scan_id})' to check progress.\n"
        result += f"Use 'get_scan_progress({scan_id})' for detailed progress information."
        
        return result
    finally:
        db.close()


@mcp.tool()
def find_vulnerabilities(script_name: str | None = None) -> str:
    """Search for hosts with specific script results or vulnerabilities detected by NSE scripts.
    
    Args:
        script_name: NSE script name to search for (e.g., ssl-cert, http-title, banner)
    
    Returns:
        List of hosts with matching script results
    """
    import json
    
    db = get_db()
    try:
        # Query ports with script output
        ports = db.query(Port).join(Host).filter(
            Port.script_output.isnot(None)
        ).all()
        
        matching_results = []
        for port in ports:
            try:
                scripts = json.loads(port.script_output)
                if script_name:
                    # Filter by specific script
                    if script_name in scripts:
                        matching_results.append({
                            'host': port.host,
                            'port': port,
                            'script': script_name,
                            'output': scripts[script_name]
                        })
                else:
                    # Show all scripts
                    for script_id, output in scripts.items():
                        matching_results.append({
                            'host': port.host,
                            'port': port,
                            'script': script_id,
                            'output': output
                        })
            except (json.JSONDecodeError, TypeError):
                continue
        
        if not matching_results:
            msg = "No script results found"
            if script_name:
                msg += f" for '{script_name}'"
            return msg
        
        result = f"Found {len(matching_results)} script result(s)"
        if script_name:
            result += f" for '{script_name}'"
        result += ":\n\n"
        
        for item in matching_results[:20]:  # Limit to 20 results
            host = item['host']
            port = item['port']
            result += f"Host: {host.ip}"
            if host.hostname:
                result += f" ({host.hostname})"
            result += "\n"
            result += f"Port: {port.port}/{port.protocol} ({port.service})\n"
            result += f"Script: {item['script']}\n"
            output_preview = item['output'][:200]
            if len(item['output']) > 200:
                output_preview += "..."
            result += f"Output: {output_preview}\n\n"
        
        if len(matching_results) > 20:
            result += f"... and {len(matching_results) - 20} more results\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_scan_progress(scan_id: int) -> str:
    """Get detailed progress information for an in-progress scan, including per-host scan status.
    
    Args:
        scan_id: The ID of the scan to check progress for
    
    Returns:
        Detailed progress information including host-level status
    """
    db = get_db()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        
        if not scan:
            return f"Scan {scan_id} not found"
        
        result = f"Scan Progress (ID: {scan.id})\n"
        result += "=" * 50 + "\n\n"
        result += f"Status: {scan.status.value}\n"
        result += f"Progress: {scan.progress_percent}%\n"
        result += f"Message: {scan.progress_message}\n\n"
        
        # Count hosts by status
        hosts = scan.hosts
        total = len(hosts)
        
        if hosts and hasattr(hosts[0], 'scan_status'):
            pending = sum(1 for h in hosts if h.scan_status == HostScanStatus.PENDING)
            scanning = sum(1 for h in hosts if h.scan_status == HostScanStatus.SCANNING)
            completed = sum(1 for h in hosts if h.scan_status == HostScanStatus.COMPLETED)
            failed = sum(1 for h in hosts if h.scan_status == HostScanStatus.FAILED)
            
            result += "Host Status:\n"
            result += f"  Total: {total}\n"
            result += f"  Completed: {completed}\n"
            result += f"  Scanning: {scanning}\n"
            result += f"  Pending: {pending}\n"
            result += f"  Failed: {failed}\n\n"
            
            # Show currently scanning hosts
            if scanning > 0:
                result += "Currently Scanning:\n"
                result += "-" * 50 + "\n"
                for host in hosts:
                    if host.scan_status == HostScanStatus.SCANNING:
                        result += f"  {host.ip}"
                        if host.hostname:
                            result += f" ({host.hostname})"
                        if host.scan_started_at:
                            elapsed = (datetime.utcnow() - host.scan_started_at).total_seconds()
                            result += f" - {elapsed:.0f}s elapsed"
                        if host.ports_discovered:
                            result += f" - {host.ports_discovered} ports found"
                        result += "\n"
                result += "\n"
            
            # Show failed hosts
            if failed > 0:
                result += "Failed Hosts:\n"
                result += "-" * 50 + "\n"
                for host in hosts:
                    if host.scan_status == HostScanStatus.FAILED:
                        result += f"  {host.ip}"
                        if host.scan_error_message:
                            result += f" - {host.scan_error_message}"
                        result += "\n"
                result += "\n"
        else:
            result += f"Total Hosts: {total}\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def list_schedules(enabled_only: bool = False, limit: int = 20) -> str:
    """List all scheduled scans with next run times.
    
    Args:
        enabled_only: Only show enabled schedules (default: False)
        limit: Maximum number of schedules to return (default: 20)
    
    Returns:
        Formatted list of scheduled scans
    """
    from app.models import ScanSchedule
    
    db = get_db()
    try:
        query = db.query(ScanSchedule)
        
        if enabled_only:
            query = query.filter(ScanSchedule.enabled == True)
        
        schedules = query.order_by(ScanSchedule.next_run_at).limit(limit).all()
        
        if not schedules:
            return "No schedules found."
        
        result = f"Found {len(schedules)} schedule(s):\n\n"
        
        for schedule in schedules:
            result += f"Schedule ID: {schedule.id}\n"
            result += f"  Name: {schedule.name}\n"
            result += f"  Network Range: {schedule.network_range}\n"
            result += f"  Cron Expression: {schedule.cron_expression}\n"
            result += f"  Enabled: {'Yes' if schedule.enabled else 'No'}\n"
            
            if schedule.next_run_at:
                result += f"  Next Run: {schedule.next_run_at}\n"
            if schedule.last_run_at:
                result += f"  Last Run: {schedule.last_run_at}\n"
            
            result += f"  Created: {schedule.created_at}\n"
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_schedule_details(schedule_id: int) -> str:
    """Get details about a specific scan schedule.
    
    Args:
        schedule_id: The ID of the schedule to retrieve
    
    Returns:
        Detailed schedule information including recent scans
    """
    from app.models import ScanSchedule
    
    db = get_db()
    try:
        schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
        
        if not schedule:
            return f"Schedule {schedule_id} not found"
        
        result = f"Schedule Details (ID: {schedule.id})\n"
        result += "=" * 50 + "\n\n"
        result += f"Name: {schedule.name}\n"
        result += f"Network Range: {schedule.network_range}\n"
        result += f"Cron Expression: {schedule.cron_expression}\n"
        result += f"Enabled: {'Yes' if schedule.enabled else 'No'}\n\n"
        
        result += f"Timing:\n"
        result += f"  Created: {schedule.created_at}\n"
        if schedule.next_run_at:
            result += f"  Next Run: {schedule.next_run_at}\n"
        if schedule.last_run_at:
            result += f"  Last Run: {schedule.last_run_at}\n"
        result += "\n"
        
        # Get recent scans from this schedule
        recent_scans = db.query(Scan).filter(
            Scan.schedule_id == schedule_id
        ).order_by(Scan.created_at.desc()).limit(5).all()
        
        if recent_scans:
            result += f"Recent Scans ({len(recent_scans)}): \n"
            result += "-" * 50 + "\n"
            for scan in recent_scans:
                result += f"  Scan {scan.id}: {scan.status.value}"
                if scan.started_at:
                    result += f" - {scan.started_at}"
                if scan.error_message:
                    result += f" - Error: {scan.error_message[:50]}"
                result += "\n"
        else:
            result += "No scans have run yet for this schedule.\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def list_users() -> str:
    """List all users (usernames and roles only, no sensitive data).
    
    Returns:
        Formatted list of users with basic information
    """
    from app.models import User
    
    db = get_db()
    try:
        users = db.query(User).order_by(User.created_at).all()
        
        if not users:
            return "No users found."
        
        result = f"Found {len(users)} user(s):\n\n"
        
        for user in users:
            result += f"User ID: {user.id}\n"
            result += f"  Username: {user.username}\n"
            result += f"  Role: {user.role.value}\n"
            result += f"  Active: {'Yes' if user.is_active else 'No'}\n"
            
            if user.email:
                result += f"  Email: {user.email}\n"
            if user.full_name:
                result += f"  Full Name: {user.full_name}\n"
            
            result += f"  Created: {user.created_at}\n"
            if user.last_login:
                result += f"  Last Login: {user.last_login}\n"
            
            if user.must_change_password:
                result += f"  Status: Must change password\n"
            
            result += "\n"
        
        return result
    finally:
        db.close()


@mcp.tool()
def get_system_health() -> str:
    """Get system health including stuck scans, scheduler status, and resource usage.
    
    Returns:
        System health report with diagnostics
    """
    from app.models import ScanSchedule
    
    db = get_db()
    try:
        result = "System Health Report\n"
        result += "=" * 50 + "\n\n"
        
        # Check for stuck/long-running scans
        now = datetime.utcnow()
        stuck_threshold = now - timedelta(hours=6)
        
        stuck_scans = db.query(Scan).filter(
            Scan.status.in_([ScanStatus.RUNNING, ScanStatus.PENDING]),
            Scan.created_at < stuck_threshold
        ).all()
        
        if stuck_scans:
            result += f"⚠ WARNING: {len(stuck_scans)} potentially stuck scan(s):\n"
            for scan in stuck_scans:
                age_hours = (now - scan.created_at).total_seconds() / 3600
                result += f"  Scan {scan.id}: {scan.status.value} for {age_hours:.1f} hours\n"
            result += "\n"
        else:
            result += "✓ No stuck scans detected\n\n"
        
        # Check recent scans
        recent_threshold = now - timedelta(hours=24)
        recent_scans = db.query(Scan).filter(
            Scan.created_at >= recent_threshold
        ).all()
        
        if recent_scans:
            completed = sum(1 for s in recent_scans if s.status == ScanStatus.COMPLETED)
            failed = sum(1 for s in recent_scans if s.status == ScanStatus.FAILED)
            running = sum(1 for s in recent_scans if s.status == ScanStatus.RUNNING)
            
            result += "Last 24 Hours:\n"
            result += f"  Total Scans: {len(recent_scans)}\n"
            result += f"  Completed: {completed}\n"
            result += f"  Failed: {failed}\n"
            result += f"  Running: {running}\n\n"
        
        # Check schedules
        schedules = db.query(ScanSchedule).all()
        enabled_schedules = [s for s in schedules if s.enabled]
        
        result += "Schedules:\n"
        result += f"  Total: {len(schedules)}\n"
        result += f"  Enabled: {len(enabled_schedules)}\n"
        result += f"  Disabled: {len(schedules) - len(enabled_schedules)}\n\n"
        
        # Database stats
        total_scans = db.query(Scan).count()
        total_hosts = db.query(Host).count()
        total_vms = db.query(Host).filter(Host.is_vm == True).count()
        
        result += "Database Statistics:\n"
        result += f"  Total Scans: {total_scans}\n"
        result += f"  Total Hosts: {total_hosts}\n"
        result += f"  Total VMs: {total_vms}\n"
        
        # Overall health status
        result += "\n"
        if stuck_scans:
            result += "Overall Status: WARNING - Stuck scans detected\n"
        else:
            result += "Overall Status: HEALTHY\n"
        
        return result
    finally:
        db.close()


# ========== SERVER ENTRY POINT ==========

def main():
    """Run the MCP server with stdio transport."""
    # Run with stdio transport (default for Claude Desktop, Warp AI, etc.)
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
