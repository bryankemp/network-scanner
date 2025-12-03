"""
MVP FastAPI application for Network Scanner.
Simplified version with core functionality only.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os

from .database import get_db
from .config import settings
from .models import User, Scan, Host, ScanStatus, ScanSchedule, Settings
from .schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ScanCreate,
    ScanResponse,
    ScanDetailResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    UserListResponse,
    NetworkStats,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    UserPasswordChangeRequest,
    UserPasswordResetRequest,
)
from .schemas.settings import AppSettings, AppSettingsResponse
from .auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_admin_user,
)
from .scanner.orchestrator import ScanOrchestrator
from .scheduler import get_scheduler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    from .database import Base, engine, SessionLocal
    from .models import UserRole
    from .auth import get_password_hash

    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized")

    # Create default admin user if no users exist
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            admin_user = User(
                username="admin",
                email="admin@localhost",
                full_name="Administrator",
                hashed_password=get_password_hash("Admin123!"),
                role=UserRole.ADMIN,
                must_change_password=True,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print("✓ Default admin user created (username: admin, password: Admin123!)")
            print("  ⚠️  Please change the default password on first login")
    finally:
        db.close()

    # Start scheduler service
    scheduler = get_scheduler()
    scheduler.start()
    print("✓ Scheduler service started")
    print("✓ Server running at http://localhost:8000")
    print("✓ API docs available at http://localhost:8000/docs")

    yield

    # Shutdown
    scheduler.stop()
    print("✓ Scheduler service stopped")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    description="Network Scanner API - MVP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add middleware to prevent caching of static files
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add no-cache headers for HTML and JS files
        if request.url.path.endswith((".html", ".js", "/")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)


# ============================================================================
# Authentication Endpoints
# ============================================================================


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint.
    Returns JWT access and refresh tokens.
    """
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=user.must_change_password,
        role=user.role.value,
        username=user.username,
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    Returns new access and refresh tokens.
    """
    from .auth import decode_token

    try:
        # Decode and verify refresh token
        payload = decode_token(request.refresh_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
            )

        # Create new tokens
        access_token = create_access_token(data={"sub": user.username})
        new_refresh_token = create_refresh_token(data={"sub": user.username})

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            must_change_password=user.must_change_password,
            role=user.role.value,
            username=user.username,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )


@app.put("/api/auth/change-password")
async def change_password(
    request: UserPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user password.
    Requires current password verification.
    """
    from .auth import get_password_hash

    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.must_change_password = False
    db.commit()

    return {"message": "Password changed successfully"}


# ============================================================================
# Scan Endpoints
# ============================================================================


