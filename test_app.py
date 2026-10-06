"""
Unit and integration test suite for the ACEest Flask Web Application.
"""

from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import (
    app as flask_app,
    db,
    Client,
    Progress,
    Workout,
    calculate_target_calories,
    calculate_bmi_info,
    init_db,
)


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Configure and initialize application context for testing with an in-memory DB."""
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        db.create_all()
        init_db()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create test client instance for HTTP requests."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client: FlaskClient) -> FlaskClient:
    """Create an authenticated test client logged in as default admin user."""
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


# -----------------------------------------------------------------------------
# Business Logic & Helper Calculations Tests
# -----------------------------------------------------------------------------

def test_calculate_target_calories() -> None:
    """Test calorie target calculation based on program multipliers."""
    # Hypertrophy factor: 1.2 -> 70 * 22 * 1.2 = 1848.0
    assert calculate_target_calories(70.0, "Hypertrophy") == 1848.0
    # Fat Loss factor: 0.9 -> 80 * 22 * 0.9 = 1584.0
    assert calculate_target_calories(80.0, "Fat Loss") == 1584.0
    # Endurance factor: 1.1 -> 60 * 22 * 1.1 = 1452.0
    assert calculate_target_calories(60.0, "Endurance") == 1452.0
    # Fallback/Unknown program default factor: 1.0 -> 100 * 22 * 1.0 = 2200.0
    assert calculate_target_calories(100.0, "General") == 2200.0


def test_calculate_bmi_info() -> None:
    """Test BMI calculation and risk assessment classifications."""
    # Missing height edge cases
    bmi, risk = calculate_bmi_info(70.0, None)
    assert bmi is None
    assert risk == "Height context missing"

    bmi, risk = calculate_bmi_info(70.0, 0.0)
    assert bmi is None
    assert risk == "Height context missing"

    # Underweight classification (< 18.5)
    bmi, risk = calculate_bmi_info(45.0, 175.0)
    assert bmi == 14.69
    assert "Underweight" in risk

    # Normal weight classification (18.5 <= bmi < 25.0)
    bmi, risk = calculate_bmi_info(70.0, 175.0)
    assert bmi == 22.86
    assert "Normal weight" in risk

    # Overweight classification (25.0 <= bmi < 30.0)
    bmi, risk = calculate_bmi_info(80.0, 175.0)
    assert bmi == 26.12
    assert "Overweight" in risk

    # Obese classification (>= 30.0)
    bmi, risk = calculate_bmi_info(100.0, 175.0)
    assert bmi == 32.65
    assert "Obese" in risk


# -----------------------------------------------------------------------------
# Authentication & Access Control Tests
# -----------------------------------------------------------------------------

def test_login_success(client: FlaskClient) -> None:
    """Test successful user login with valid admin credentials."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"ACEest Fitness Management Portal" in response.data


def test_login_failure(client: FlaskClient) -> None:
    """Test login failure with invalid credentials."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid credentials." in response.data


def test_logout(authenticated_client: FlaskClient) -> None:
    """Test session clearance on logout."""
    response = authenticated_client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"System Login" in response.data


def test_dashboard_unauthenticated_redirect(client: FlaskClient) -> None:
    """Test unauthenticated dashboard access redirects to login."""
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"System Login" in response.data


# -----------------------------------------------------------------------------
# Client Profile CRUD Tests
# -----------------------------------------------------------------------------

def test_save_client_create(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test creating a new client profile."""
    response = authenticated_client.post(
        "/clients/save",
        data={
            "name": "Alex Turner",
            "age": "32",
            "weight": "78.5",
            "height": "182.0",
            "target_weight": "75.0",
            "target_adherence": "90.0",
            "program": "Hypertrophy",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Alex Turner" in response.data

    with app.app_context():
        created = Client.query.filter_by(name="Alex Turner").first()
        assert created is not None
        assert created.age == 32
        assert created.weight == 78.5
        assert created.program == "Hypertrophy"


def test_save_client_update(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test updating an existing client profile."""
    with app.app_context():
        existing = Client(name="Sam Miller", age=28, weight=65.0, program="Fat Loss")
        db.session.add(existing)
        db.session.commit()
        client_id = existing.id

    response = authenticated_client.post(
        "/clients/save",
        data={
            "client_id": str(client_id),
            "name": "Sam Miller Updated",
            "age": "29",
            "weight": "63.0",
            "height": "170.0",
            "target_weight": "60.0",
            "target_adherence": "95.0",
            "program": "Fat Loss",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Sam Miller Updated" in response.data

    with app.app_context():
        updated = Client.query.get(client_id)
        assert updated is not None
        assert updated.name == "Sam Miller Updated"
        assert updated.weight == 63.0


# -----------------------------------------------------------------------------
# Adherence Logging & AI Routine Generation Tests
# -----------------------------------------------------------------------------

def test_log_adherence(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test logging weekly percentage adherence."""
    with app.app_context():
        test_client = Client(name="Tracker Client", age=30, weight=80.0, program="Endurance")
        db.session.add(test_client)
        db.session.commit()
        client_id = test_client.id

    response = authenticated_client.post(
        f"/clients/{client_id}/log-adherence",
        data={"adherence": "88.5"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        log = Progress.query.filter_by(client_id=client_id).first()
        assert log is not None
        assert log.adherence == 88.5


def test_generate_ai_program(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test generating an AI workout routine template."""
    with app.app_context():
        test_client = Client(name="Routine Client", age=26, weight=72.0, program="Hypertrophy")
        db.session.add(test_client)
        db.session.commit()
        client_id = test_client.id

    response = authenticated_client.get(
        f"/clients/{client_id}/ai-generate",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        workout = Workout.query.filter_by(client_id=client_id).first()
        assert workout is not None
        assert "Hypertrophy" in workout.workout_type


# -----------------------------------------------------------------------------
# Visualization & Export Tests
# -----------------------------------------------------------------------------

def test_progress_chart_rendering(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test dynamic generation and streaming of Matplotlib progress chart PNG."""
    with app.app_context():
        test_client = Client(name="Visual Client", age=31, weight=75.0, program="Fat Loss")
        db.session.add(test_client)
        db.session.commit()
        client_id = test_client.id

        log = Progress(client_id=client_id, week_date="Week 1", adherence=82.0)
        db.session.add(log)
        db.session.commit()

    response = authenticated_client.get(f"/clients/{client_id}/progress-chart.png")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert len(response.data) > 0


def test_export_pdf_report(authenticated_client: FlaskClient, app: Flask) -> None:
    """Test exporting client summary as a downloadable PDF document."""
    with app.app_context():
        test_client = Client(
            name="PDF Client",
            age=45,
            weight=88.0,
            height=178.0,
            program="Endurance",
        )
        db.session.add(test_client)
        db.session.commit()
        client_id = test_client.id

    response = authenticated_client.get(f"/clients/{client_id}/export-pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
