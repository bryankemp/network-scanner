"""
Monitor and fix stuck scans with diagnostic analysis.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
import logging
import psutil

from ..models import Scan, ScanStatus, Host, HostScanStatus

logger = logging.getLogger(__name__)


class StuckScanMonitor:
    """Monitor and detect stuck scans with root cause analysis."""

    # Maximum time a scan can run without updates
    MAX_SCAN_TIME_HOURS = 6

    # Maximum time a scan can be at the same progress without updates
    MAX_STALLED_TIME_MINUTES = 30

    @staticmethod
    def diagnose_stuck_scan(db: Session, scan: Scan) -> Dict:
        """
        Diagnose WHY a scan is stuck.

        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            "scan_id": scan.id,
            "status": scan.status.value,
            "progress_percent": scan.progress_percent,
            "progress_message": scan.progress_message,
            "issues": [],
        }

        # Check host-level status
        hosts = db.query(Host).filter(Host.scan_id == scan.id).all()
        if hosts:
            total_hosts = len(hosts)
            pending_hosts = [h for h in hosts if h.scan_status == HostScanStatus.PENDING]
            scanning_hosts = [h for h in hosts if h.scan_status == HostScanStatus.SCANNING]
            failed_hosts = [h for h in hosts if h.scan_status == HostScanStatus.FAILED]
            completed_hosts = [h for h in hosts if h.scan_status == HostScanStatus.COMPLETED]

            diagnostics["total_hosts"] = total_hosts
            diagnostics["pending_hosts"] = len(pending_hosts)
            diagnostics["scanning_hosts"] = len(scanning_hosts)
            diagnostics["failed_hosts"] = len(failed_hosts)
            diagnostics["completed_hosts"] = len(completed_hosts)

            # Identify which hosts are stuck scanning
            if scanning_hosts:
                now = datetime.utcnow()
                stuck_scanning = []
                for host in scanning_hosts:
                    if host.scan_started_at:
                        scan_duration = (now - host.scan_started_at).total_seconds() / 60
                        if scan_duration > 10:  # More than 10 minutes
                            stuck_scanning.append(
                                {
                                    "ip": host.ip,
                                    "duration_minutes": round(scan_duration, 1),
                                    "started_at": host.scan_started_at.isoformat(),
                                }
                            )

                if stuck_scanning:
                    diagnostics["stuck_scanning_hosts"] = stuck_scanning
                    diagnostics["issues"].append(
                        f"{len(stuck_scanning)} host(s) stuck in SCANNING state for >10 minutes"
                    )

        # Check for running nmap processes
        nmap_processes = StuckScanMonitor._find_nmap_processes(scan.id)
        if nmap_processes:
            diagnostics["nmap_processes"] = nmap_processes
            diagnostics["issues"].append(f"{len(nmap_processes)} nmap process(es) still running")

        # Check scan runtime
        if scan.started_at:
            runtime_hours = (datetime.utcnow() - scan.started_at).total_seconds() / 3600
            diagnostics["runtime_hours"] = round(runtime_hours, 2)
            if runtime_hours > StuckScanMonitor.MAX_SCAN_TIME_HOURS:
                diagnostics["issues"].append(
                    f"Total runtime {runtime_hours:.1f}h exceeds max {StuckScanMonitor.MAX_SCAN_TIME_HOURS}h"
                )

        return diagnostics

    @staticmethod
    def _find_nmap_processes(scan_id: int) -> List[Dict]:
        """
        Find running nmap processes for this scan.

        Returns:
            List of process info dictionaries
        """
        processes = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    if proc.info["name"] == "nmap":
                        cmdline = proc.info["cmdline"]
                        # Check if this nmap process is for our scan
                        if cmdline and any(f"scan_{scan_id}" in arg for arg in cmdline):
                            runtime_seconds = psutil.time.time() - proc.info["create_time"]
                            processes.append(
                                {
                                    "pid": proc.info["pid"],
                                    "cmdline": " ".join(cmdline) if cmdline else "",
                                    "runtime_seconds": round(runtime_seconds, 1),
                                }
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Error finding nmap processes: {e}")

        return processes

    @staticmethod
    def kill_nmap_processes(scan_id: int) -> int:
        """
        Kill all nmap processes for a scan.

        Returns:
            Number of processes killed
        """
        killed = 0
        processes = StuckScanMonitor._find_nmap_processes(scan_id)
        for proc_info in processes:
            try:
                proc = psutil.Process(proc_info["pid"])
                proc.terminate()  # Try graceful termination first
                try:
                    proc.wait(timeout=5)  # Wait up to 5 seconds
                except psutil.TimeoutExpired:
                    proc.kill()  # Force kill if needed
                logger.info(f"Killed nmap process {proc_info['pid']} for scan {scan_id}")
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not kill process {proc_info['pid']}: {e}")

        return killed

    @staticmethod
    def check_and_fix_stuck_scans(db: Session) -> int:
        """
        Check for stuck scans and mark them as failed with diagnostics.

        A scan is considered stuck if:
        1. Status is 'running' or 'pending'
        2. Started more than MAX_SCAN_TIME_HOURS ago
        3. No progress updates in MAX_STALLED_TIME_MINUTES

        Args:
            db: Database session

        Returns:
            Number of scans marked as failed
        """
        now = datetime.utcnow()
        fixed_count = 0

        # Find running or pending scans
        running_scans = (
            db.query(Scan).filter(Scan.status.in_([ScanStatus.RUNNING, ScanStatus.PENDING])).all()
        )

        for scan in running_scans:
            is_stuck = False
            reason = ""

            # Check 1: Total runtime exceeded
            if scan.started_at:
                runtime = now - scan.started_at
                if runtime > timedelta(hours=StuckScanMonitor.MAX_SCAN_TIME_HOURS):
                    is_stuck = True
                    hours = runtime.total_seconds() / 3600
                    reason = f"Scan exceeded maximum runtime ({hours:.1f} hours)"

            # Check 2: No progress updates (using updated_at from SQLAlchemy)
            # If scan has been updated recently, it's still alive
            if not is_stuck and hasattr(scan, "updated_at") and scan.updated_at:
                time_since_update = now - scan.updated_at
                if time_since_update > timedelta(minutes=StuckScanMonitor.MAX_STALLED_TIME_MINUTES):
                    is_stuck = True
                    minutes = time_since_update.total_seconds() / 60
                    reason = f"No progress for {minutes:.1f} minutes"

            # Check 3: Started long ago but never actually started
            if not is_stuck and scan.status == ScanStatus.PENDING:
                if scan.created_at:
                    age = now - scan.created_at
                    if age > timedelta(hours=1):
                        is_stuck = True
                        reason = "Scan stuck in pending state for over 1 hour"

            if is_stuck:
                # Run diagnostics to understand WHY it's stuck
                diagnostics = StuckScanMonitor.diagnose_stuck_scan(db, scan)
                logger.warning(f"Stuck scan diagnostics for scan #{scan.id}: {diagnostics}")

                # Kill any running nmap processes
                killed = StuckScanMonitor.kill_nmap_processes(scan.id)
                if killed > 0:
                    logger.info(f"Killed {killed} nmap process(es) for scan #{scan.id}")

                # Mark scan as failed with diagnostic info
                scan.status = ScanStatus.FAILED
                scan.completed_at = now
                scan.error_message = (
                    f"Scan timeout: {reason}. Issues: {', '.join(diagnostics['issues'])}"
                )
                fixed_count += 1

                logger.warning(f"Detected stuck scan {scan.id}: {reason}")

        if fixed_count > 0:
            db.commit()
            logger.info(f"Marked {fixed_count} stuck scan(s) as failed")

        return fixed_count