@app.post("/api/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create and initiate a new network scan (admin only).
    Scan runs in a separate thread.
    Accepts multiple networks in CIDR format.
    If no networks specified, auto-detects current network.
    """
    from .scanner.network_detection import detect_current_network
    import threading

    # Auto-detect network if not specified
    if scan_data.networks is None or len(scan_data.networks) == 0:
        detected_network = detect_current_network()
        if detected_network:
            networks = [detected_network]
        else:
            raise HTTPException(
                status_code=400,
                detail="Could not auto-detect network. Please specify networks manually.",
            )
    else:
        networks = scan_data.networks

    # Store networks as comma-separated string for display
    network_range = ", ".join(networks)

    # Create scan record
    scan = Scan(
        network_range=network_range,
        status=ScanStatus.PENDING,
        progress_percent=0,
        progress_message="Scan queued",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Execute scan in background thread (don't pass db session, it will be closed)
    thread = threading.Thread(target=run_scan_background, args=(scan.id, networks), daemon=True)
    thread.start()
    print(f"[API] Started background thread for scan {scan.id}", flush=True)

    return scan


def run_scan_background(scan_id: int, networks: list):
    """Background task to execute scan with its own database session."""
    from .database import SessionLocal
    import sys

    print(f"[BACKGROUND] Starting scan {scan_id} for networks: {networks}", flush=True)
    sys.stdout.flush()

    # Create a new database session for the background task
    db = SessionLocal()
    try:
        print("[BACKGROUND] Creating orchestrator...", flush=True)
        orchestrator = ScanOrchestrator(db)
        print("[BACKGROUND] Executing scan...", flush=True)
        orchestrator.execute_scan(scan_id, networks)
        print(f"[BACKGROUND] Scan {scan_id} completed successfully", flush=True)
    except Exception as e:
        print(f"[BACKGROUND] Scan {scan_id} failed: {e}", flush=True)
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
    finally:
        db.close()
        print(f"[BACKGROUND] Database session closed for scan {scan_id}", flush=True)


@app.get("/api/scans", response_model=list[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    List all scans.
    Returns most recent scans first.
    """
    scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    return scans


@app.get("/api/scans/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """
    Get detailed scan information including hosts and artifacts.
    """
    from sqlalchemy.orm import joinedload

    scan = (
        db.query(Scan)
        .options(joinedload(Scan.hosts).joinedload(Host.ports), joinedload(Scan.artifacts))
        .filter(Scan.id == scan_id)
        .first()
    )

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return scan


@app.delete("/api/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a scan and all associated data (admin only)."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Delete artifacts files
    for artifact in scan.artifacts:
        try:
            if os.path.exists(artifact.file_path):
                os.remove(artifact.file_path)
        except Exception as e:
            print(f"Warning: Failed to delete artifact file: {e}")

    # Delete database records (cascade will handle related records)
    db.delete(scan)
    db.commit()


# ============================================================================
# Artifact Endpoints
# ============================================================================


@app.get("/api/artifacts/{scan_id}/{artifact_type}")
async def get_artifact(scan_id: int, artifact_type: str, db: Session = Depends(get_db)):
    """
    Download or view a scan artifact (HTML, PNG, XLSX, etc.).
    """
    from .models import Artifact, ArtifactType

    # Map string to enum
    try:
        art_type = ArtifactType(artifact_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid artifact type: {artifact_type}")

    artifact = (
        db.query(Artifact).filter(Artifact.scan_id == scan_id, Artifact.type == art_type).first()
    )

    if not artifact or not os.path.exists(artifact.file_path):
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Determine media type
    media_types = {
        ArtifactType.HTML: "text/html",
        ArtifactType.PNG: "image/png",
        ArtifactType.SVG: "image/svg+xml",
        ArtifactType.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ArtifactType.XML: "application/xml",
        ArtifactType.DOT: "text/plain",
    }

    return FileResponse(
        artifact.file_path,
        media_type=media_types.get(art_type, "application/octet-stream"),
        filename=os.path.basename(artifact.file_path),
    )


# ============================================================================
# Statistics Endpoint
# ============================================================================


@app.get("/api/stats", response_model=NetworkStats)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get overall network statistics with unique counts.

    Counts unique hosts by IP address, not total host records across all scans.
    This prevents counting the same host multiple times if scanned repeatedly.
    """
    from sqlalchemy import func, distinct

    total_scans = db.query(func.count(Scan.id)).scalar()

    # Count UNIQUE hosts by IP address (not total host records)
    total_hosts = db.query(func.count(distinct(Host.ip))).scalar()

    # Count UNIQUE VMs by IP address
    total_vms = db.query(func.count(distinct(Host.ip))).filter(Host.is_vm).scalar()

    # Count UNIQUE services by IP + port + protocol combination
    from .models import Port

    total_services = (
        db.query(func.count(distinct(func.concat(Host.ip, ":", Port.port, "/", Port.protocol))))
        .select_from(Port)
        .join(Host, Port.host_id == Host.id)
        .scalar()
    )

    # Recent scans (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_scans = db.query(func.count(Scan.id)).filter(Scan.created_at >= yesterday).scalar()

    # Failed scans
    failed_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatus.FAILED).scalar()

    # Active schedules
    active_schedules = db.query(func.count(ScanSchedule.id)).filter(ScanSchedule.enabled).scalar()

    return NetworkStats(
        total_scans=total_scans or 0,
        total_hosts=total_hosts or 0,
        total_vms=total_vms or 0,
        total_services=total_services or 0,
        recent_scans=recent_scans or 0,
        active_schedules=active_schedules or 0,
        failed_scans=failed_scans or 0,
    )


# ============================================================================
# Schedule Endpoints
# ============================================================================


@app.post("/api/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new scan schedule (admin only).
    """
    # Create schedule record
    schedule = ScanSchedule(
        name=schedule_data.name,
        cron_expression=schedule_data.cron_expression,
        network_range=schedule_data.network_range,
        enabled=schedule_data.enabled,
        created_by_id=current_user.id,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Add to scheduler if enabled
    if schedule.enabled:
        scheduler = get_scheduler()
        scheduler.add_schedule(schedule.id)

    return schedule


@app.get("/api/schedules", response_model=ScheduleListResponse)
async def list_schedules(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    List all scan schedules.
    """
    from sqlalchemy import func

    schedules = (
        db.query(ScanSchedule)
        .order_by(ScanSchedule.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(func.count(ScanSchedule.id)).scalar()

    return ScheduleListResponse(schedules=schedules, total=total or 0)


@app.get("/api/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Get a specific schedule by ID.
    """
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@app.put("/api/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing schedule (admin only).
    """
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if schedule_data.name is not None:
        schedule.name = schedule_data.name
    if schedule_data.cron_expression is not None:
        schedule.cron_expression = schedule_data.cron_expression
    if schedule_data.network_range is not None:
        schedule.network_range = schedule_data.network_range
    if schedule_data.enabled is not None:
        schedule.enabled = schedule_data.enabled

    schedule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(schedule)

    # Update scheduler
    scheduler = get_scheduler()
    if schedule.enabled:
        scheduler.update_schedule(schedule.id)
    else:
        scheduler.remove_schedule(schedule.id)

    return schedule


@app.delete("/api/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete a schedule (admin only).
    """
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from scheduler
    scheduler = get_scheduler()
    scheduler.remove_schedule(schedule.id)

    # Delete from database
    db.delete(schedule)
    db.commit()


@app.post("/api/schedules/{schedule_id}/trigger", response_model=ScanResponse)
async def trigger_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Manually trigger a scheduled scan immediately (admin only).
    """
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Trigger the schedule
    scheduler = get_scheduler()
    scheduler.trigger_schedule(schedule.id)

    # Return the most recent scan created by this schedule
    scan = (
        db.query(Scan)
        .filter(Scan.schedule_id == schedule_id)
        .order_by(Scan.created_at.desc())
        .first()
    )

    if not scan:
        raise HTTPException(status_code=500, detail="Failed to trigger schedule")

    return scan


# ============================================================================
# Unique Data Endpoints
# ============================================================================


@app.get("/api/hosts/unique")
async def get_unique_hosts(db: Session = Depends(get_db)):
    """
    Get list of unique hosts (latest scan data for each IP).
    """
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    # Get the most recent host record for each unique IP
    subquery = db.query(Host.ip, func.max(Host.id).label("max_id")).group_by(Host.ip).subquery()

    hosts = (
        db.query(Host)
        .join(subquery, (Host.ip == subquery.c.ip) & (Host.id == subquery.c.max_id))
        .options(joinedload(Host.ports))
        .all()
    )

    # Sort hosts by IP address naturally
    def ip_sort_key(host):
        try:
            return tuple(int(part) for part in host.ip.split("."))
        except (ValueError, AttributeError):
            return (999, 999, 999, 999)

    return sorted(hosts, key=ip_sort_key)


@app.get("/api/vms/unique")
async def get_unique_vms(db: Session = Depends(get_db)):
    """
    Get list of unique VMs (latest scan data for each VM IP).
    """
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    # Get the most recent host record for each unique VM IP
    subquery = (
        db.query(Host.ip, func.max(Host.id).label("max_id"))
        .filter(Host.is_vm)
        .group_by(Host.ip)
        .subquery()
    )

    vms = (
        db.query(Host)
        .join(subquery, (Host.ip == subquery.c.ip) & (Host.id == subquery.c.max_id))
        .options(joinedload(Host.ports))
        .all()
    )

    # Sort VMs by IP address naturally
    def ip_sort_key(host):
        try:
            return tuple(int(part) for part in host.ip.split("."))
        except (ValueError, AttributeError):
            return (999, 999, 999, 999)

    return sorted(vms, key=ip_sort_key)


@app.get("/api/services/unique")
async def get_unique_services(db: Session = Depends(get_db)):
    """
    Get unique services grouped by service type and product/version.
    Returns services with list of hosts running each service.
    """
    from sqlalchemy import func
    from .models import Port

    # Query all ports with host IP, grouped by service attributes
    services_query = (
        db.query(
            Port.port,
            Port.protocol,
            Port.service,
            Port.product,
            Port.version,
            func.group_concat(Host.ip).label("host_ips"),
        )
        .select_from(Port)
        .join(Host, Port.host_id == Host.id)
        .group_by(Port.port, Port.protocol, Port.service, Port.product, Port.version)
        .order_by(Port.service, Port.product, Port.port)
        .all()
    )

    # Transform into grouped structure with better handling
    services_grouped = {}

    def ip_sort_key(ip):
        try:
            return tuple(int(part) for part in ip.split("."))
        except (ValueError, AttributeError):
            return (999, 999, 999, 999)

    for row in services_query:
        # Better service naming
        if row.service:
            service_name = row.service
        elif row.port == 22:
            service_name = "ssh"
        elif row.port == 80:
            service_name = "http"
        elif row.port == 443:
            service_name = "https"
        else:
            service_name = f"port-{row.port}"

        # Better product naming
        if row.product and row.version:
            product_key = f"{row.product} {row.version}"
        elif row.product:
            product_key = row.product
        elif row.version:
            product_key = f"version {row.version}"
        else:
            product_key = f"port {row.port}/{row.protocol}"

        if service_name not in services_grouped:
            services_grouped[service_name] = {}

        if product_key not in services_grouped[service_name]:
            services_grouped[service_name][product_key] = []

        # Sort hosts by IP
        host_list = sorted(row.host_ips.split(",") if row.host_ips else [], key=ip_sort_key)

        services_grouped[service_name][product_key].append(
            {
                "port": row.port,
                "protocol": row.protocol,
                "product": row.product,
                "version": row.version,
                "hosts": host_list,
            }
        )

    return services_grouped


# ============================================================================
# User Management Endpoints (Admin Only)
# ============================================================================


@app.get("/api/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    List all users (admin only).
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    return UserListResponse(users=users, total=total)


@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new user (admin only).
    """
    from .models import UserRole
    from .auth import get_password_hash

    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=UserRole[user_data.role.upper()],
        must_change_password=True,  # Force password change on first login
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update a user (admin only).
    """
    from .models import UserRole

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields if provided
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = UserRole[user_data.role.upper()]
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete a user (admin only). Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()


@app.post("/api/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    reset_data: UserPasswordResetRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Reset a user password (admin only).
    """
    from .auth import get_password_hash

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(reset_data.new_password)
    user.must_change_password = reset_data.force_change
    db.commit()

    return {"message": "Password reset successfully"}


# ============================================================================
# Settings Endpoints
# ============================================================================


def get_setting(db: Session, key: str, default: str) -> str:
    """Helper to get a setting value."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    """Helper to set a setting value."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        db.add(setting)
    db.commit()


@app.get("/api/settings", response_model=AppSettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """
    Get application settings.
    Returns current configuration values.
    """
    return AppSettingsResponse(
        scan_parallelism=int(get_setting(db, "scan_parallelism", "8")),
        data_retention_days=int(get_setting(db, "data_retention_days", "90")),
    )


@app.put("/api/settings", response_model=AppSettingsResponse)
async def update_settings(
    settings_data: AppSettings,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update application settings (admin only).
    Changes take effect immediately for new scans.
    """
    set_setting(db, "scan_parallelism", str(settings_data.scan_parallelism))
    set_setting(db, "data_retention_days", str(settings_data.data_retention_days))

    # Update config settings in memory for immediate effect
    from .config import settings as config_settings

    config_settings.scan_parallelism = settings_data.scan_parallelism

    return AppSettingsResponse(
        scan_parallelism=settings_data.scan_parallelism,
        data_retention_days=settings_data.data_retention_days,
    )


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "network-scanner-api", "version": "1.0.0-mvp"}


# ============================================================================
# Static Frontend (Flutter Web build)
# ============================================================================
try:
    # Serve prebuilt frontend from "static" directory (copied during deployment)
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
    print("✓ Frontend static files mounted at /")
except Exception as _e:
    # Static directory may not exist in dev; ignore
    pass

# Serve frontend (optional manual run)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
