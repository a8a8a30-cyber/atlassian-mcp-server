import os
import json
from datetime import date, datetime, timedelta, timezone
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import joinedload

db = SQLAlchemy()

VEHICLE_STATUSES = ("available", "rented", "maintenance")
OPEN_RESERVATION_STATUSES = ("pending", "confirmed", "active")
REVENUE_STATUSES = ("active", "completed")
GPS_BACKEND_CONTRACT_PREFIX = "FLASK-CONTRACT"

STATUS_LABELS = {
    "available": "متاحة",
    "rented": "مؤجرة",
    "maintenance": "صيانة",
    "pending": "قيد المراجعة",
    "confirmed": "مؤكد",
    "active": "نشط",
    "completed": "مكتمل",
    "cancelled": "ملغي",
    "closed": "مغلق",
}

STATUS_BADGES = {
    "available": "text-bg-success",
    "rented": "text-bg-primary",
    "maintenance": "text-bg-warning",
    "pending": "text-bg-warning",
    "confirmed": "text-bg-info",
    "active": "text-bg-primary",
    "completed": "text-bg-success",
    "cancelled": "text-bg-secondary",
    "closed": "text-bg-dark",
}


def utc_now():
    return datetime.now(timezone.utc)


def status_label(status_code: str) -> str:
    return STATUS_LABELS.get(status_code, status_code)


def status_badge(status_code: str) -> str:
    return STATUS_BADGES.get(status_code, "text-bg-secondary")


def gps_backend_base_url() -> str:
    return os.getenv("GPS_BACKEND_BASE_URL", "").strip().rstrip("/")


def gps_backend_enabled() -> bool:
    return bool(gps_backend_base_url())


def gps_backend_timeout_seconds() -> int:
    try:
        return int(os.getenv("GPS_BACKEND_TIMEOUT_SECONDS", "15"))
    except ValueError:
        return 15


def build_external_contract_id(contract_id: int) -> str:
    return f"{GPS_BACKEND_CONTRACT_PREFIX}-{contract_id}"


def safe_json_loads(raw_value: str):
    if not raw_value:
        return {}
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return {"raw": raw_value}


def call_gps_backend(
    method: str,
    path: str,
    payload: dict | None = None,
    query_params: dict | None = None,
):
    base_url = gps_backend_base_url()
    if not base_url:
        return {
            "ok": False,
            "status": None,
            "error": "GPS backend URL is not configured.",
            "data": None,
        }

    normalized_path = path if path.startswith("/") else f"/{path}"
    url = f"{base_url}{normalized_path}"
    if query_params:
        filtered = {k: v for k, v in query_params.items() if v is not None}
        if filtered:
            url = f"{url}?{urllib_parse.urlencode(filtered)}"

    request_data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    backend_request = urllib_request.Request(
        url=url,
        data=request_data,
        method=method.upper(),
        headers=headers,
    )

    try:
        with urllib_request.urlopen(
            backend_request, timeout=gps_backend_timeout_seconds()
        ) as response:
            body = response.read().decode("utf-8")
            return {
                "ok": True,
                "status": response.status,
                "error": None,
                "data": safe_json_loads(body),
            }
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed_body = safe_json_loads(body)
        message = parsed_body.get("error") if isinstance(parsed_body, dict) else str(exc)
        return {
            "ok": False,
            "status": exc.code,
            "error": message or f"HTTP error {exc.code}",
            "data": parsed_body,
        }
    except urllib_error.URLError as exc:
        return {
            "ok": False,
            "status": None,
            "error": f"GPS backend is unreachable: {exc.reason}",
            "data": None,
        }


def parse_backend_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        normalized = value
    else:
        text = str(value).strip()
        normalized = None
        parse_formats = (
            None,
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        )
        for parse_format in parse_formats:
            try:
                if parse_format is None:
                    normalized = datetime.fromisoformat(text.replace("Z", "+00:00"))
                else:
                    normalized = datetime.strptime(text, parse_format)
                break
            except ValueError:
                continue
    if normalized is None:
        return None
    if normalized.tzinfo is None:
        return normalized.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc)


def sync_contract_to_gps_backend(contract, reservation, vehicle):
    if not gps_backend_enabled():
        return {"ok": False, "skipped": True, "message": "GPS backend غير مفعل."}

    imei = (vehicle.gps_identifier or "").strip()
    if not imei:
        return {
            "ok": False,
            "skipped": True,
            "message": "لا يوجد IMEI في المركبة، يرجى تعبئة GPS ID.",
        }

    start_dt = contract.start_datetime or utc_now()
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    else:
        start_dt = start_dt.astimezone(timezone.utc)

    expected_end_dt = datetime.combine(
        reservation.end_date,
        datetime.max.time().replace(microsecond=0),
    ).replace(tzinfo=timezone.utc)

    payload = {
        "externalContractId": build_external_contract_id(contract.id),
        "customerName": reservation.customer_name,
        "vehiclePlate": vehicle.plate_number,
        "deviceImei": imei,
        "startAt": start_dt.isoformat().replace("+00:00", "Z"),
        "endAt": expected_end_dt.isoformat().replace("+00:00", "Z"),
        "speedLimitKmh": int(os.getenv("DEFAULT_SPEED_LIMIT_KMH", "120")),
        "distanceLimitKm": float(os.getenv("DEFAULT_DISTANCE_LIMIT_KM", "500")),
    }

    response = call_gps_backend(
        method="POST",
        path="/api/integration/rental/contracts",
        payload=payload,
    )
    if response["ok"] and isinstance(response["data"], dict) and response["data"].get("ok"):
        contract_data = response["data"].get("contract", {})
        return {
            "ok": True,
            "skipped": False,
            "created": response["data"].get("created", True),
            "external_contract_id": contract_data.get("externalContractId"),
        }
    return {
        "ok": False,
        "skipped": False,
        "message": response.get("error") or "تعذر مزامنة العقد مع GPS backend.",
    }


