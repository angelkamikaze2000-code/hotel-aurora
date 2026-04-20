from datetime import datetime

from flask import Blueprint, request

from ..models import Reservation, Room


rooms_bp = Blueprint("rooms", __name__)


ACTIVE_RESERVATION_STATUSES = {"pending", "confirmed", "paid"}


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return payload, status_code


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def room_is_available(room_id, check_in=None, check_out=None):
    room = Room.query.get(room_id)
    if not room or not room.is_available:
        return False

    if not check_in or not check_out:
        return room.is_available

    conflict_exists = (
        Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.check_in < check_out,
            Reservation.check_out > check_in,
        ).first()
        is not None
    )
    return not conflict_exists


@rooms_bp.get("")
def list_rooms():
    category = (request.args.get("category") or "").strip().lower()
    min_capacity = request.args.get("min_capacity", type=int)
    available_only = request.args.get("available_only", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    check_in = parse_iso_date(request.args.get("check_in"))
    check_out = parse_iso_date(request.args.get("check_out"))

    if (request.args.get("check_in") and not check_in) or (
        request.args.get("check_out") and not check_out
    ):
        return error_response("Las fechas deben enviarse en formato YYYY-MM-DD.")

    if check_in and check_out and check_out <= check_in:
        return error_response("La fecha de salida debe ser posterior al check-in.")

    query = Room.query.order_by(Room.price_per_night.asc(), Room.name.asc())
    if category:
        query = query.filter(Room.category == category)
    if min_capacity:
        query = query.filter(Room.capacity >= min_capacity)

    rooms = []
    for room in query.all():
        is_available = room_is_available(room.id, check_in, check_out)
        if available_only and not is_available:
            continue
        rooms.append(room.to_dict(is_available=is_available))

    return {"items": rooms, "total": len(rooms)}


@rooms_bp.get("/<int:room_id>")
def get_room(room_id):
    check_in = parse_iso_date(request.args.get("check_in"))
    check_out = parse_iso_date(request.args.get("check_out"))
    room = Room.query.get(room_id)

    if not room:
        return error_response("Habitacion no encontrada.", 404)

    if check_in and check_out and check_out <= check_in:
        return error_response("La fecha de salida debe ser posterior al check-in.")

    return {"room": room.to_dict(is_available=room_is_available(room.id, check_in, check_out))}


@rooms_bp.get("/availability")
def room_availability():
    check_in = parse_iso_date(request.args.get("check_in"))
    check_out = parse_iso_date(request.args.get("check_out"))
    room_id = request.args.get("room_id", type=int)
    category = (request.args.get("category") or "").strip().lower()
    min_capacity = request.args.get("min_capacity", type=int)

    if not check_in or not check_out:
        return error_response("Debe enviar check_in y check_out.")
    if check_out <= check_in:
        return error_response("La fecha de salida debe ser posterior al check-in.")

    if room_id:
        room = Room.query.get(room_id)
        if not room:
            return error_response("Habitacion no encontrada.", 404)
        return {
            "room_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "is_available": room_is_available(room_id, check_in, check_out),
        }

    query = Room.query
    if category:
        query = query.filter(Room.category == category)
    if min_capacity:
        query = query.filter(Room.capacity >= min_capacity)

    available_rooms = [
        room.to_dict(is_available=True)
        for room in query.all()
        if room_is_available(room.id, check_in, check_out)
    ]
    return {
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "items": available_rooms,
        "total": len(available_rooms),
    }
