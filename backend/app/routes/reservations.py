from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import Reservation, ReservationService, Room, User
from .rooms import room_is_available


reservations_bp = Blueprint("reservations", __name__)


TAX_RATE = Decimal("0.18")


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return payload, status_code


def parse_iso_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def normalize_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def normalize_int(value, default=0, minimum=0):
    try:
        return max(int(value), minimum)
    except (TypeError, ValueError):
        return default


def build_reservation_code():
    return f"AUR-{uuid4().hex[:8].upper()}"


def find_or_create_guest(data):
    email = str(data.get("email", "")).strip().lower()
    user = User.query.filter_by(email=email).first()
    if user:
        user.first_name = str(data.get("first_name", user.first_name)).strip() or user.first_name
        user.last_name = str(data.get("last_name", user.last_name)).strip() or user.last_name
        user.phone = str(data.get("phone", user.phone or "")).strip() or user.phone
        return user

    user = User(
        first_name=str(data.get("first_name", "")).strip(),
        last_name=str(data.get("last_name", "")).strip(),
        email=email,
        phone=str(data.get("phone", "")).strip() or None,
        role="guest",
    )
    user.set_password(uuid4().hex)
    db.session.add(user)
    db.session.flush()
    return user


@reservations_bp.post("")
def create_reservation():
    data = request.get_json(silent=True) or {}
    errors = {}

    required_fields = {
        "first_name": "El nombre es obligatorio.",
        "last_name": "El apellido es obligatorio.",
        "email": "El correo es obligatorio.",
        "room_id": "La habitacion es obligatoria.",
        "check_in": "La fecha de check-in es obligatoria.",
        "check_out": "La fecha de check-out es obligatoria.",
        "country": "El pais es obligatorio.",
        "document_id": "El documento es obligatorio.",
    }
    for field, message in required_fields.items():
        if not str(data.get(field, "")).strip():
            errors[field] = message

    email = str(data.get("email", "")).strip().lower()
    if email and "@" not in email:
        errors["email"] = "Ingrese un correo valido."

    room_id = data.get("room_id")
    check_in = parse_iso_date(data.get("check_in"))
    check_out = parse_iso_date(data.get("check_out"))
    adults = normalize_int(data.get("adults", 1) or 1, default=1, minimum=1)
    children = normalize_int(data.get("children", 0) or 0, default=0, minimum=0)

    if data.get("check_in") and not check_in:
        errors["check_in"] = "Fecha de check-in invalida."
    if data.get("check_out") and not check_out:
        errors["check_out"] = "Fecha de check-out invalida."
    if check_in and check_out and check_out <= check_in:
        errors["check_out"] = "La fecha de salida debe ser posterior al check-in."

    room = Room.query.get(room_id) if room_id else None
    if room_id and not room:
        errors["room_id"] = "Habitacion no encontrada."
    elif room and adults + children > room.capacity:
        errors["capacity"] = "La habitacion no soporta la cantidad de huespedes indicada."

    services_payload = data.get("services") or []
    normalized_services = []
    if services_payload:
        if not isinstance(services_payload, list):
            errors["services"] = "Los servicios deben enviarse como una lista."
        else:
            for index, service in enumerate(services_payload):
                if not isinstance(service, dict):
                    errors[f"services[{index}]"] = "Servicio invalido."
                    continue
                name = str(service.get("name", "")).strip()
                price = normalize_decimal(service.get("price", 0))
                if not name:
                    errors[f"services[{index}].name"] = "El nombre del servicio es obligatorio."
                if price is None or price < 0:
                    errors[f"services[{index}].price"] = "El precio del servicio es invalido."
                if name and price is not None and price >= 0:
                    normalized_services.append({"name": name, "price": price})

    if errors:
        return error_response("Datos de reserva invalidos.", 400, errors)

    if not room.is_available or not room_is_available(room.id, check_in, check_out):
        return error_response("La habitacion no esta disponible para las fechas seleccionadas.", 409)

    nights = (check_out - check_in).days
    room_total = Decimal(room.price_per_night) * nights
    services_total = sum((service["price"] for service in normalized_services), Decimal("0.00"))
    subtotal = (room_total + services_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxes = (subtotal * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + taxes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    user = find_or_create_guest(data)
    reservation = Reservation(
        user_id=user.id,
        room_id=room.id,
        reservation_code=build_reservation_code(),
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        country=str(data.get("country", "")).strip(),
        document_id=str(data.get("document_id", "")).strip(),
        travel_reason=str(data.get("travel_reason", "")).strip() or None,
        special_requests=str(data.get("special_requests", "")).strip() or None,
        status="pending",
        subtotal=subtotal,
        taxes=taxes,
        total=total,
    )
    db.session.add(reservation)
    db.session.flush()

    for service in normalized_services:
        db.session.add(
            ReservationService(
                reservation_id=reservation.id,
                name=service["name"],
                price=service["price"],
            )
        )

    db.session.commit()
    return {
        "message": "Reserva creada correctamente.",
        "reservation": reservation.to_dict(),
    }, 201


@reservations_bp.get("/<int:reservation_id>")
def get_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return error_response("Reserva no encontrada.", 404)
    return {"reservation": reservation.to_dict()}


@reservations_bp.get("/mine")
@jwt_required()
def list_my_reservations():
    user_id = get_jwt_identity()
    reservations = (
        Reservation.query.filter_by(user_id=user_id)
        .order_by(Reservation.created_at.desc())
        .all()
    )
    return {"items": [reservation.to_dict() for reservation in reservations], "total": len(reservations)}
