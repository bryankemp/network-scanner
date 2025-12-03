"""
Unit tests for MCP server start_scan tool and stuck scan monitoring.

Tests MCP scan initiation, status reporting, and automatic stuck scan detection/recovery.
Author: Bryan Kemp <bryan@kempville.com>
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add mcp_server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp_server'))

from app.models import Scan, Host, ScanStatus, HostScanStatus
from app.scanner.stuck_scan_monitor import StuckScanMonitor


class TestMCPServerStartScan:
    """Tests for MCP server's start_scan tool."""

    def test_start_scan_creates_scan_record(self, db_session):
        """Test that start_scan creates a Scan database record."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("threading.Thread") as mock_thread:
            
            mock_get_db.return_value = db_session

            result = start_scan(networks=["192.168.1.0/24"])

            # Verify scan was created
            scan = db_session.query(Scan).first()
            assert scan is not None
            assert scan.network_range == "192.168.1.0/24"
            assert scan.status == ScanStatus.PENDING

    def test_start_scan_with_multiple_networks(self, db_session):
        """Test start_scan with multiple network ranges."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("threading.Thread") as mock_thread:
            
            mock_get_db.return_value = db_session

            result = start_scan(networks=["192.168.1.0/24", "10.0.0.0/24"])

            # Verify scan was created with both networks
            scan = db_session.query(Scan).first()
            assert scan is not None
            assert "192.168.1.0/24" in scan.network_range
            assert "10.0.0.0/24" in scan.network_range

    def test_start_scan_validates_cidr_format(self, db_session):
        """Test that start_scan validates CIDR network format."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db:
            mock_get_db.return_value = db_session

            # Invalid CIDR format
            result = start_scan(networks=["invalid-network"])

            # Should return error message
            assert "Invalid CIDR" in result

    def test_start_scan_auto_detects_network(self, db_session):
        """Test that start_scan auto-detects network when none provided."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("app.scanner.network_detection.detect_current_network") as mock_detect, \
             patch("threading.Thread") as mock_thread:
            
            mock_get_db.return_value = db_session
            mock_detect.return_value = "192.168.1.0/24"

            result = start_scan(networks=None)

            # Verify network was auto-detected
            scan = db_session.query(Scan).first()
            assert scan is not None
            assert "192.168.1.0/24" in scan.network_range

    def test_start_scan_handles_auto_detect_failure(self, db_session):
        """Test start_scan handles failure to auto-detect network."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("app.scanner.network_detection.detect_current_network") as mock_detect:
            
            mock_get_db.return_value = db_session
            mock_detect.return_value = None

            result = start_scan(networks=None)

            # Should return error about auto-detection
            assert "Could not auto-detect" in result

    def test_start_scan_starts_background_thread(self, db_session):
        """Test that start_scan initiates background scan thread."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("threading.Thread") as mock_thread:
            
            mock_get_db.return_value = db_session

            result = start_scan(networks=["192.168.1.0/24"])

            # Verify thread was created and started
            assert mock_thread.called
            thread_instance = mock_thread.return_value
            thread_instance.start.assert_called_once()

    def test_start_scan_returns_scan_info(self, db_session):
        """Test that start_scan returns scan ID and status information."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("threading.Thread") as mock_thread:
            
            mock_get_db.return_value = db_session

            result = start_scan(networks=["192.168.1.0/24"])

            # Verify result contains scan info
            assert "Scan ID:" in result
            assert "Networks:" in result
            assert "Status:" in result
            assert "get_scan_details" in result

    def test_start_scan_background_executes_orchestrator(self, db_session):
        """Test that background thread uses ScanOrchestrator."""
        from mcp_server.server import start_scan

        with patch("mcp_server.server.get_db") as mock_get_db, \
             patch("threading.Thread") as mock_thread, \
             patch("app.scanner.orchestrator.ScanOrchestrator") as mock_orchestrator_class:
            
            mock_get_db.return_value = db_session
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Get the background function that would be called
            result = start_scan(networks=["192.168.1.0/24"])
            
            # Verify thread would execute with scan
            assert mock_thread.called


class TestStuckScanMonitor:
    """Tests for stuck scan detection and recovery."""

    def test_diagnose_stuck_scan_basic_info(self, db_session):
        """Test that diagnose_stuck_scan returns basic scan diagnostics."""
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=2),
            progress_percent=50,
            progress_message="Scanning hosts...",
        )
        db_session.add(scan)
        db_session.commit()

        diagnostics = StuckScanMonitor.diagnose_stuck_scan(db_session, scan)

        assert diagnostics["scan_id"] == scan.id
        assert diagnostics["status"] == "running"
        assert diagnostics["progress_percent"] == 50
        assert "issues" in diagnostics

    def test_diagnose_detects_runtime_exceeded(self, db_session):
        """Test that diagnose detects scans exceeding maximum runtime."""
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=10),  # Over 6 hour limit
            progress_percent=50,
        )
        db_session.add(scan)
        db_session.commit()

        diagnostics = StuckScanMonitor.diagnose_stuck_scan(db_session, scan)

        assert diagnostics["runtime_hours"] > StuckScanMonitor.MAX_SCAN_TIME_HOURS
        assert len(diagnostics["issues"]) > 0

    def test_diagnose_identifies_stuck_hosts(self, db_session):
        """Test that diagnose identifies hosts stuck in SCANNING state."""
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db_session.add(scan)
        db_session.commit()

        # Add stuck host
        stuck_host = Host(
            scan_id=scan.id,
            ip="192.168.1.100",
            scan_status=HostScanStatus.SCANNING,
            scan_started_at=datetime.utcnow() - timedelta(minutes=15),
        )
        db_session.add(stuck_host)
        db_session.commit()

        diagnostics = StuckScanMonitor.diagnose_stuck_scan(db_session, scan)

        assert "stuck_scanning_hosts" in diagnostics
        assert len(diagnostics["stuck_scanning_hosts"]) == 1
        assert diagnostics["stuck_scanning_hosts"][0]["ip"] == "192.168.1.100"

    def test_diagnose_reports_host_status_breakdown(self, db_session):
        """Test that diagnose reports breakdown of host statuses."""
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db_session.add(scan)
        db_session.commit()

        # Add hosts with various statuses
        hosts = [
            Host(scan_id=scan.id, ip=f"192.168.1.{i}", scan_status=status)
            for i, status in enumerate(
                [
                    HostScanStatus.PENDING,
                    HostScanStatus.SCANNING,
                    HostScanStatus.COMPLETED,
                    HostScanStatus.FAILED,
                ],
                100,
            )
        ]
        for host in hosts:
            db_session.add(host)
        db_session.commit()

        diagnostics = StuckScanMonitor.diagnose_stuck_scan(db_session, scan)

        assert diagnostics["total_hosts"] == 4
        assert diagnostics["pending_hosts"] == 1
        assert diagnostics["scanning_hosts"] == 1
        assert diagnostics["completed_hosts"] == 1
        assert diagnostics["failed_hosts"] == 1

    def test_check_and_fix_marks_old_scans_failed(self, db_session):
        """Test that check_and_fix marks scans exceeding runtime limit as failed."""
        # Create scan that started 10 hours ago
        old_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=10),
            progress_percent=30,
        )
        db_session.add(old_scan)
        db_session.commit()

        fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

        assert fixed_count == 1

        # Refresh and verify scan was marked as failed
        db_session.refresh(old_scan)
        assert old_scan.status == ScanStatus.FAILED
        assert old_scan.completed_at is not None
        assert "timeout" in old_scan.error_message.lower()

    def test_check_and_fix_marks_stalled_scans_failed(self, db_session):
        """Test that check_and_fix marks scans with no progress updates as failed."""
        # Create scan with old updated_at timestamp
        stalled_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=1),
            updated_at=datetime.utcnow() - timedelta(minutes=45),  # Over 30 min limit
            progress_percent=20,
        )
        db_session.add(stalled_scan)
        db_session.commit()

        fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

        assert fixed_count == 1

        # Verify scan was marked as failed
        db_session.refresh(stalled_scan)
        assert stalled_scan.status == ScanStatus.FAILED

    def test_check_and_fix_marks_pending_timeout_failed(self, db_session):
        """Test that check_and_fix marks pending scans stuck for >1 hour as failed."""
        # Create pending scan older than 1 hour
        stuck_pending = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(hours=2),
            progress_percent=0,
        )
        db_session.add(stuck_pending)
        db_session.commit()

        fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

        assert fixed_count == 1

        # Verify scan was marked as failed
        db_session.refresh(stuck_pending)
        assert stuck_pending.status == ScanStatus.FAILED

    def test_check_and_fix_ignores_completed_scans(self, db_session):
        """Test that check_and_fix ignores completed scans."""
        completed_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(hours=10),
            completed_at=datetime.utcnow() - timedelta(hours=9),
            progress_percent=100,
        )
        db_session.add(completed_scan)
        db_session.commit()

        fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

        # Should not mark completed scan as failed
        assert fixed_count == 0
        db_session.refresh(completed_scan)
        assert completed_scan.status == ScanStatus.COMPLETED

    def test_check_and_fix_ignores_recent_scans(self, db_session):
        """Test that check_and_fix ignores recently started scans."""
        recent_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            updated_at=datetime.utcnow() - timedelta(minutes=2),
            progress_percent=10,
        )
        db_session.add(recent_scan)
        db_session.commit()

        fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

        # Should not mark recent scan as stuck
        assert fixed_count == 0
        db_session.refresh(recent_scan)
        assert recent_scan.status == ScanStatus.RUNNING

    def test_check_and_fix_kills_nmap_processes(self, db_session):
        """Test that check_and_fix attempts to kill associated nmap processes."""
        stuck_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=10),
            progress_percent=50,
        )
        db_session.add(stuck_scan)
        db_session.commit()

        with patch.object(StuckScanMonitor, "kill_nmap_processes") as mock_kill:
            mock_kill.return_value = 2  # Mock killing 2 processes

            fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

            # Verify kill_nmap_processes was called
            mock_kill.assert_called_once_with(stuck_scan.id)

    def test_check_and_fix_includes_diagnostics_in_error(self, db_session):
        """Test that error message includes diagnostic information."""
        stuck_scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(hours=10),
            progress_percent=50,
        )
        db_session.add(stuck_scan)
        db_session.commit()

        with patch.object(StuckScanMonitor, "kill_nmap_processes") as mock_kill:
            mock_kill.return_value = 0

            fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

            # Verify error message includes diagnostic info
            db_session.refresh(stuck_scan)
            assert "timeout" in stuck_scan.error_message.lower()
            assert "Issues:" in stuck_scan.error_message

    def test_kill_nmap_processes_finds_scan_processes(self):
        """Test that kill_nmap_processes identifies nmap processes for scan."""
        with patch("psutil.process_iter") as mock_iter:
            # Mock nmap process for scan ID 123
            mock_process = Mock()
            mock_process.info = {
                "pid": 12345,
                "name": "nmap",
                "cmdline": ["nmap", "-o", "/tmp/scan_123_discovery.xml"],
                "create_time": 1000000,
            }
            mock_iter.return_value = [mock_process]

            with patch("psutil.time.time", return_value=1001000):
                processes = StuckScanMonitor._find_nmap_processes(scan_id=123)

                assert len(processes) == 1
                assert processes[0]["pid"] == 12345

    def test_kill_nmap_processes_terminates_gracefully(self):
        """Test that kill_nmap_processes tries graceful termination first."""
        with patch.object(StuckScanMonitor, "_find_nmap_processes") as mock_find, \
             patch("psutil.Process") as mock_process_class:
            
            mock_find.return_value = [{"pid": 12345, "cmdline": "nmap scan_123"}]
            mock_process = Mock()
            mock_process_class.return_value = mock_process

            killed = StuckScanMonitor.kill_nmap_processes(scan_id=123)

            # Verify terminate was called first
            mock_process.terminate.assert_called_once()

    def test_kill_nmap_processes_force_kills_if_needed(self):
        """Test that kill_nmap_processes force kills if termination fails."""
        import psutil

        with patch.object(StuckScanMonitor, "_find_nmap_processes") as mock_find, \
             patch("psutil.Process") as mock_process_class:
            
            mock_find.return_value = [{"pid": 12345, "cmdline": "nmap scan_123"}]
            mock_process = Mock()
            mock_process.wait.side_effect = psutil.TimeoutExpired(5)
            mock_process_class.return_value = mock_process

            killed = StuckScanMonitor.kill_nmap_processes(scan_id=123)

            # Verify kill was called after timeout
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()


class TestMonitoringIntegration:
    """Integration tests for scan monitoring."""

    def test_monitor_detects_and_fixes_multiple_stuck_scans(self, db_session):
        """Test that monitor can detect and fix multiple stuck scans at once."""
        # Create multiple stuck scans
        stuck_scans = []
        for i in range(3):
            scan = Scan(
                network_range=f"192.168.{i}.0/24",
                status=ScanStatus.RUNNING,
                started_at=datetime.utcnow() - timedelta(hours=10),
                progress_percent=30 + i * 10,
            )
            db_session.add(scan)
            stuck_scans.append(scan)
        db_session.commit()

        with patch.object(StuckScanMonitor, "kill_nmap_processes") as mock_kill:
            mock_kill.return_value = 0

            fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db_session)

            assert fixed_count == 3

            # Verify all were marked as failed
            for scan in stuck_scans:
                db_session.refresh(scan)
                assert scan.status == ScanStatus.FAILED

    def test_monitor_scheduled_job_runs_periodically(self):
        """Test that stuck scan monitor is scheduled to run periodically."""
        from app.scheduler.scheduler import SchedulerService

        scheduler = SchedulerService()
        scheduler.start()

        try:
            # Verify stuck scan monitor job was added
            jobs = scheduler.scheduler.get_jobs()
            monitor_job = next((j for j in jobs if j.id == "stuck_scan_monitor"), None)

            assert monitor_job is not None
            assert monitor_job.name == "Stuck Scan Monitor"
        finally:
            scheduler.stop()
