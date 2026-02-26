import os
from datetime import datetime, timezone

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload

db = SQLAlchemy()

VEHICLE_STATUSES = ("available", "rented", "maintenance")
OPEN_RESERVATION_STATUSES = ("pending", "confirmed", "active")


def utc_now():
    return datetime.now(timezone.utc)


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
        raise ValueError("End date must be after start date.")
    return rental_days, round(daily_rate * rental_days, 2)


def seed_initial_data():
    if Branch.query.count() == 0:
        db.session.add(Branch(name="Main Branch", city="Riyadh"))
        db.session.commit()


def create_app(database_uri=None, testing=False):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_uri(app, database_uri)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    @app.get("/")
    def dashboard():
        totals = {
            "branches": Branch.query.count(),
            "vehicles": Vehicle.query.count(),
            "available_vehicles": Vehicle.query.filter_by(status="available").count(),
            "active_contracts": Contract.query.filter_by(status="active").count(),
            "open_reservations": Reservation.query.filter(
                Reservation.status.in_(OPEN_RESERVATION_STATUSES)
            ).count(),
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
        return render_template(
            "dashboard.html",
            totals=totals,
            upcoming_reservations=upcoming_reservations,
            latest_positions=latest_positions,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.route("/branches", methods=["GET", "POST"])
    def branches():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            city = request.form.get("city", "").strip()
            if not name or not city:
                flash("Branch name and city are required.", "danger")
                return redirect(url_for("branches"))

            duplicate = Branch.query.filter(Branch.name.ilike(name)).first()
            if duplicate:
                flash("Branch already exists.", "danger")
                return redirect(url_for("branches"))

            db.session.add(Branch(name=name, city=city))
            db.session.commit()
            flash("Branch added successfully.", "success")
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
                flash("Please provide valid vehicle values.", "danger")
                return redirect(url_for("vehicles"))

            if not plate_number or not make or not model:
                flash("Plate, make and model are required.", "danger")
                return redirect(url_for("vehicles"))
            if status not in VEHICLE_STATUSES:
                flash("Vehicle status is invalid.", "danger")
                return redirect(url_for("vehicles"))
            if year < 1990 or year > 2100:
                flash("Vehicle year is out of range.", "danger")
                return redirect(url_for("vehicles"))
            if daily_rate <= 0:
                flash("Daily rate must be greater than zero.", "danger")
                return redirect(url_for("vehicles"))
            if odometer < 0:
                flash("Odometer cannot be negative.", "danger")
                return redirect(url_for("vehicles"))

            branch = db.session.get(Branch, branch_id)
            if not branch:
                flash("Selected branch does not exist.", "danger")
                return redirect(url_for("vehicles"))

            if Vehicle.query.filter_by(plate_number=plate_number).first():
                flash("Vehicle with this plate already exists.", "danger")
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
            flash("Vehicle added successfully.", "success")
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
            flash("Vehicle status is invalid.", "danger")
            return redirect(url_for("vehicles"))

        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            flash("Vehicle not found.", "danger")
            return redirect(url_for("vehicles"))

        vehicle.status = status
        db.session.commit()
        flash("Vehicle status updated.", "success")
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
                flash("Please provide valid reservation values.", "danger")
                return redirect(url_for("reservations"))

            if not customer_name or not customer_phone:
                flash("Customer name and phone are required.", "danger")
                return redirect(url_for("reservations"))

            vehicle = db.session.get(Vehicle, vehicle_id)
            pickup_branch = db.session.get(Branch, pickup_branch_id)
            dropoff_branch = db.session.get(Branch, dropoff_branch_id)
            if not vehicle or not pickup_branch or not dropoff_branch:
                flash("Vehicle and branches must exist.", "danger")
                return redirect(url_for("reservations"))
            if vehicle.status == "maintenance":
                flash("Vehicle in maintenance cannot be reserved.", "danger")
                return redirect(url_for("reservations"))

            conflicting_reservation = Reservation.query.filter(
                Reservation.vehicle_id == vehicle_id,
                Reservation.status.in_(OPEN_RESERVATION_STATUSES),
                Reservation.start_date < end_date,
                Reservation.end_date > start_date,
            ).first()
            if conflicting_reservation:
                flash("Vehicle is already reserved for this period.", "danger")
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
                f"Reservation created ({rental_days} days, total {total_price:.2f} SAR).",
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
            flash("Reservation not found.", "danger")
            return redirect(url_for("reservations"))

        if reservation.status in ("completed", "cancelled", "active"):
            flash("Reservation cannot be cancelled in current state.", "danger")
            return redirect(url_for("reservations"))

        reservation.status = "cancelled"
        db.session.commit()
        flash("Reservation cancelled.", "success")
        return redirect(url_for("reservations"))

    @app.route("/contracts", methods=["GET", "POST"])
    def contracts():
        if request.method == "POST":
            try:
                reservation_id = int(request.form.get("reservation_id", "").strip())
                start_odometer = int(request.form.get("start_odometer", "0").strip())
                fuel_out = int(request.form.get("fuel_out", "100").strip())
            except (TypeError, ValueError):
                flash("Please provide valid contract values.", "danger")
                return redirect(url_for("contracts"))

            reservation = db.session.get(Reservation, reservation_id)
            if not reservation:
                flash("Reservation not found.", "danger")
                return redirect(url_for("contracts"))
            if reservation.status != "confirmed":
                flash("Only confirmed reservations can be converted to contracts.", "danger")
                return redirect(url_for("contracts"))
            if reservation.contract:
                flash("Contract already exists for this reservation.", "danger")
                return redirect(url_for("contracts"))

            vehicle = db.session.get(Vehicle, reservation.vehicle_id)
            if not vehicle:
                flash("Vehicle not found.", "danger")
                return redirect(url_for("contracts"))
            if start_odometer < vehicle.odometer:
                flash("Start odometer cannot be lower than current odometer.", "danger")
                return redirect(url_for("contracts"))
            if fuel_out < 0 or fuel_out > 100:
                flash("Fuel out must be from 0 to 100.", "danger")
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
            flash("Contract started successfully.", "success")
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

    @app.post("/contracts/<int:contract_id>/close")
    def close_contract(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("Contract not found.", "danger")
            return redirect(url_for("contracts"))
        if contract.status != "active":
            flash("Only active contracts can be closed.", "danger")
            return redirect(url_for("contracts"))

        try:
            end_odometer = int(
                request.form.get("end_odometer", str(contract.start_odometer)).strip()
            )
            fuel_in = int(request.form.get("fuel_in", "100").strip())
        except (TypeError, ValueError):
            flash("Please provide valid closing values.", "danger")
            return redirect(url_for("contracts"))

        if end_odometer < contract.start_odometer:
            flash("End odometer cannot be lower than start odometer.", "danger")
            return redirect(url_for("contracts"))
        if fuel_in < 0 or fuel_in > 100:
            flash("Fuel in must be from 0 to 100.", "danger")
            return redirect(url_for("contracts"))

        vehicle = db.session.get(Vehicle, contract.vehicle_id)
        reservation = db.session.get(Reservation, contract.reservation_id)
        if not vehicle or not reservation:
            flash("Missing linked vehicle or reservation.", "danger")
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
        flash("Contract closed and vehicle returned to available.", "success")
        return redirect(url_for("contracts"))

    @app.route("/gps", methods=["GET", "POST"])
    def gps():
        if request.method == "POST":
            try:
                vehicle_id = int(request.form.get("vehicle_id", "").strip())
                latitude = float(request.form.get("latitude", "").strip())
                longitude = float(request.form.get("longitude", "").strip())
                speed_kmh = float(request.form.get("speed_kmh", "0").strip())
            except (TypeError, ValueError):
                flash("Please provide valid GPS values.", "danger")
                return redirect(url_for("gps"))

            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle:
                flash("Vehicle does not exist.", "danger")
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
            flash("GPS point recorded.", "success")
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
