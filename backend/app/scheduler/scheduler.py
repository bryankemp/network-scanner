"""
Scheduler service for recurring network scans.

This module provides a background scheduler service that executes network scans
based on cron expressions. It uses APScheduler to manage scheduled jobs and
integrates with the existing scan orchestrator.
"""

import logging
import os
import threading
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import ScanSchedule, Scan, ScanStatus
from ..scanner.orchestrator import ScanOrchestrator
from ..scanner.stuck_scan_monitor import StuckScanMonitor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background scheduler service for recurring network scans."""

    def __init__(self):
        """Initialize the scheduler service."""
        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": False,  # Run all missed jobs
                "max_instances": 1,  # One instance per schedule at a time
                "misfire_grace_time": 300,  # 5 minutes grace period
            },
        )
        self._lock = threading.Lock()
        self._running = False
        logger.info("SchedulerService initialized")

    def start(self):
        """Start the scheduler and load all enabled schedules."""
        with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return

            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

            # Add daily data cleanup job (runs at 2 AM UTC)
            self._add_cleanup_job()

            # Add stuck scan monitoring job (runs every 10 minutes)
            self._add_stuck_scan_monitor_job()

            # Load all enabled schedules
            self.load_schedules()

    def stop(self):
        """Stop the scheduler and wait for running jobs to complete."""
        with self._lock:
            if not self._running:
                return

            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")

    def load_schedules(self):
        """Load all enabled schedules from database and add to scheduler."""
        db = SessionLocal()
        try:
            schedules = db.query(ScanSchedule).filter(ScanSchedule.enabled).all()
            logger.info(f"Loading {len(schedules)} enabled schedule(s)")

            for schedule in schedules:
                try:
                    self._add_job(schedule)
                    # Update next run time
                    self._update_next_run(db, schedule)
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.id}: {e}")

            db.commit()
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
            db.rollback()
        finally:
            db.close()

    def add_schedule(self, schedule_id: int):
        """Add a new schedule to the scheduler.

        Args:
            schedule_id: ID of the schedule to add
        """
        db = SessionLocal()
        try:
            schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return

            if not schedule.enabled:
                logger.info(f"Schedule {schedule_id} is disabled, not adding to scheduler")
                return

            self._add_job(schedule)
            self._update_next_run(db, schedule)
            db.commit()
            logger.info(f"Added schedule {schedule_id} to scheduler")
        except Exception as e:
            logger.error(f"Failed to add schedule {schedule_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def update_schedule(self, schedule_id: int):
        """Update an existing schedule in the scheduler.

        Args:
            schedule_id: ID of the schedule to update
        """
        # Remove old job and add new one
        self.remove_schedule(schedule_id)
        self.add_schedule(schedule_id)

    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from the scheduler.

        Args:
            schedule_id: ID of the schedule to remove
        """
        job_id = f"schedule_{schedule_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id} from scheduler")
        except Exception as e:
            logger.debug(f"Job {job_id} not found in scheduler: {e}")

    def trigger_schedule(self, schedule_id: int):
        """Manually trigger a scheduled scan immediately.

        Args:
            schedule_id: ID of the schedule to trigger
        """
        db = SessionLocal()
        try:
            schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return

            logger.info(f"Manually triggering schedule {schedule_id}")
            self._execute_scheduled_scan(schedule_id)
        finally:
            db.close()

    def _add_job(self, schedule: ScanSchedule):
        """Add a job to the scheduler.

        Args:
            schedule: ScanSchedule model instance
        """
        job_id = f"schedule_{schedule.id}"

        # Remove existing job if it exists
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

        # Parse cron expression and create trigger
        try:
            # Validate cron expression with croniter
            croniter(schedule.cron_expression)

            # APScheduler expects cron parts in different order
            # croniter: minute hour day month day_of_week
            # APScheduler: minute hour day month day_of_week
            parts = schedule.cron_expression.split()

            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    timezone="UTC",
                )
            elif len(parts) == 6:
                # Extended format with seconds
                second, minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    second=second,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    timezone="UTC",
                )
            else:
                raise ValueError(f"Invalid cron expression: {schedule.cron_expression}")

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_scheduled_scan,
                trigger=trigger,
                id=job_id,
                name=f"Scan: {schedule.name}",
                args=[schedule.id],
                replace_existing=True,
            )

            logger.info(f"Added job {job_id} with cron: {schedule.cron_expression}")
        except Exception as e:
            logger.error(f"Failed to add job for schedule {schedule.id}: {e}")
            raise

    def _execute_scheduled_scan(self, schedule_id: int):
        """Execute a scheduled scan.

        This method is called by APScheduler when a scheduled scan is triggered.
        It creates a new scan record and executes it in the background.

        Args:
            schedule_id: ID of the schedule to execute
        """
        db = SessionLocal()
        try:
            schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return

            if not schedule.enabled:
                logger.info(f"Schedule {schedule_id} is disabled, skipping execution")
                return

            logger.info(f"Executing scheduled scan for schedule {schedule_id}: {schedule.name}")

            # Parse network ranges (comma-separated)
            networks = [n.strip() for n in schedule.network_range.split(",")]

            # Create scan record
            scan = Scan(
                network_range=schedule.network_range,
                status=ScanStatus.PENDING,
                progress_percent=0,
                progress_message=f"Scheduled scan: {schedule.name}",
                schedule_id=schedule_id,
            )
            db.add(scan)
            db.commit()
            db.refresh(scan)

            # Update schedule last run time
            schedule.last_run_at = datetime.utcnow()
            db.commit()

            logger.info(f"Created scan {scan.id} for schedule {schedule_id}")

            # Execute scan in background thread
            thread = threading.Thread(
                target=self._run_scan_background, args=(scan.id, networks), daemon=True
            )
            thread.start()

            # Update next run time
            self._update_next_run(db, schedule)
            db.commit()

        except Exception as e:
            logger.error(f"Failed to execute scheduled scan {schedule_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def _run_scan_background(self, scan_id: int, networks: list):
        """Run scan in background thread with its own database session.

        Args:
            scan_id: ID of the scan to execute
            networks: List of network ranges to scan
        """
        db = SessionLocal()
        try:
            logger.info(f"Starting background scan {scan_id} for networks: {networks}")
            orchestrator = ScanOrchestrator(db)
            orchestrator.execute_scan(scan_id, networks)
            logger.info(f"Scheduled scan {scan_id} completed successfully")
        except Exception as e:
            logger.error(f"Scheduled scan {scan_id} failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
        finally:
            db.close()

    def _update_next_run(self, db: Session, schedule: ScanSchedule):
        """Update the next_run_at field for a schedule.

        Args:
            db: Database session
            schedule: ScanSchedule instance
        """
        try:
            cron = croniter(schedule.cron_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)
            schedule.next_run_at = next_run
            logger.debug(f"Next run for schedule {schedule.id}: {next_run}")
        except Exception as e:
            logger.error(f"Failed to calculate next run for schedule {schedule.id}: {e}")

    def _add_cleanup_job(self):
        """Add daily data cleanup job to remove old scan data."""
        try:
            trigger = CronTrigger(hour=2, minute=0, timezone="UTC")  # 2 AM UTC

            self.scheduler.add_job(
                func=self._cleanup_old_data,
                trigger=trigger,
                id="data_cleanup",
                name="Data Cleanup",
                replace_existing=True,
            )

            logger.info("Added daily data cleanup job (runs at 2 AM UTC)")
        except Exception as e:
            logger.error(f"Failed to add cleanup job: {e}")

    def _add_stuck_scan_monitor_job(self):
        """Add stuck scan monitoring job that runs every 10 minutes."""
        try:
            trigger = CronTrigger(minute="*/10", timezone="UTC")  # Every 10 minutes

            self.scheduler.add_job(
                func=self._check_stuck_scans,
                trigger=trigger,
                id="stuck_scan_monitor",
                name="Stuck Scan Monitor",
                replace_existing=True,
            )

            logger.info("Added stuck scan monitoring job (runs every 10 minutes)")
        except Exception as e:
            logger.error(f"Failed to add stuck scan monitor job: {e}")

    def _cleanup_old_data(self):
        """Remove scan data older than the configured retention period."""
        from ..models import Settings, Port, Artifact
        from datetime import timedelta

        db = SessionLocal()
        try:
            # Get data retention setting
            setting = db.query(Settings).filter(Settings.key == "data_retention_days").first()
            retention_days = int(setting.value) if setting else 90

            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            logger.info(
                f"Starting data cleanup for scans older than {retention_days} days (before {cutoff_date})"
            )

            # Find old scans
            old_scans = db.query(Scan).filter(Scan.created_at < cutoff_date).all()

            if not old_scans:
                logger.info("No old scans to clean up")
                return

            scan_ids = [scan.id for scan in old_scans]
            logger.info(f"Found {len(old_scans)} old scans to delete")

            # Delete related artifacts (files on disk)
            artifacts = db.query(Artifact).filter(Artifact.scan_id.in_(scan_ids)).all()
            for artifact in artifacts:
                try:
                    if os.path.exists(artifact.file_path):
                        os.remove(artifact.file_path)
                        logger.debug(f"Deleted file: {artifact.file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {artifact.file_path}: {e}")

            # Delete artifacts from database
            db.query(Artifact).filter(Artifact.scan_id.in_(scan_ids)).delete(
                synchronize_session=False
            )

            # Delete ports (cascade should handle this, but explicit for clarity)
            host_ids = [host.id for scan in old_scans for host in scan.hosts or []]
            if host_ids:
                db.query(Port).filter(Port.host_id.in_(host_ids)).delete(synchronize_session=False)

            # Delete hosts (cascade should handle this)
            for scan in old_scans:
                if scan.hosts:
                    for host in scan.hosts:
                        db.delete(host)

            # Delete scans
            for scan in old_scans:
                db.delete(scan)

            db.commit()
            logger.info(
                f"Successfully cleaned up {len(old_scans)} old scans and their related data"
            )

        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            db.rollback()
        finally:
            db.close()

    def _check_stuck_scans(self):
        """Check for and fix stuck scans."""
        db = SessionLocal()
        try:
            logger.info("Running stuck scan monitor")
            fixed_count = StuckScanMonitor.check_and_fix_stuck_scans(db)

            if fixed_count > 0:
                logger.warning(f"Fixed {fixed_count} stuck scan(s)")
            else:
                logger.debug("No stuck scans found")

        except Exception as e:
            logger.error(f"Stuck scan monitor failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
        finally:
            db.close()


# Global scheduler instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get the global scheduler service instance.

    Returns:
        SchedulerService instance
    """
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
