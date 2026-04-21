from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import re
from uuid import uuid4

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import Ad, AdPlan, Payment, Reservation, ReservationService, Room, User


admin_bp = Blueprint("admin", __name__)


ALLOWED_RESERVATION_STATUSES = {"pending", "confirmed", "paid", "cancelled", "completed"}
ALLOWED_AD_STATUSES = {"pending_payment", "active", "paused", "archived"}
ALLOWED_USER_ROLES = {"guest", "admin"}
TAX_RATE = Decimal("0.18")


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return payload, status_code


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def parse_iso_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def normalize_int(value, default=0, minimum=0):
    try:
        return max(int(value), minimum)
    except (TypeError, ValueError):
        return default


def build_reservation_code():
    return f"AUR-{uuid4().hex[:8].upper()}"


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "si"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


def slugify(value):
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return normalized.strip("-")


def get_current_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return None, error_response("Usuario no encontrado.", 404)
    if user.role != "admin":
        return None, error_response("No tiene permisos de administrador.", 403)
    return user, None


def reservation_summary(reservation):
    return {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "room_id": reservation.room_id,
        "reservation_code": reservation.reservation_code,
        "status": reservation.status,
        "check_in": reservation.check_in.isoformat() if reservation.check_in else None,
        "check_out": reservation.check_out.isoformat() if reservation.check_out else None,
        "adults": reservation.adults,
        "children": reservation.children,
        "country": reservation.country,
        "document_id": reservation.document_id,
        "travel_reason": reservation.travel_reason,
        "special_requests": reservation.special_requests,
        "total": float(reservation.total or 0),
        "subtotal": float(reservation.subtotal or 0),
        "taxes": float(reservation.taxes or 0),
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
        "guest_name": (
            f"{reservation.user.first_name} {reservation.user.last_name}".strip()
            if reservation.user
            else "Sin huesped"
        ),
        "guest_first_name": reservation.user.first_name if reservation.user else None,
        "guest_last_name": reservation.user.last_name if reservation.user else None,
        "guest_email": reservation.user.email if reservation.user else None,
        "guest_phone": reservation.user.phone if reservation.user else None,
        "room_name": reservation.room.name if reservation.room else None,
        "services": [
            {"id": service.id, "name": service.name, "price": float(service.price or 0)}
            for service in reservation.services
        ],
    }


def room_summary(room):
    return {
        "id": room.id,
        "name": room.name,
        "slug": room.slug,
        "category": room.category,
        "description": room.description,
        "price_per_night": float(room.price_per_night or 0),
        "capacity": room.capacity,
        "size_m2": room.size_m2,
        "bed_type": room.bed_type,
        "is_available": room.is_available,
        "featured_image": room.featured_image,
        "updated_at": room.updated_at.isoformat() if room.updated_at else None,
    }


def ad_summary(ad):
    return {
        "id": ad.id,
        "ad_plan_id": ad.ad_plan_id,
        "title": ad.title,
        "company_name": ad.company_name,
        "contact_name": ad.contact_name,
        "contact_email": ad.contact_email,
        "contact_phone": ad.contact_phone,
        "category": ad.category,
        "description": ad.description,
        "status": ad.status,
        "is_paid": ad.is_paid,
        "plan_name": ad.plan.name if ad.plan else None,
        "plan_price": float(ad.plan.price or 0) if ad.plan else 0,
        "starts_at": ad.starts_at.isoformat() if ad.starts_at else None,
        "ends_at": ad.ends_at.isoformat() if ad.ends_at else None,
        "created_at": ad.created_at.isoformat() if ad.created_at else None,
    }


def user_summary(user):
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def reservation_conflict_exists(room_id, check_in, check_out, reservation_id=None):
    query = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(["pending", "confirmed", "paid", "completed"]),
        Reservation.check_in < check_out,
        Reservation.check_out > check_in,
    )
    if reservation_id:
        query = query.filter(Reservation.id != reservation_id)
    return query.first() is not None


