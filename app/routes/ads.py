from decimal import Decimal

from flask import Blueprint, request

from ..extensions import db
from ..models import Ad, AdPlan


ads_bp = Blueprint("ads", __name__)


DEFAULT_PLANS = (
    {"name": "Basico", "price": Decimal("99.00"), "duration_days": 30, "max_active_ads": 1, "is_featured": False},
    {"name": "Pro", "price": Decimal("249.00"), "duration_days": 30, "max_active_ads": 3, "is_featured": True},
    {"name": "Premium", "price": Decimal("499.00"), "duration_days": 30, "max_active_ads": 999, "is_featured": True},
)


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return payload, status_code


def ensure_default_plans():
    if AdPlan.query.count() > 0:
        return
    for plan_data in DEFAULT_PLANS:
        db.session.add(AdPlan(**plan_data))
    db.session.commit()


@ads_bp.get("")
def list_ads():
    ensure_default_plans()
    status = (request.args.get("status") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    paid_only = request.args.get("paid_only", "").strip().lower() in {"1", "true", "yes"}
    include_plans = request.args.get("include_plans", "").strip().lower() in {"1", "true", "yes"}

    query = Ad.query.order_by(Ad.created_at.desc())
    if status:
        query = query.filter(Ad.status == status)
    if category:
        query = query.filter(Ad.category == category)
    if paid_only:
        query = query.filter(Ad.is_paid.is_(True))

    response = {
        "items": [ad.to_dict() for ad in query.all()],
        "total": query.count(),
    }
    if include_plans:
        response["plans"] = [plan.to_dict() for plan in AdPlan.query.order_by(AdPlan.price.asc()).all()]
    return response


@ads_bp.get("/plans")
def list_ad_plans():
    ensure_default_plans()
    plans = [plan.to_dict() for plan in AdPlan.query.order_by(AdPlan.price.asc()).all()]
    return {"items": plans, "total": len(plans)}


@ads_bp.post("")
def create_ad():
    ensure_default_plans()
    data = request.get_json(silent=True) or {}
    errors = {}

    required_fields = {
        "company_name": "La empresa es obligatoria.",
        "contact_name": "El nombre de contacto es obligatorio.",
        "contact_email": "El correo es obligatorio.",
        "contact_phone": "El telefono es obligatorio.",
        "title": "El titulo es obligatorio.",
        "category": "La categoria es obligatoria.",
    }
    for field, message in required_fields.items():
        if not str(data.get(field, "")).strip():
            errors[field] = message

    email = str(data.get("contact_email", "")).strip().lower()
    if email and "@" not in email:
        errors["contact_email"] = "Ingrese un correo valido."

    plan = None
    if data.get("ad_plan_id"):
        plan = AdPlan.query.get(data.get("ad_plan_id"))
    elif data.get("plan_name"):
        plan = AdPlan.query.filter(AdPlan.name.ilike(str(data.get("plan_name")).strip())).first()
    else:
        plan = AdPlan.query.filter_by(name="Basico").first()

    if not plan:
        errors["ad_plan_id"] = "Plan publicitario no encontrado."

    if errors:
        return error_response("Datos del anuncio invalidos.", 400, errors)

    ad = Ad(
        ad_plan_id=plan.id,
        title=str(data.get("title", "")).strip(),
        company_name=str(data.get("company_name", "")).strip(),
        contact_name=str(data.get("contact_name", "")).strip(),
        contact_email=email,
        contact_phone=str(data.get("contact_phone", "")).strip(),
        category=str(data.get("category", "")).strip().lower(),
        description=str(data.get("description", "")).strip() or None,
        status="pending_payment",
        starts_at=None,
        ends_at=None,
        is_paid=False,
    )
    db.session.add(ad)
    db.session.commit()

    return {
        "message": "Solicitud de anuncio creada correctamente.",
        "ad": ad.to_dict(),
    }, 201