def close_contract_in_gps_backend(contract_id: int):
    if not gps_backend_enabled():
        return {"ok": False, "skipped": True, "message": "GPS backend غير مفعل."}

    external_contract_id = build_external_contract_id(contract_id)
    encoded_external_id = urllib_parse.quote(external_contract_id, safe="")
    response = call_gps_backend(
        method="PATCH",
        path=f"/api/contracts/external/{encoded_external_id}/close",
    )
    if response["ok"] and isinstance(response["data"], dict) and response["data"].get("ok"):
        return {"ok": True, "skipped": False}
    return {
        "ok": False,
        "skipped": False,
        "message": response.get("error") or "تعذر إغلاق العقد في GPS backend.",
    }


def sync_live_positions_from_backend(limit=300, from_minutes=20):
    if not gps_backend_enabled():
        return {"ok": False, "message": "GPS backend غير مفعل."}

    sync_devices_result = call_gps_backend(method="POST", path="/api/gpsdome/sync/devices")
    if not sync_devices_result["ok"]:
        return {
            "ok": False,
            "message": f"فشل مزامنة الأجهزة: {sync_devices_result.get('error')}",
        }

    sync_positions_result = call_gps_backend(
        method="POST",
        path="/api/gpsdome/sync/positions",
        payload={"fromMinutes": from_minutes, "limit": max(int(limit), 200)},
    )
    if not sync_positions_result["ok"]:
        return {
            "ok": False,
            "message": f"فشل مزامنة المواقع: {sync_positions_result.get('error')}",
        }

    live_positions_result = call_gps_backend(
        method="GET",
        path="/api/reports/live-positions",
        query_params={"limit": int(limit)},
    )
    if not live_positions_result["ok"]:
        return {
            "ok": False,
            "message": f"فشل جلب المواقع المباشرة: {live_positions_result.get('error')}",
        }

    payload = live_positions_result.get("data") or {}
    backend_positions = payload.get("positions", []) if isinstance(payload, dict) else []
    if not isinstance(backend_positions, list):
        return {"ok": False, "message": "تنسيق المواقع المستلمة من GPS backend غير صالح."}

    vehicles = Vehicle.query.filter(Vehicle.gps_identifier.isnot(None)).all()
    vehicles_by_imei = {}
    for vehicle in vehicles:
        key = (vehicle.gps_identifier or "").strip()
        if key:
            vehicles_by_imei[key] = vehicle

    imported = 0
    duplicates = 0
    unmatched = 0
    ignored = 0

    for item in backend_positions:
        imei = str(item.get("imei", "")).strip()
        vehicle = vehicles_by_imei.get(imei)
        if not vehicle:
            unmatched += 1
            continue

        try:
            latitude = float(item.get("latitude"))
            longitude = float(item.get("longitude"))
            speed_kmh = max(float(item.get("speedKmh", 0) or 0), 0.0)
        except (TypeError, ValueError):
            ignored += 1
            continue

        recorded_at = parse_backend_datetime(item.get("positionTime")) or utc_now()
        existing = GpsPosition.query.filter_by(
            vehicle_id=vehicle.id,
            recorded_at=recorded_at,
        ).first()
        if existing:
            duplicates += 1
            continue

        db.session.add(
            GpsPosition(
                vehicle_id=vehicle.id,
                latitude=latitude,
                longitude=longitude,
                speed_kmh=speed_kmh,
                recorded_at=recorded_at,
                source="gpsdome",
            )
        )
        imported += 1

    if imported > 0:
        db.session.commit()

    return {
        "ok": True,
        "imported": imported,
        "duplicates": duplicates,
        "unmatched": unmatched,
        "ignored": ignored,
        "fetched": len(backend_positions),
    }