def find_or_create_guest_from_admin(data, existing_user_id=None):
    if existing_user_id:
        user = User.query.get(existing_user_id)
        if not user:
            return None, {"user_id": "Usuario no encontrado."}
    else:
        email = str(data.get("email", "")).strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                first_name=str(data.get("first_name", "")).strip(),
                last_name=str(data.get("last_name", "")).strip(),
                email=email,
                phone=str(data.get("phone", "")).strip() or None,
                role="guest",
                is_active=True,
            )
            user.set_password(uuid4().hex)
            db.session.add(user)
            db.session.flush()

    user.first_name = str(data.get("first_name", user.first_name)).strip() or user.first_name
    user.last_name = str(data.get("last_name", user.last_name)).strip() or user.last_name
    email = str(data.get("email", user.email)).strip().lower()
    if email:
        duplicate = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate:
            return None, {"email": "Ya existe otro usuario con ese correo."}
        user.email = email
    user.phone = str(data.get("phone", user.phone or "")).strip() or user.phone
    return user, {}


def validate_services_payload(services_payload):
    errors = {}
    normalized_services = []

    if not services_payload:
        return normalized_services, errors
    if not isinstance(services_payload, list):
        return normalized_services, {"services": "Los servicios deben enviarse como una lista."}

    for index, service in enumerate(services_payload):
        if not isinstance(service, dict):
            errors[f"services[{index}]"] = "Servicio invalido."
            continue
        name = str(service.get("name", "")).strip()
        price = money(service.get("price", 0))
        if not name:
            errors[f"services[{index}].name"] = "El nombre del servicio es obligatorio."
        if price is None or price < 0:
            errors[f"services[{index}].price"] = "El precio del servicio es invalido."
        if name and price is not None and price >= 0:
            normalized_services.append({"name": name, "price": price})

    return normalized_services, errors


def validate_reservation_payload(data, reservation=None):
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
        if reservation is None and not str(data.get(field, "")).strip():
            errors[field] = message

    email = str(data.get("email", reservation.user.email if reservation and reservation.user else "")).strip().lower()
    if email and "@" not in email:
        errors["email"] = "Ingrese un correo valido."

    room_id = data.get("room_id", reservation.room_id if reservation else None)
    room = Room.query.get(room_id) if room_id else None
    if room_id and not room:
        errors["room_id"] = "Habitacion no encontrada."

    check_in = parse_iso_date(data.get("check_in", reservation.check_in.isoformat() if reservation and reservation.check_in else None))
    check_out = parse_iso_date(data.get("check_out", reservation.check_out.isoformat() if reservation and reservation.check_out else None))

    if data.get("check_in") and not check_in:
        errors["check_in"] = "Fecha de check-in invalida."
    if data.get("check_out") and not check_out:
        errors["check_out"] = "Fecha de check-out invalida."
    if check_in and check_out and check_out <= check_in:
        errors["check_out"] = "La fecha de salida debe ser posterior al check-in."

    adults = normalize_int(data.get("adults", reservation.adults if reservation else 1), default=1, minimum=1)
    children = normalize_int(data.get("children", reservation.children if reservation else 0), default=0, minimum=0)
    if room and adults + children > room.capacity:
        errors["capacity"] = "La habitacion no soporta la cantidad de huespedes indicada."

    if room and check_in and check_out:
        if not room.is_available:
            errors["room_id"] = "La habitacion no esta disponible."
        elif reservation_conflict_exists(room.id, check_in, check_out, reservation.id if reservation else None):
            errors["availability"] = "La habitacion ya tiene una reserva en ese rango de fechas."

    services, service_errors = validate_services_payload(data.get("services", [s.to_dict() for s in reservation.services] if reservation else []))
    errors.update(service_errors)

    return {
        "errors": errors,
        "email": email,
        "room": room,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
        "services": services,
    }


