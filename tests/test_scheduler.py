"""
Unit tests for scheduler service and scheduled scan functionality.

Tests schedule creation, updating, triggering, cron expression handling, and background execution.
Author: Bryan Kemp <bryan@kempville.com>
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from croniter import croniter

from app.scheduler.scheduler import SchedulerService, get_scheduler
from app.models import ScanSchedule, Scan, ScanStatus
from app.config import settings


class TestSchedulerService:
    """Tests for SchedulerService core functionality."""

    @pytest.fixture
    def scheduler_service(self):
        """Create a fresh scheduler service instance for testing."""
        service = SchedulerService()
        yield service
        # Cleanup - stop scheduler if running
        if service._running:
            service.stop()

    @pytest.fixture
    def sample_schedule(self, db_session):
        """Create a sample schedule for testing."""
        schedule = ScanSchedule(
            name="Daily Network Scan",
            network_range="192.168.1.0/24",
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        return schedule

    def test_scheduler_initialization(self, scheduler_service):
        """Test scheduler service initializes correctly."""
        assert scheduler_service.scheduler is not None
        assert scheduler_service._running is False
        assert scheduler_service._lock is not None

    def test_scheduler_start(self, scheduler_service):
        """Test starting the scheduler service."""
        with patch.object(scheduler_service, "load_schedules") as mock_load:
            scheduler_service.start()

            assert scheduler_service._running is True
            assert scheduler_service.scheduler.running is True
            mock_load.assert_called_once()

    def test_scheduler_start_idempotent(self, scheduler_service):
        """Test that calling start multiple times is safe."""
        scheduler_service.start()
        assert scheduler_service._running is True

        # Start again - should be idempotent
        scheduler_service.start()
        assert scheduler_service._running is True

    def test_scheduler_stop(self, scheduler_service):
        """Test stopping the scheduler service."""
        scheduler_service.start()
        assert scheduler_service._running is True

        scheduler_service.stop()
        assert scheduler_service._running is False
        assert scheduler_service.scheduler.running is False

    def test_scheduler_stop_idempotent(self, scheduler_service):
        """Test that calling stop multiple times is safe."""
        scheduler_service.start()
        scheduler_service.stop()
        assert scheduler_service._running is False

        # Stop again - should be idempotent
        scheduler_service.stop()
        assert scheduler_service._running is False

    def test_add_schedule_creates_job(self, scheduler_service, sample_schedule, db_session):
        """Test that adding a schedule creates an APScheduler job."""
        scheduler_service.start()

        with patch.object(scheduler_service.scheduler, "add_job") as mock_add_job:
            scheduler_service.add_schedule(sample_schedule.id)

            # Verify job was added
            assert mock_add_job.called
            call_args = mock_add_job.call_args
            assert call_args[1]["id"] == f"schedule_{sample_schedule.id}"
            assert call_args[1]["name"] == f"Scan: {sample_schedule.name}"

    def test_add_schedule_parses_cron_expression(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that cron expressions are correctly parsed."""
        scheduler_service.start()

        with patch.object(scheduler_service.scheduler, "add_job") as mock_add_job:
            scheduler_service.add_schedule(sample_schedule.id)

            # Verify CronTrigger was created with correct values
            assert mock_add_job.called
            trigger = mock_add_job.call_args[1]["trigger"]
            assert trigger is not None

    def test_add_schedule_disabled(self, scheduler_service, sample_schedule, db_session):
        """Test that disabled schedules are not added to scheduler."""
        sample_schedule.enabled = False
        db_session.commit()

        scheduler_service.start()

        with patch.object(scheduler_service.scheduler, "add_job") as mock_add_job:
            scheduler_service.add_schedule(sample_schedule.id)

            # Job should not be added for disabled schedule
            assert not mock_add_job.called

    def test_update_schedule_removes_and_adds_job(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that updating a schedule removes old job and adds new one."""
        scheduler_service.start()

        with patch.object(scheduler_service, "remove_schedule") as mock_remove, \
             patch.object(scheduler_service, "add_schedule") as mock_add:
            
            scheduler_service.update_schedule(sample_schedule.id)

            mock_remove.assert_called_once_with(sample_schedule.id)
            mock_add.assert_called_once_with(sample_schedule.id)

    def test_remove_schedule_deletes_job(self, scheduler_service, sample_schedule):
        """Test that removing a schedule deletes the APScheduler job."""
        scheduler_service.start()

        with patch.object(scheduler_service.scheduler, "remove_job") as mock_remove:
            scheduler_service.remove_schedule(sample_schedule.id)

            mock_remove.assert_called_once_with(f"schedule_{sample_schedule.id}")

    def test_trigger_schedule_executes_immediately(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test manually triggering a scheduled scan executes immediately."""
        scheduler_service.start()

        with patch.object(scheduler_service, "_execute_scheduled_scan") as mock_execute:
            scheduler_service.trigger_schedule(sample_schedule.id)

            # Verify scan was triggered
            mock_execute.assert_called_once_with(sample_schedule.id)

    def test_execute_scheduled_scan_creates_scan(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that executing a scheduled scan creates a Scan record."""
        with patch.object(scheduler_service, "_run_scan_background"):
            scheduler_service._execute_scheduled_scan(sample_schedule.id)

            # Verify scan was created
            scan = db_session.query(Scan).filter(Scan.schedule_id == sample_schedule.id).first()
            assert scan is not None
            assert scan.network_range == sample_schedule.network_range
            assert scan.status == ScanStatus.PENDING

            # Verify last_run_at was updated
            db_session.refresh(sample_schedule)
            assert sample_schedule.last_run_at is not None

    def test_execute_scheduled_scan_updates_next_run(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that executing updates next_run_at timestamp."""
        initial_next_run = sample_schedule.next_run_at

        with patch.object(scheduler_service, "_run_scan_background"):
            scheduler_service._execute_scheduled_scan(sample_schedule.id)

            # Refresh and verify next_run_at was updated
            db_session.refresh(sample_schedule)
            assert sample_schedule.next_run_at is not None

    def test_execute_scheduled_scan_starts_background_thread(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that scan execution starts a background thread."""
        with patch("threading.Thread") as mock_thread:
            scheduler_service._execute_scheduled_scan(sample_schedule.id)

            # Verify thread was created and started
            assert mock_thread.called
            thread_instance = mock_thread.return_value
            thread_instance.start.assert_called_once()

    def test_execute_scheduled_scan_ignores_disabled(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that disabled schedules are not executed."""
        sample_schedule.enabled = False
        db_session.commit()

        with patch.object(scheduler_service, "_run_scan_background") as mock_run:
            scheduler_service._execute_scheduled_scan(sample_schedule.id)

            # Scan should not be created or executed
            assert not mock_run.called

    def test_run_scan_background_executes_orchestrator(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that background scan execution uses ScanOrchestrator."""
        # Create a scan first
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.PENDING,
            schedule_id=sample_schedule.id,
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        with patch("app.scheduler.scheduler.ScanOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            scheduler_service._run_scan_background(scan.id, ["192.168.1.0/24"])

            # Verify orchestrator was used
            mock_orchestrator_class.assert_called_once()
            mock_orchestrator.execute_scan.assert_called_once_with(
                scan.id, ["192.168.1.0/24"]
            )

    def test_run_scan_background_handles_errors(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that background scan handles errors gracefully."""
        scan = Scan(
            network_range="192.168.1.0/24",
            status=ScanStatus.PENDING,
            schedule_id=sample_schedule.id,
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        with patch("app.scheduler.scheduler.ScanOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.execute_scan.side_effect = Exception("Network error")
            mock_orchestrator_class.return_value = mock_orchestrator

            # Should not raise exception
            scheduler_service._run_scan_background(scan.id, ["192.168.1.0/24"])

    def test_load_schedules_adds_enabled_schedules(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that load_schedules adds all enabled schedules."""
        # Create another schedule
        schedule2 = ScanSchedule(
            name="Weekly Scan",
            network_range="10.0.0.0/24",
            cron_expression="0 0 * * 0",  # Weekly on Sunday
            enabled=True,
        )
        db_session.add(schedule2)
        db_session.commit()

        with patch.object(scheduler_service, "_add_job") as mock_add_job:
            scheduler_service.load_schedules()

            # Should add both enabled schedules
            assert mock_add_job.call_count == 2

    def test_load_schedules_skips_disabled(
        self, scheduler_service, sample_schedule, db_session
    ):
        """Test that load_schedules skips disabled schedules."""
        sample_schedule.enabled = False
        db_session.commit()

        with patch.object(scheduler_service, "_add_job") as mock_add_job:
            scheduler_service.load_schedules()

            # Should not add disabled schedule
            assert mock_add_job.call_count == 0


class TestCronExpressionHandling:
    """Tests for cron expression parsing and validation."""

    @pytest.fixture
    def scheduler_service(self):
        """Create scheduler service for testing."""
        service = SchedulerService()
        service.start()
        yield service
        service.stop()

    def test_standard_cron_format(self, scheduler_service, db_session):
        """Test standard 5-field cron expression."""
        schedule = ScanSchedule(
            name="Test",
            network_range="192.168.1.0/24",
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
        )
        db_session.add(schedule)
        db_session.commit()

        # Should not raise exception
        scheduler_service.add_schedule(schedule.id)

    def test_extended_cron_format(self, scheduler_service, db_session):
        """Test extended 6-field cron expression with seconds."""
        schedule = ScanSchedule(
            name="Test",
            network_range="192.168.1.0/24",
            cron_expression="0 0 2 * * *",  # Daily at 2 AM with seconds
            enabled=True,
        )
        db_session.add(schedule)
        db_session.commit()

        # Should not raise exception
        scheduler_service.add_schedule(schedule.id)

    def test_invalid_cron_expression(self, scheduler_service, db_session):
        """Test that invalid cron expression raises error."""
        schedule = ScanSchedule(
            name="Test",
            network_range="192.168.1.0/24",
            cron_expression="invalid cron",
            enabled=True,
        )
        db_session.add(schedule)
        db_session.commit()

        with pytest.raises(Exception):
            scheduler_service.add_schedule(schedule.id)

    def test_next_run_time_calculation(self, scheduler_service, db_session):
        """Test that next_run_at is calculated correctly."""
        schedule = ScanSchedule(
            name="Test",
            network_range="192.168.1.0/24",
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
        )
        db_session.add(schedule)
        db_session.commit()

        scheduler_service._update_next_run(db_session, schedule)

        # Verify next_run_at was set
        assert schedule.next_run_at is not None
        assert schedule.next_run_at > datetime.utcnow()


class TestSchedulerIntegration:
    """Integration tests for scheduler service."""

    def test_full_schedule_lifecycle(self, db_session):
        """Test complete schedule lifecycle: create, trigger, update, remove."""
        scheduler = get_scheduler()
        scheduler.start()

        try:
            # Create schedule
            schedule = ScanSchedule(
                name="Integration Test",
                network_range="192.168.1.0/24",
                cron_expression="0 3 * * *",
                enabled=True,
            )
            db_session.add(schedule)
            db_session.commit()
            db_session.refresh(schedule)

            # Add to scheduler
            scheduler.add_schedule(schedule.id)

            # Manually trigger
            with patch.object(scheduler, "_run_scan_background"):
                scheduler.trigger_schedule(schedule.id)

                # Verify scan was created
                scan = (
                    db_session.query(Scan)
                    .filter(Scan.schedule_id == schedule.id)
                    .first()
                )
                assert scan is not None

            # Update schedule
            schedule.cron_expression = "0 4 * * *"
            db_session.commit()
            scheduler.update_schedule(schedule.id)

            # Remove schedule
            scheduler.remove_schedule(schedule.id)

        finally:
            scheduler.stop()

    def test_scheduler_starts_on_app_startup(self):
        """Test that scheduler is automatically started and accessible."""
        scheduler = get_scheduler()
        assert scheduler is not None
        assert isinstance(scheduler, SchedulerService)
