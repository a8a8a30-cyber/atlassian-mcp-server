import os
import tempfile
import unittest

from app import Branch, Contract, GpsPosition, Reservation, Vehicle, create_app, db


class CarRentalMvpTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app(
            database_uri=f"sqlite:///{self.db_path}",
            testing=True,
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            main_branch = Branch.query.first()
            second_branch = Branch(name="Airport Branch", city="Jeddah")
            db.session.add(second_branch)
            db.session.flush()

            vehicle = Vehicle(
                plate_number="ABC123",
                make="Toyota",
                model="Camry",
                year=2023,
                daily_rate=150,
                status="available",
                odometer=10000,
                branch_id=main_branch.id,
                gps_identifier="GPS-1",
            )
            db.session.add(vehicle)
            db.session.commit()

            self.main_branch_id = main_branch.id
            self.second_branch_id = second_branch.id
            self.vehicle_id = vehicle.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _create_reservation(self, start_date: str, end_date: str):
        return self.client.post(
            "/reservations",
            data={
                "customer_name": "Test Customer",
                "customer_phone": "0500000000",
                "vehicle_id": str(self.vehicle_id),
                "pickup_branch_id": str(self.main_branch_id),
                "dropoff_branch_id": str(self.second_branch_id),
                "start_date": start_date,
                "end_date": end_date,
                "notes": "",
            },
            follow_redirects=True,
        )

    def _start_contract(self):
        self._create_reservation("2026-03-10", "2026-03-12")
        with self.app.app_context():
            reservation = Reservation.query.one()
        response = self.client.post(
            "/contracts",
            data={
                "reservation_id": str(reservation.id),
                "start_odometer": "10010",
                "fuel_out": "95",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            return Contract.query.one()

    def test_create_reservation_calculates_price(self):
        response = self._create_reservation("2026-03-01", "2026-03-04")
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            reservation = Reservation.query.one()
            self.assertEqual(reservation.total_price, 450.0)
            self.assertEqual(reservation.status, "confirmed")

    def test_prevent_overlapping_reservation(self):
        first = self._create_reservation("2026-03-01", "2026-03-05")
        self.assertEqual(first.status_code, 200)

        second = self._create_reservation("2026-03-03", "2026-03-06")
        self.assertEqual(second.status_code, 200)

        with self.app.app_context():
            self.assertEqual(Reservation.query.count(), 1)

    def test_close_contract_returns_vehicle_available(self):
        contract = self._start_contract()

        with self.app.app_context():
            active_contract = db.session.get(Contract, contract.id)
            self.assertEqual(active_contract.status, "active")
            vehicle = db.session.get(Vehicle, self.vehicle_id)
            reservation = db.session.get(Reservation, active_contract.reservation_id)
            self.assertEqual(vehicle.status, "rented")
            self.assertEqual(reservation.status, "active")

        response = self.client.post(
            f"/contracts/{contract.id}/close",
            data={
                "end_odometer": "10125",
                "fuel_in": "80",
                "close_notes": "Returned in good condition",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            updated_contract = db.session.get(Contract, contract.id)
            updated_vehicle = db.session.get(Vehicle, self.vehicle_id)
            updated_reservation = db.session.get(Reservation, reservation.id)
            self.assertEqual(updated_contract.status, "closed")
            self.assertEqual(updated_vehicle.status, "available")
            self.assertEqual(updated_vehicle.odometer, 10125)
            self.assertEqual(updated_reservation.status, "completed")

    def test_save_gps_position(self):
        response = self.client.post(
            "/gps",
            data={
                "vehicle_id": str(self.vehicle_id),
                "latitude": "24.7136",
                "longitude": "46.6753",
                "speed_kmh": "82",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            position = GpsPosition.query.one()
            self.assertEqual(position.vehicle_id, self.vehicle_id)
            self.assertEqual(position.speed_kmh, 82.0)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_reports_endpoint(self):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)

    def test_setup_demo_endpoint(self):
        response = self.client.post("/setup-demo", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertGreaterEqual(Vehicle.query.count(), 4)
            self.assertGreaterEqual(Reservation.query.count(), 2)

    def test_contract_gps_report_page_when_backend_disabled(self):
        contract = self._start_contract()
        response = self.client.get(
            f"/contracts/{contract.id}/gps-report",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_gps_sync_route_when_backend_disabled(self):
        response = self.client.post(
            "/gps/sync",
            data={"limit": "100", "from_minutes": "15"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_gps_backend_test_route_when_backend_disabled(self):
        response = self.client.post(
            "/gps/test-backend",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