def recalculate_reservation_totals(room, check_in, check_out, services):
    nights = (check_out - check_in).days
    room_total = Decimal(room.price_per_night) * nights
    services_total = sum((service["price"] for service in services), Decimal("0.00"))
    subtotal = (room_total + services_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxes = (subtotal * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + taxes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return subtotal, taxes, total


def sync_reservation_services(reservation, services):
    reservation.services.clear()
    for service in services:
        reservation.services.append(
            ReservationService(name=service["name"], price=service["price"])
        )


def validate_room_payload(data, room=None):
    errors = {}
    required_fields = ("name", "category", "description", "price_per_night", "capacity", "size_m2", "bed_type")

    for field in required_fields:
        if room is None and not str(data.get(field, "")).strip():
            errors[field] = "Este campo es obligatorio."

    slug = str(data.get("slug", "")).strip().lower() or slugify(data.get("name"))
    if not slug:
        errors["slug"] = "No se pudo generar un slug valido."

    price = None
    if "price_per_night" in data or room is None:
        price = money(data.get("price_per_night"))
        if price is None or price < 0:
            errors["price_per_night"] = "El precio por noche es invalido."

    capacity = room.capacity if room else None
    if "capacity" in data or room is None:
        try:
            capacity = int(data.get("capacity"))
            if capacity < 1:
                raise ValueError
        except (TypeError, ValueError):
            errors["capacity"] = "La capacidad debe ser un entero mayor a 0."

    size_m2 = room.size_m2 if room else None
    if "size_m2" in data or room is None:
        try:
            size_m2 = int(data.get("size_m2"))
            if size_m2 < 1:
                raise ValueError
        except (TypeError, ValueError):
            errors["size_m2"] = "El tamano debe ser un entero mayor a 0."

    slug_query = Room.query.filter(Room.slug == slug)
    if room:
        slug_query = slug_query.filter(Room.id != room.id)
    if slug and slug_query.first():
        errors["slug"] = "Ya existe una habitacion con ese slug."

    return {
        "errors": errors,
        "slug": slug,
        "price_per_night": price,
        "capacity": capacity,
        "size_m2": size_m2,
    }


def apply_room_changes(room, data, normalized):
    room.name = str(data.get("name", room.name)).strip() or room.name
    room.slug = normalized["slug"]
    room.category = str(data.get("category", room.category)).strip().lower() or room.category
    room.description = str(data.get("description", room.description)).strip() or room.description
    if normalized["price_per_night"] is not None:
        room.price_per_night = normalized["price_per_night"]
    room.capacity = normalized["capacity"]
    room.size_m2 = normalized["size_m2"]
    room.bed_type = str(data.get("bed_type", room.bed_type)).strip() or room.bed_type
    room.featured_image = str(data.get("featured_image", room.featured_image or "")).strip() or None
    next_is_available = parse_bool(data.get("is_available"))
    if next_is_available is not None:
        room.is_available = next_is_available


def validate_ad_payload(data, ad=None):
    errors = {}
    required_fields = (
        "title",
        "company_name",
        "contact_name",
        "contact_email",
        "contact_phone",
        "category",
    )
    for field in required_fields:
        if ad is None and not str(data.get(field, "")).strip():
            errors[field] = "Este campo es obligatorio."

    email = str(data.get("contact_email", ad.contact_email if ad else "")).strip().lower()
    if email and "@" not in email:
        errors["contact_email"] = "Ingrese un correo valido."

    plan_id = data.get("ad_plan_id", ad.ad_plan_id if ad else None)
    plan = AdPlan.query.get(plan_id) if plan_id else None
    if ad is None and not plan:
        errors["ad_plan_id"] = "Debe seleccionar un plan valido."
    if plan_id and not plan:
        errors["ad_plan_id"] = "Plan publicitario no encontrado."

    return {"errors": errors, "plan": plan, "email": email}


def apply_ad_changes(ad, data, normalized):
    if normalized["plan"] is not None:
        ad.ad_plan_id = normalized["plan"].id
    ad.title = str(data.get("title", ad.title)).strip() or ad.title
    ad.company_name = str(data.get("company_name", ad.company_name)).strip() or ad.company_name
    ad.contact_name = str(data.get("contact_name", ad.contact_name)).strip() or ad.contact_name
    ad.contact_email = normalized["email"] or ad.contact_email
    ad.contact_phone = str(data.get("contact_phone", ad.contact_phone)).strip() or ad.contact_phone
    ad.category = str(data.get("category", ad.category)).strip().lower() or ad.category
    ad.description = str(data.get("description", ad.description or "")).strip() or None
    next_status = str(data.get("status", ad.status)).strip().lower() or ad.status
    next_is_paid = parse_bool(data.get("is_paid"))

    if next_status in ALLOWED_AD_STATUSES:
        ad.status = next_status

    if next_is_paid is not None:
        ad.is_paid = next_is_paid

    if ad.status == "active":
        ad.is_paid = True if next_is_paid is None else ad.is_paid
        if not ad.starts_at:
            ad.starts_at = datetime.utcnow()
        if not ad.ends_at:
            duration_days = ad.plan.duration_days if ad.plan else 30
            ad.ends_at = ad.starts_at + timedelta(days=duration_days)
    elif ad.status == "pending_payment":
        ad.is_paid = False


@admin_bp.get("/dashboard")
@jwt_required()
def dashboard():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    total_revenue = sum((payment.amount or Decimal("0.00")) for payment in Payment.query.all())

    return {
        "stats": {
            "users_total": User.query.count(),
            "rooms_total": Room.query.count(),
            "rooms_available": Room.query.filter_by(is_available=True).count(),
            "reservations_total": Reservation.query.count(),
            "reservations_pending": Reservation.query.filter_by(status="pending").count(),
            "reservations_confirmed": Reservation.query.filter(
                Reservation.status.in_(["confirmed", "paid", "completed"])
            ).count(),
            "ads_total": Ad.query.count(),
            "ads_pending_payment": Ad.query.filter_by(status="pending_payment").count(),
            "ads_active": Ad.query.filter_by(status="active").count(),
            "revenue_total": float(total_revenue),
        }
    }


@admin_bp.get("/users")
@jwt_required()
def list_users():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    users = User.query.order_by(User.created_at.desc()).all()
    return {"items": [user_summary(user) for user in users], "total": len(users)}


@admin_bp.patch("/users/<int:user_id>")
@jwt_required()
def update_user(user_id):
    current_admin, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    user = User.query.get(user_id)
    if not user:
        return error_response("Usuario no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    next_role = str(data.get("role", user.role)).strip().lower()
    next_is_active = parse_bool(data.get("is_active"))

    if next_role not in ALLOWED_USER_ROLES:
        return error_response("Rol de usuario invalido.")

    if user.id == current_admin.id and next_role != "admin":
        return error_response("No puede quitarse el rol admin a si mismo.", 409)

    user.role = next_role
    if next_is_active is not None:
        if user.id == current_admin.id and not next_is_active:
            return error_response("No puede desactivar su propia cuenta admin.", 409)
        user.is_active = next_is_active

    db.session.commit()
    return {"message": "Usuario actualizado correctamente.", "user": user_summary(user)}


@admin_bp.get("/reservations")
@jwt_required()
def list_reservations():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    status = (request.args.get("status") or "").strip().lower()
    query = Reservation.query.order_by(Reservation.created_at.desc())
    if status:
        query = query.filter(Reservation.status == status)

    reservations = query.all()
    return {"items": [reservation_summary(item) for item in reservations], "total": len(reservations)}


@admin_bp.post("/reservations")
@jwt_required()
def create_reservation():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    normalized = validate_reservation_payload(data)
    if normalized["errors"]:
        return error_response("Datos de reserva invalidos.", 400, normalized["errors"])

    user, user_errors = find_or_create_guest_from_admin(data)
    if user_errors:
        return error_response("Datos de huesped invalidos.", 400, user_errors)

    subtotal, taxes, total = recalculate_reservation_totals(
        normalized["room"],
        normalized["check_in"],
        normalized["check_out"],
        normalized["services"],
    )

    reservation = Reservation(
        user_id=user.id,
        room_id=normalized["room"].id,
        reservation_code=build_reservation_code(),
        check_in=normalized["check_in"],
        check_out=normalized["check_out"],
        adults=normalized["adults"],
        children=normalized["children"],
        country=str(data.get("country", "")).strip(),
        document_id=str(data.get("document_id", "")).strip(),
        travel_reason=str(data.get("travel_reason", "")).strip() or None,
        special_requests=str(data.get("special_requests", "")).strip() or None,
        status=str(data.get("status", "pending")).strip().lower() or "pending",
        subtotal=subtotal,
        taxes=taxes,
        total=total,
    )
    db.session.add(reservation)
    db.session.flush()
    sync_reservation_services(reservation, normalized["services"])
    db.session.commit()
    return {"message": "Reserva creada correctamente.", "reservation": reservation_summary(reservation)}, 201


@admin_bp.patch("/reservations/<int:reservation_id>/status")
@jwt_required()
def update_reservation_status(reservation_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return error_response("Reserva no encontrada.", 404)

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().lower()
    if status not in ALLOWED_RESERVATION_STATUSES:
        return error_response("Estado de reserva invalido.")

    reservation.status = status
    db.session.commit()
    return {
        "message": "Estado de la reserva actualizado correctamente.",
        "reservation": reservation_summary(reservation),
    }


@admin_bp.patch("/reservations/<int:reservation_id>")
@jwt_required()
def update_reservation(reservation_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return error_response("Reserva no encontrada.", 404)

    data = request.get_json(silent=True) or {}
    normalized = validate_reservation_payload(data, reservation=reservation)
    if normalized["errors"]:
        return error_response("Datos de reserva invalidos.", 400, normalized["errors"])

    if "status" in data:
        next_status = str(data.get("status", reservation.status)).strip().lower()
        if next_status not in ALLOWED_RESERVATION_STATUSES:
            return error_response("Estado de reserva invalido.")
        reservation.status = next_status

    user, user_errors = find_or_create_guest_from_admin(data, existing_user_id=reservation.user_id)
    if user_errors:
        return error_response("Datos de huesped invalidos.", 400, user_errors)

    subtotal, taxes, total = recalculate_reservation_totals(
        normalized["room"],
        normalized["check_in"],
        normalized["check_out"],
        normalized["services"],
    )

    reservation.user_id = user.id
    reservation.room_id = normalized["room"].id
    reservation.check_in = normalized["check_in"]
    reservation.check_out = normalized["check_out"]
    reservation.adults = normalized["adults"]
    reservation.children = normalized["children"]
    reservation.country = str(data.get("country", reservation.country)).strip() or reservation.country
    reservation.document_id = str(data.get("document_id", reservation.document_id)).strip() or reservation.document_id
    reservation.travel_reason = str(data.get("travel_reason", reservation.travel_reason or "")).strip() or None
    reservation.special_requests = str(data.get("special_requests", reservation.special_requests or "")).strip() or None
    reservation.subtotal = subtotal
    reservation.taxes = taxes
    reservation.total = total
    sync_reservation_services(reservation, normalized["services"])

    db.session.commit()
    return {"message": "Reserva actualizada correctamente.", "reservation": reservation_summary(reservation)}


@admin_bp.delete("/reservations/<int:reservation_id>")
@jwt_required()
def delete_reservation(reservation_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return error_response("Reserva no encontrada.", 404)

    if Payment.query.filter_by(reservation_id=reservation.id).first():
        return error_response(
            "No se puede eliminar una reserva con pagos asociados. Cancelala en su lugar.",
            409,
        )

    db.session.delete(reservation)
    db.session.commit()
    return {"message": "Reserva eliminada correctamente."}


@admin_bp.get("/rooms")
@jwt_required()
def list_rooms():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    rooms = Room.query.order_by(Room.category.asc(), Room.price_per_night.asc()).all()
    return {"items": [room_summary(room) for room in rooms], "total": len(rooms)}


@admin_bp.post("/rooms")
@jwt_required()
def create_room():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    normalized = validate_room_payload(data)
    if normalized["errors"]:
        return error_response("Datos de habitacion invalidos.", 400, normalized["errors"])

    room = Room(
        name=str(data.get("name", "")).strip(),
        slug=normalized["slug"],
        category=str(data.get("category", "")).strip().lower(),
        description=str(data.get("description", "")).strip(),
        price_per_night=normalized["price_per_night"],
        capacity=normalized["capacity"],
        size_m2=normalized["size_m2"],
        bed_type=str(data.get("bed_type", "")).strip(),
        is_available=parse_bool(data.get("is_available")) is not False,
        featured_image=str(data.get("featured_image", "")).strip() or None,
    )
    db.session.add(room)
    db.session.commit()
    return {"message": "Habitacion creada correctamente.", "room": room_summary(room)}, 201


@admin_bp.patch("/rooms/<int:room_id>")
@jwt_required()
def update_room(room_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    room = Room.query.get(room_id)
    if not room:
        return error_response("Habitacion no encontrada.", 404)

    data = request.get_json(silent=True) or {}
    normalized = validate_room_payload(data, room=room)
    if normalized["errors"]:
        return error_response("Datos de habitacion invalidos.", 400, normalized["errors"])

    apply_room_changes(room, data, normalized)

    db.session.commit()
    return {"message": "Habitacion actualizada correctamente.", "room": room_summary(room)}


@admin_bp.delete("/rooms/<int:room_id>")
@jwt_required()
def delete_room(room_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    room = Room.query.get(room_id)
    if not room:
        return error_response("Habitacion no encontrada.", 404)

    if Reservation.query.filter_by(room_id=room.id).first():
        return error_response(
            "No se puede eliminar una habitacion con reservas asociadas. Desactivela en su lugar.",
            409,
        )

    db.session.delete(room)
    db.session.commit()
    return {"message": "Habitacion eliminada correctamente."}


@admin_bp.get("/ads")
@jwt_required()
def list_ads():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    status = (request.args.get("status") or "").strip().lower()
    query = Ad.query.order_by(Ad.created_at.desc())
    if status:
        query = query.filter(Ad.status == status)

    ads = query.all()
    return {"items": [ad_summary(item) for item in ads], "total": len(ads)}


@admin_bp.get("/ad-plans")
@jwt_required()
def list_ad_plans():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    plans = AdPlan.query.order_by(AdPlan.price.asc()).all()
    return {
        "items": [
            {
                "id": plan.id,
                "name": plan.name,
                "price": float(plan.price or 0),
                "duration_days": plan.duration_days,
            }
            for plan in plans
        ],
        "total": len(plans),
    }


@admin_bp.post("/ads")
@jwt_required()
def create_ad():
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    normalized = validate_ad_payload(data)
    if normalized["errors"]:
        return error_response("Datos del anuncio invalidos.", 400, normalized["errors"])

    ad = Ad(
        ad_plan_id=normalized["plan"].id,
        title=str(data.get("title", "")).strip(),
        company_name=str(data.get("company_name", "")).strip(),
        contact_name=str(data.get("contact_name", "")).strip(),
        contact_email=normalized["email"],
        contact_phone=str(data.get("contact_phone", "")).strip(),
        category=str(data.get("category", "")).strip().lower(),
        description=str(data.get("description", "")).strip() or None,
        status=str(data.get("status", "pending_payment")).strip().lower() or "pending_payment",
        is_paid=parse_bool(data.get("is_paid")) is True,
    )
    apply_ad_changes(ad, data, normalized)
    db.session.add(ad)
    db.session.commit()
    return {"message": "Anuncio creado correctamente.", "ad": ad_summary(ad)}, 201


@admin_bp.patch("/ads/<int:ad_id>")
@jwt_required()
def update_ad(ad_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    ad = Ad.query.get(ad_id)
    if not ad:
        return error_response("Anuncio no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    normalized = validate_ad_payload(data, ad=ad)
    if normalized["errors"]:
        return error_response("Datos del anuncio invalidos.", 400, normalized["errors"])

    if "status" in data:
        next_status = str(data.get("status", ad.status)).strip().lower()
        if next_status not in ALLOWED_AD_STATUSES:
            return error_response("Estado de anuncio invalido.")

    apply_ad_changes(ad, data, normalized)

    db.session.commit()
    return {"message": "Anuncio actualizado correctamente.", "ad": ad_summary(ad)}


@admin_bp.delete("/ads/<int:ad_id>")
@jwt_required()
def delete_ad(ad_id):
    _, auth_error = get_current_admin()
    if auth_error:
        return auth_error

    ad = Ad.query.get(ad_id)
    if not ad:
        return error_response("Anuncio no encontrado.", 404)

    if Payment.query.filter_by(ad_id=ad.id).first():
        return error_response(
            "No se puede eliminar un anuncio con pagos asociados. Archivelo en su lugar.",
            409,
        )

    db.session.delete(ad)
    db.session.commit()
    return {"message": "Anuncio eliminado correctamente."}