def load_contract_gps_report(contract_id: int):
    if not gps_backend_enabled():
        return {"ok": False, "message": "GPS backend غير مفعل.", "report": None}

    external_contract_id = build_external_contract_id(contract_id)
    encoded_external_id = urllib_parse.quote(external_contract_id, safe="")
    response = call_gps_backend(
        method="GET",
        path=f"/api/reports/contracts/external/{encoded_external_id}",
    )
    if response["ok"] and isinstance(response["data"], dict) and response["data"].get("ok"):
        return {
            "ok": True,
            "message": None,
            "report": response["data"].get("report"),
            "external_contract_id": external_contract_id,
        }
    return {
        "ok": False,
        "message": response.get("error") or "تعذر تحميل تقرير GPS.",
        "report": None,
        "external_contract_id": external_contract_id,
    }


def resolve_database_uri(app: Flask, database_uri: str | None = None) -> str:
    if database_uri:
        return database_uri

    env_database_url = os.getenv("DATABASE_URL")
    if env_database_url:
        # Some providers expose postgres:// while SQLAlchemy expects postgresql://
        if env_database_url.startswith("postgres://"):
            return env_database_url.replace("postgres://", "postgresql://", 1)
        return env_database_url

    os.makedirs(app.instance_path, exist_ok=True)
    sqlite_path = os.path.join(app.instance_path, "car_rental.db")
    return f"sqlite:///{sqlite_path}"


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    vehicles = db.relationship("Vehicle", back_populates="branch", lazy=True)


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(30), unique=True, nullable=False)
    make = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="available", nullable=False)
    odometer = db.Column(db.Integer, default=0, nullable=False)
    gps_identifier = db.Column(db.String(120), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    branch = db.relationship("Branch", back_populates="vehicles")
    reservations = db.relationship("Reservation", back_populates="vehicle", lazy=True)
    gps_positions = db.relationship("GpsPosition", back_populates="vehicle", lazy=True)


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    pickup_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    dropoff_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="confirmed", nullable=False)
    notes = db.Column(db.String(400), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    vehicle = db.relationship("Vehicle", back_populates="reservations")
    pickup_branch = db.relationship("Branch", foreign_keys=[pickup_branch_id])
    dropoff_branch = db.relationship("Branch", foreign_keys=[dropoff_branch_id])
    contract = db.relationship("Contract", back_populates="reservation", uselist=False)


class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer,
        db.ForeignKey("reservations.id"),
        unique=True,
        nullable=False,
    )
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    start_datetime = db.Column(db.DateTime, default=utc_now, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=True)
    start_odometer = db.Column(db.Integer, nullable=False)
    end_odometer = db.Column(db.Integer, nullable=True)
    fuel_out = db.Column(db.Integer, default=100, nullable=False)
    fuel_in = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)
    close_notes = db.Column(db.String(400), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    reservation = db.relationship("Reservation", back_populates="contract")
    vehicle = db.relationship("Vehicle")


class GpsPosition(db.Model):
    __tablename__ = "gps_positions"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed_kmh = db.Column(db.Float, default=0.0, nullable=False)
    recorded_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    source = db.Column(db.String(40), default="manual", nullable=False)

    vehicle = db.relationship("Vehicle", back_populates="gps_positions")


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def calculate_total_price(daily_rate: float, start_date, end_date):
    rental_days = (end_date - start_date).days
    if rental_days <= 0:
        raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")
    return rental_days, round(daily_rate * rental_days, 2)


def sar_amount(value: float) -> str:
    return f"{value:,.2f} ر.س"


def seed_initial_data():
    if Branch.query.count() == 0:
        db.session.add(Branch(name="Main Branch", city="Riyadh"))
        db.session.commit()


def seed_demo_data():
    branch_definitions = [
        ("Main Branch", "Riyadh"),
        ("Airport Branch", "Jeddah"),
        ("North Branch", "Dammam"),
    ]
    branches_by_name = {}
    for name, city in branch_definitions:
        branch = Branch.query.filter_by(name=name).first()
        if not branch:
            branch = Branch(name=name, city=city)
            db.session.add(branch)
    db.session.flush()

    for branch in Branch.query.all():
        branches_by_name[branch.name] = branch

    vehicle_definitions = [
        {
            "plate_number": "RTL-101",
            "make": "Toyota",
            "model": "Camry",
            "year": 2024,
            "daily_rate": 220,
            "status": "available",
            "odometer": 15000,
            "gps_identifier": "GPS-RTL-101",
            "branch_name": "Main Branch",
        },
        {
            "plate_number": "RTL-202",
            "make": "Hyundai",
            "model": "Sonata",
            "year": 2023,
            "daily_rate": 210,
            "status": "available",
            "odometer": 21400,
            "gps_identifier": "GPS-RTL-202",
            "branch_name": "Airport Branch",
        },
        {
            "plate_number": "RTL-303",
            "make": "Kia",
            "model": "K5",
            "year": 2024,
            "daily_rate": 230,
            "status": "maintenance",
            "odometer": 9800,
            "gps_identifier": "GPS-RTL-303",
            "branch_name": "North Branch",
        },
    ]

    added_vehicles = 0
    for definition in vehicle_definitions:
        if Vehicle.query.filter_by(plate_number=definition["plate_number"]).first():
            continue
        branch = branches_by_name.get(definition["branch_name"])
        if not branch:
            continue
        db.session.add(
            Vehicle(
                plate_number=definition["plate_number"],
                make=definition["make"],
                model=definition["model"],
                year=definition["year"],
                daily_rate=definition["daily_rate"],
                status=definition["status"],
                odometer=definition["odometer"],
                gps_identifier=definition["gps_identifier"],
                branch_id=branch.id,
            )
        )
        added_vehicles += 1
    db.session.flush()

    vehicles = Vehicle.query.order_by(Vehicle.id.asc()).all()
    reservations_added = 0
    if vehicles:
        has_any_reservation = Reservation.query.count() > 0
        if not has_any_reservation:
            start_one = date.today() + timedelta(days=1)
            end_one = date.today() + timedelta(days=4)
            _, total_one = calculate_total_price(vehicles[0].daily_rate, start_one, end_one)
            reservation_one = Reservation(
                customer_name="عميل تجريبي",
                customer_phone="0500000001",
                vehicle_id=vehicles[0].id,
                pickup_branch_id=vehicles[0].branch_id,
                dropoff_branch_id=vehicles[0].branch_id,
                start_date=start_one,
                end_date=end_one,
                total_price=total_one,
                status="confirmed",
                notes="بيانات تجريبية",
            )
            db.session.add(reservation_one)
            reservations_added += 1

            if len(vehicles) > 1:
                start_two = date.today() - timedelta(days=1)
                end_two = date.today() + timedelta(days=2)
                _, total_two = calculate_total_price(
                    vehicles[1].daily_rate,
                    start_two,
                    end_two,
                )
                reservation_two = Reservation(
                    customer_name="شركة تجريبية",
                    customer_phone="0555555555",
                    vehicle_id=vehicles[1].id,
                    pickup_branch_id=vehicles[1].branch_id,
                    dropoff_branch_id=vehicles[1].branch_id,
                    start_date=start_two,
                    end_date=end_two,
                    total_price=total_two,
                    status="active",
                    notes="عقد نشط تجريبي",
                )
                db.session.add(reservation_two)
                db.session.flush()

                contract = Contract(
                    reservation_id=reservation_two.id,
                    vehicle_id=vehicles[1].id,
                    start_odometer=vehicles[1].odometer,
                    fuel_out=95,
                    status="active",
                )
                db.session.add(contract)
                vehicles[1].status = "rented"
                reservations_added += 1

    gps_added = 0
    if GpsPosition.query.count() == 0:
        for vehicle in vehicles[:2]:
            db.session.add(
                GpsPosition(
                    vehicle_id=vehicle.id,
                    latitude=24.7136 if vehicle.id % 2 else 21.4858,
                    longitude=46.6753 if vehicle.id % 2 else 39.1925,
                    speed_kmh=62.0 if vehicle.id % 2 else 48.0,
                    source="demo",
                )
            )
            gps_added += 1

    db.session.commit()
    return {
        "vehicles": added_vehicles,
        "reservations": reservations_added,
        "gps_points": gps_added,
    }


def create_app(database_uri=None, testing=False):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_uri(app, database_uri)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing

    db.init_app(app)

    @app.template_filter("sar")
    def sar_filter(value):
        try:
            return sar_amount(float(value))
        except (TypeError, ValueError):
            return "0.00 ر.س"

    @app.context_processor
    def inject_ui_helpers():
        return {
            "status_label": status_label,
            "status_badge": status_badge,
            "gps_backend_enabled": gps_backend_enabled(),
            "build_external_contract_id": build_external_contract_id,
            "vehicle_status_options": [
                (status_code, status_label(status_code))
                for status_code in VEHICLE_STATUSES
            ],
        }

    with app.app_context():
        db.create_all()
        seed_initial_data()

    @app.get("/")
    def dashboard():
        total_vehicles = Vehicle.query.count()
        rented_vehicles = Vehicle.query.filter_by(status="rented").count()
        utilization_rate = (
            round((rented_vehicles / total_vehicles) * 100, 1) if total_vehicles else 0.0
        )
        totals = {
            "branches": Branch.query.count(),
            "vehicles": total_vehicles,
            "available_vehicles": Vehicle.query.filter_by(status="available").count(),
            "rented_vehicles": rented_vehicles,
            "maintenance_vehicles": Vehicle.query.filter_by(status="maintenance").count(),
            "active_contracts": Contract.query.filter_by(status="active").count(),
            "open_reservations": Reservation.query.filter(
                Reservation.status.in_(OPEN_RESERVATION_STATUSES)
            ).count(),
            "utilization_rate": utilization_rate,
        }
        upcoming_reservations = (
            Reservation.query.options(
                joinedload(Reservation.vehicle),
                joinedload(Reservation.pickup_branch),
            )
            .filter(Reservation.status.in_(OPEN_RESERVATION_STATUSES))
            .order_by(Reservation.start_date.asc())
            .limit(10)
            .all()
        )
        latest_positions = (
            GpsPosition.query.options(joinedload(GpsPosition.vehicle))
            .order_by(GpsPosition.recorded_at.desc())
            .limit(10)
            .all()
        )
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        next_month_start = (
            datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            if now.month == 12
            else datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        )
        monthly_revenue = (
            0.0
        )
        revenue_rows = (
            db.session.query(Reservation.total_price, Reservation.created_at)
            .filter(Reservation.status.in_(REVENUE_STATUSES))
            .all()
        )
        for amount, created_at in revenue_rows:
            if created_at is None:
                continue
            normalized = (
                created_at.astimezone(timezone.utc)
                if created_at.tzinfo
                else created_at.replace(tzinfo=timezone.utc)
            )
            if month_start <= normalized < next_month_start:
                monthly_revenue += float(amount)
        is_empty_workspace = totals["vehicles"] == 0 and Reservation.query.count() == 0
        return render_template(
            "dashboard.html",
            totals=totals,
            upcoming_reservations=upcoming_reservations,
            latest_positions=latest_positions,
            monthly_revenue=monthly_revenue,
            is_empty_workspace=is_empty_workspace,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.post("/setup-demo")
    def setup_demo():
        result = seed_demo_data()
        flash(
            (
                "تم تجهيز بيانات تجريبية بنجاح "
                f"(مركبات: {result['vehicles']}, حجوزات: {result['reservations']}, "
                f"نقاط GPS: {result['gps_points']})."
            ),
            "success",
        )
        return redirect(url_for("dashboard"))

    @app.get("/reports")
    def reports():
        total_revenue = (
            db.session.query(func.coalesce(func.sum(Reservation.total_price), 0.0))
            .filter(Reservation.status.in_(REVENUE_STATUSES))
            .scalar()
        )
        reservation_totals = {
            "all": Reservation.query.count(),
            "open": Reservation.query.filter(
                Reservation.status.in_(OPEN_RESERVATION_STATUSES)
            ).count(),
            "completed": Reservation.query.filter_by(status="completed").count(),
            "cancelled": Reservation.query.filter_by(status="cancelled").count(),
        }

        fleet_totals = {
            "all": Vehicle.query.count(),
            "available": Vehicle.query.filter_by(status="available").count(),
            "rented": Vehicle.query.filter_by(status="rented").count(),
            "maintenance": Vehicle.query.filter_by(status="maintenance").count(),
        }

        branch_rows = []
        for branch in Branch.query.order_by(Branch.name.asc()).all():
            branch_vehicle_count = Vehicle.query.filter_by(branch_id=branch.id).count()
            branch_active_contracts = (
                db.session.query(func.count(Contract.id))
                .join(Reservation, Reservation.id == Contract.reservation_id)
                .filter(
                    Reservation.pickup_branch_id == branch.id,
                    Contract.status == "active",
                )
                .scalar()
            )
            branch_revenue = (
                db.session.query(func.coalesce(func.sum(Reservation.total_price), 0.0))
                .filter(
                    Reservation.pickup_branch_id == branch.id,
                    Reservation.status.in_(REVENUE_STATUSES),
                )
                .scalar()
            )
            branch_rows.append(
                {
                    "name": branch.name,
                    "city": branch.city,
                    "vehicles": branch_vehicle_count,
                    "active_contracts": branch_active_contracts,
                    "revenue": branch_revenue,
                }
            )

        active_contracts = (
            Contract.query.options(
                joinedload(Contract.vehicle),
                joinedload(Contract.reservation),
            )
            .filter(Contract.status == "active")
            .order_by(Contract.start_datetime.asc())
            .all()
        )

        return render_template(
            "reports.html",
            total_revenue=total_revenue,
            reservation_totals=reservation_totals,
            fleet_totals=fleet_totals,
            branch_rows=branch_rows,
            active_contracts=active_contracts,
        )

    @app.route("/branches", methods=["GET", "POST"])
    def branches():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            city = request.form.get("city", "").strip()
            if not name or not city:
                flash("اسم الفرع والمدينة مطلوبان.", "danger")
                return redirect(url_for("branches"))

            duplicate = Branch.query.filter(Branch.name.ilike(name)).first()
            if duplicate:
                flash("هذا الفرع موجود مسبقًا.", "danger")
                return redirect(url_for("branches"))

            db.session.add(Branch(name=name, city=city))
            db.session.commit()
            flash("تم إضافة الفرع بنجاح.", "success")
            return redirect(url_for("branches"))

        all_branches = Branch.query.order_by(Branch.name.asc()).all()
        return render_template("branches.html", branches=all_branches)

    @app.route("/vehicles", methods=["GET", "POST"])
    def vehicles():
        if request.method == "POST":
            try:
                plate_number = request.form.get("plate_number", "").strip().upper()
                make = request.form.get("make", "").strip()
                model = request.form.get("model", "").strip()
                year = int(request.form.get("year", "").strip())
                daily_rate = float(request.form.get("daily_rate", "").strip())
                status = request.form.get("status", "available").strip()
                odometer = int(request.form.get("odometer", "0").strip())
                branch_id = int(request.form.get("branch_id", "").strip())
                gps_identifier = request.form.get("gps_identifier", "").strip() or None
            except (TypeError, ValueError):
                flash("يرجى إدخال بيانات مركبة صحيحة.", "danger")
                return redirect(url_for("vehicles"))

            if not plate_number or not make or not model:
                flash("رقم اللوحة والشركة والموديل مطلوبة.", "danger")
                return redirect(url_for("vehicles"))
            if status not in VEHICLE_STATUSES:
                flash("حالة المركبة غير صحيحة.", "danger")
                return redirect(url_for("vehicles"))
            if year < 1990 or year > 2100:
                flash("سنة المركبة خارج النطاق المسموح.", "danger")
                return redirect(url_for("vehicles"))
            if daily_rate <= 0:
                flash("سعر اليوم يجب أن يكون أكبر من صفر.", "danger")
                return redirect(url_for("vehicles"))
            if odometer < 0:
                flash("عداد المسافة لا يمكن أن يكون سالبًا.", "danger")
                return redirect(url_for("vehicles"))

            branch = db.session.get(Branch, branch_id)
            if not branch:
                flash("الفرع المحدد غير موجود.", "danger")
                return redirect(url_for("vehicles"))

            if Vehicle.query.filter_by(plate_number=plate_number).first():
                flash("توجد مركبة بنفس رقم اللوحة.", "danger")
                return redirect(url_for("vehicles"))

            db.session.add(
                Vehicle(
                    plate_number=plate_number,
                    make=make,
                    model=model,
                    year=year,
                    daily_rate=daily_rate,
                    status=status,
                    odometer=odometer,
                    branch_id=branch_id,
                    gps_identifier=gps_identifier,
                )
            )
            db.session.commit()
            flash("تم إضافة المركبة بنجاح.", "success")
            return redirect(url_for("vehicles"))

        all_branches = Branch.query.order_by(Branch.name.asc()).all()
        all_vehicles = (
            Vehicle.query.options(joinedload(Vehicle.branch))
            .order_by(Vehicle.created_at.desc())
            .all()
        )
        return render_template(
            "vehicles.html",
            branches=all_branches,
            vehicles=all_vehicles,
            vehicle_statuses=VEHICLE_STATUSES,
        )

    @app.post("/vehicles/<int:vehicle_id>/status")
    def update_vehicle_status(vehicle_id):
        status = request.form.get("status", "").strip()
        if status not in VEHICLE_STATUSES:
            flash("حالة المركبة غير صحيحة.", "danger")
            return redirect(url_for("vehicles"))

        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            flash("المركبة غير موجودة.", "danger")
            return redirect(url_for("vehicles"))

        vehicle.status = status
        db.session.commit()
        flash("تم تحديث حالة المركبة.", "success")
        return redirect(url_for("vehicles"))

    @app.route("/reservations", methods=["GET", "POST"])
    def reservations():
        if request.method == "POST":
            try:
                customer_name = request.form.get("customer_name", "").strip()
                customer_phone = request.form.get("customer_phone", "").strip()
                vehicle_id = int(request.form.get("vehicle_id", "").strip())
                pickup_branch_id = int(request.form.get("pickup_branch_id", "").strip())
                dropoff_branch_id = int(request.form.get("dropoff_branch_id", "").strip())
                start_date = parse_date(request.form.get("start_date", "").strip())
                end_date = parse_date(request.form.get("end_date", "").strip())
                notes = request.form.get("notes", "").strip() or None
            except (TypeError, ValueError):
                flash("يرجى إدخال بيانات حجز صحيحة.", "danger")
                return redirect(url_for("reservations"))

            if not customer_name or not customer_phone:
                flash("اسم العميل ورقم الهاتف مطلوبان.", "danger")
                return redirect(url_for("reservations"))

            vehicle = db.session.get(Vehicle, vehicle_id)
            pickup_branch = db.session.get(Branch, pickup_branch_id)
            dropoff_branch = db.session.get(Branch, dropoff_branch_id)
            if not vehicle or not pickup_branch or not dropoff_branch:
                flash("يجب اختيار مركبة وفروع صحيحة.", "danger")
                return redirect(url_for("reservations"))
            if vehicle.status == "maintenance":
                flash("لا يمكن حجز مركبة في حالة الصيانة.", "danger")
                return redirect(url_for("reservations"))

            conflicting_reservation = Reservation.query.filter(
                Reservation.vehicle_id == vehicle_id,
                Reservation.status.in_(OPEN_RESERVATION_STATUSES),
                Reservation.start_date < end_date,
                Reservation.end_date > start_date,
            ).first()
            if conflicting_reservation:
                flash("المركبة محجوزة مسبقًا في هذه الفترة.", "danger")
                return redirect(url_for("reservations"))

            try:
                rental_days, total_price = calculate_total_price(
                    vehicle.daily_rate, start_date, end_date
                )
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("reservations"))

            reservation = Reservation(
                customer_name=customer_name,
                customer_phone=customer_phone,
                vehicle_id=vehicle_id,
                pickup_branch_id=pickup_branch_id,
                dropoff_branch_id=dropoff_branch_id,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                status="confirmed",
                notes=notes,
            )
            db.session.add(reservation)
            db.session.commit()
            flash(
                f"تم إنشاء الحجز ({rental_days} يوم، الإجمالي {total_price:.2f} ر.س).",
                "success",
            )
            return redirect(url_for("reservations"))

        all_vehicles = (
            Vehicle.query.options(joinedload(Vehicle.branch))
            .order_by(Vehicle.plate_number.asc())
            .all()
        )
        all_branches = Branch.query.order_by(Branch.name.asc()).all()
        all_reservations = (
            Reservation.query.options(
                joinedload(Reservation.vehicle),
                joinedload(Reservation.pickup_branch),
                joinedload(Reservation.dropoff_branch),
            )
            .order_by(Reservation.created_at.desc())
            .all()
        )
        return render_template(
            "reservations.html",
            vehicles=all_vehicles,
            branches=all_branches,
            reservations=all_reservations,
        )

    @app.post("/reservations/<int:reservation_id>/cancel")
    def cancel_reservation(reservation_id):
        reservation = db.session.get(Reservation, reservation_id)
        if not reservation:
            flash("الحجز غير موجود.", "danger")
            return redirect(url_for("reservations"))

        if reservation.status in ("completed", "cancelled", "active"):
            flash("لا يمكن إلغاء الحجز في حالته الحالية.", "danger")
            return redirect(url_for("reservations"))

        reservation.status = "cancelled"
        db.session.commit()
        flash("تم إلغاء الحجز.", "success")
        return redirect(url_for("reservations"))

    @app.route("/contracts", methods=["GET", "POST"])
    def contracts():
        if request.method == "POST":
            try:
                reservation_id = int(request.form.get("reservation_id", "").strip())
                start_odometer = int(request.form.get("start_odometer", "0").strip())
                fuel_out = int(request.form.get("fuel_out", "100").strip())
            except (TypeError, ValueError):
                flash("يرجى إدخال بيانات عقد صحيحة.", "danger")
                return redirect(url_for("contracts"))

            reservation = db.session.get(Reservation, reservation_id)
            if not reservation:
                flash("الحجز غير موجود.", "danger")
                return redirect(url_for("contracts"))
            if reservation.status != "confirmed":
                flash("يمكن بدء العقد للحجوزات المؤكدة فقط.", "danger")
                return redirect(url_for("contracts"))
            if reservation.contract:
                flash("يوجد عقد مسبق لهذا الحجز.", "danger")
                return redirect(url_for("contracts"))

            vehicle = db.session.get(Vehicle, reservation.vehicle_id)
            if not vehicle:
                flash("المركبة غير موجودة.", "danger")
                return redirect(url_for("contracts"))
            if start_odometer < vehicle.odometer:
                flash("عداد البداية لا يمكن أن يكون أقل من العداد الحالي.", "danger")
                return redirect(url_for("contracts"))
            if fuel_out < 0 or fuel_out > 100:
                flash("نسبة الوقود عند التسليم يجب أن تكون بين 0 و100.", "danger")
                return redirect(url_for("contracts"))

            contract = Contract(
                reservation_id=reservation.id,
                vehicle_id=vehicle.id,
                start_odometer=start_odometer,
                fuel_out=fuel_out,
                status="active",
            )
            vehicle.status = "rented"
            vehicle.odometer = start_odometer
            reservation.status = "active"
            db.session.add(contract)
            db.session.commit()

            gps_sync_result = sync_contract_to_gps_backend(contract, reservation, vehicle)
            flash("تم بدء العقد بنجاح.", "success")
            if gps_sync_result.get("ok"):
                flash("تمت مزامنة العقد مع GPS backend.", "info")
            elif not gps_sync_result.get("skipped"):
                flash(
                    f"تم بدء العقد محليًا لكن فشل الربط مع GPS backend: {gps_sync_result.get('message')}",
                    "warning",
                )
            else:
                flash(gps_sync_result.get("message"), "warning")
            return redirect(url_for("contracts"))

        eligible_reservations = (
            Reservation.query.options(joinedload(Reservation.vehicle))
            .filter(Reservation.status == "confirmed")
            .order_by(Reservation.start_date.asc())
            .all()
        )
        all_contracts = (
            Contract.query.options(
                joinedload(Contract.vehicle),
                joinedload(Contract.reservation),
            )
            .order_by(Contract.created_at.desc())
            .all()
        )
        return render_template(
            "contracts.html",
            reservations=eligible_reservations,
            contracts=all_contracts,
        )

    @app.get("/contracts/<int:contract_id>/gps-report")
    def contract_gps_report(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("العقد غير موجود.", "danger")
            return redirect(url_for("contracts"))

        result = load_contract_gps_report(contract.id)
        if not result.get("ok"):
            flash(
                f"تعذر تحميل تقرير GPS للعقد #{contract.id}: {result.get('message')}",
                "warning",
            )

        return render_template(
            "contract_gps_report.html",
            contract=contract,
            report=result.get("report"),
            integration_error=result.get("message") if not result.get("ok") else None,
            external_contract_id=result.get("external_contract_id"),
        )

    @app.post("/contracts/<int:contract_id>/close")
    def close_contract(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("العقد غير موجود.", "danger")
            return redirect(url_for("contracts"))
        if contract.status != "active":
            flash("يمكن إغلاق العقود النشطة فقط.", "danger")
            return redirect(url_for("contracts"))

        try:
            end_odometer = int(
                request.form.get("end_odometer", str(contract.start_odometer)).strip()
            )
            fuel_in = int(request.form.get("fuel_in", "100").strip())
        except (TypeError, ValueError):
            flash("يرجى إدخال قيم إغلاق صحيحة.", "danger")
            return redirect(url_for("contracts"))

        if end_odometer < contract.start_odometer:
            flash("عداد الإغلاق لا يمكن أن يكون أقل من عداد البداية.", "danger")
            return redirect(url_for("contracts"))
        if fuel_in < 0 or fuel_in > 100:
            flash("نسبة الوقود عند الاستلام يجب أن تكون بين 0 و100.", "danger")
            return redirect(url_for("contracts"))

        vehicle = db.session.get(Vehicle, contract.vehicle_id)
        reservation = db.session.get(Reservation, contract.reservation_id)
        if not vehicle or not reservation:
            flash("تعذر العثور على المركبة أو الحجز المرتبط بالعقد.", "danger")
            return redirect(url_for("contracts"))

        contract.end_datetime = utc_now()
        contract.end_odometer = end_odometer
        contract.fuel_in = fuel_in
        contract.status = "closed"
        contract.close_notes = request.form.get("close_notes", "").strip() or None

        vehicle.status = "available"
        vehicle.odometer = end_odometer
        reservation.status = "completed"

        db.session.commit()
        flash("تم إغلاق العقد وإرجاع المركبة إلى متاحة.", "success")

        gps_close_result = close_contract_in_gps_backend(contract.id)
        if gps_close_result.get("ok"):
            flash("تم إغلاق العقد في GPS backend.", "info")
        elif not gps_close_result.get("skipped"):
            flash(
                f"تم الإغلاق محليًا لكن فشل إغلاق GPS backend: {gps_close_result.get('message')}",
                "warning",
            )

        return redirect(url_for("contracts"))

    @app.post("/gps/sync")
    def sync_gps_from_backend():
        try:
            limit = int(request.form.get("limit", "300").strip())
            from_minutes = int(request.form.get("from_minutes", "20").strip())
        except ValueError:
            flash("قيم المزامنة غير صحيحة.", "danger")
            return redirect(url_for("gps"))

        result = sync_live_positions_from_backend(
            limit=max(limit, 50),
            from_minutes=max(from_minutes, 1),
        )
        if result.get("ok"):
            flash(
                (
                    "تمت مزامنة GPS بنجاح "
                    f"(تم الاستيراد: {result['imported']}, "
                    f"المكررة: {result['duplicates']}, "
                    f"غير المطابقة: {result['unmatched']})."
                ),
                "success",
            )
        else:
            flash(result.get("message") or "فشلت مزامنة GPS.", "warning")
        return redirect(url_for("gps"))

    @app.post("/gps/test-backend")
    def test_gps_backend_connection():
        response = call_gps_backend(method="GET", path="/health")
        if response.get("ok"):
            payload = response.get("data") or {}
            mysql_status = payload.get("mysql", "unknown")
            flash(
                f"اتصال GPS backend ناجح. حالة قاعدة البيانات: {mysql_status}.",
                "success",
            )
        else:
            flash(
                f"فشل الاتصال مع GPS backend: {response.get('error')}",
                "warning",
            )
        return redirect(url_for("gps"))

    @app.route("/gps", methods=["GET", "POST"])
    def gps():
        if request.method == "POST":
            try:
                vehicle_id = int(request.form.get("vehicle_id", "").strip())
                latitude = float(request.form.get("latitude", "").strip())
                longitude = float(request.form.get("longitude", "").strip())
                speed_kmh = float(request.form.get("speed_kmh", "0").strip())
            except (TypeError, ValueError):
                flash("يرجى إدخال قيم GPS صحيحة.", "danger")
                return redirect(url_for("gps"))

            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle:
                flash("المركبة غير موجودة.", "danger")
                return redirect(url_for("gps"))

            db.session.add(
                GpsPosition(
                    vehicle_id=vehicle_id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=max(speed_kmh, 0),
                    source="manual",
                )
            )
            db.session.commit()
            flash("تم تسجيل نقطة GPS بنجاح.", "success")
            return redirect(url_for("gps"))

        all_vehicles = Vehicle.query.order_by(Vehicle.plate_number.asc()).all()
        latest_positions = (
            GpsPosition.query.options(joinedload(GpsPosition.vehicle))
            .order_by(GpsPosition.recorded_at.desc())
            .limit(100)
            .all()
        )
        return render_template(
            "gps.html",
            vehicles=all_vehicles,
            positions=latest_positions,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
