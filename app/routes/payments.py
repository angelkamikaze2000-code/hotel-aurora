import base64
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

from flask import Blueprint, current_app, request

from ..extensions import db
from ..models import Ad, Payment, Reservation


payments_bp = Blueprint("payments", __name__)


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


def build_payment_code():
    return f"PAY-{uuid4().hex[:8].upper()}"


def get_context_resource(context_type, data):
    if context_type == "reservation":
        reservation = Reservation.query.get(data.get("reservation_id"))
        if not reservation:
            return None, error_response("Reserva no encontrada.", 404)

        amount = money(data.get("amount", reservation.total))
        if amount is None or amount <= 0:
            return None, error_response("El monto del pago es invalido.")

        return {
            "context_type": "reservation",
            "resource": reservation,
            "amount": amount,
            "currency": str(data.get("currency", "USD")).strip() or "USD",
            "description": f"Reserva {reservation.reservation_code}",
        }, None

    if context_type == "ad":
        ad = Ad.query.get(data.get("ad_id"))
        if not ad:
            return None, error_response("Anuncio no encontrado.", 404)

        amount = money(data.get("amount", ad.plan.price if ad.plan else 0))
        if amount is None or amount <= 0:
            return None, error_response("El monto del pago es invalido.")

        return {
            "context_type": "ad",
            "resource": ad,
            "amount": amount,
            "currency": str(data.get("currency", "USD")).strip() or "USD",
            "description": f"Anuncio {ad.title}",
        }, None

    return None, error_response("context_type debe ser 'reservation' o 'ad'.")


def paypal_enabled():
    return bool(
        current_app.config.get("PAYPAL_CLIENT_ID")
        and current_app.config.get("PAYPAL_CLIENT_SECRET")
    )


def paypal_base_url():
    env = current_app.config.get("PAYPAL_ENV", "sandbox")
    if env == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def paypal_request(method, path, payload=None, access_token=None):
    url = f"{paypal_base_url()}{path}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = None

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        client_id = current_app.config.get("PAYPAL_CLIENT_ID", "")
        client_secret = current_app.config.get("PAYPAL_CLIENT_SECRET", "")
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request_obj = urllib_request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib_request.urlopen(request_obj, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"message": raw or "Error de PayPal."}
        raise RuntimeError(parsed.get("message") or parsed.get("error_description") or "Error de PayPal.") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError("No fue posible conectar con PayPal.") from exc


def get_paypal_access_token():
    url = f"{paypal_base_url()}/v1/oauth2/token"
    client_id = current_app.config.get("PAYPAL_CLIENT_ID", "")
    client_secret = current_app.config.get("PAYPAL_CLIENT_SECRET", "")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    request_obj = urllib_request.Request(
        url,
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(request_obj, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"message": raw or "Error de autenticacion con PayPal."}
        raise RuntimeError(parsed.get("error_description") or parsed.get("message") or "Error de autenticacion con PayPal.") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError("No fue posible conectar con PayPal.") from exc

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("PayPal no devolvio un access token valido.")
    return token


def apply_successful_payment(context, method, transaction_reference):
    if context["context_type"] == "reservation":
        reservation = context["resource"]
        payment = Payment(
            reservation_id=reservation.id,
            payment_code=build_payment_code(),
            context_type="reservation",
            method=method,
            status="paid",
            amount=context["amount"],
            currency=context["currency"],
            transaction_reference=transaction_reference,
        )
        reservation.status = "confirmed"
        db.session.add(payment)
        db.session.commit()
        return {
            "message": "Pago de reserva procesado correctamente.",
            "payment": payment.to_dict(),
            "reservation": reservation.to_dict(),
        }, 201

    ad = context["resource"]
    payment = Payment(
        ad_id=ad.id,
        payment_code=build_payment_code(),
        context_type="ad",
        method=method,
        status="paid",
        amount=context["amount"],
        currency=context["currency"],
        transaction_reference=transaction_reference,
    )
    now = datetime.utcnow()
    ad.is_paid = True
    ad.status = "active"
    ad.starts_at = now
    ad.ends_at = now + timedelta(days=ad.plan.duration_days if ad.plan else 30)
    db.session.add(payment)
    db.session.commit()
    return {
        "message": "Pago de anuncio procesado correctamente.",
        "payment": payment.to_dict(),
        "ad": ad.to_dict(),
    }, 201


@payments_bp.get("/paypal-config")
def paypal_config():
    if not paypal_enabled():
        return error_response("PayPal no esta configurado en el servidor.", 503)

    return {
        "client_id": current_app.config["PAYPAL_CLIENT_ID"],
        "currency": "USD",
        "intent": "capture",
        "environment": current_app.config.get("PAYPAL_ENV", "sandbox"),
    }


@payments_bp.post("/paypal/create-order")
def paypal_create_order():
    if not paypal_enabled():
        return error_response("PayPal no esta configurado en el servidor.", 503)

    data = request.get_json(silent=True) or {}
    context_type = str(data.get("context_type", "")).strip().lower()
    context, context_error = get_context_resource(context_type, data)
    if context_error:
        return context_error

    try:
        access_token = get_paypal_access_token()
        order = paypal_request(
            "POST",
            "/v2/checkout/orders",
            payload={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": f"{context_type}-{context['resource'].id}",
                        "description": context["description"],
                        "amount": {
                            "currency_code": context["currency"],
                            "value": f"{context['amount']:.2f}",
                        },
                    }
                ],
            },
            access_token=access_token,
        )
    except RuntimeError as exc:
        return error_response(str(exc), 502)

    return {
        "order_id": order.get("id"),
        "status": order.get("status"),
    }, 201


@payments_bp.post("/paypal/capture-order")
def paypal_capture_order():
    if not paypal_enabled():
        return error_response("PayPal no esta configurado en el servidor.", 503)

    data = request.get_json(silent=True) or {}
    context_type = str(data.get("context_type", "")).strip().lower()
    order_id = str(data.get("order_id", "")).strip()
    context, context_error = get_context_resource(context_type, data)
    if context_error:
        return context_error
    if not order_id:
        return error_response("order_id es obligatorio.")

    try:
        access_token = get_paypal_access_token()
        capture = paypal_request(
            "POST",
            f"/v2/checkout/orders/{order_id}/capture",
            payload={},
            access_token=access_token,
        )
    except RuntimeError as exc:
        return error_response(str(exc), 502)

    status = str(capture.get("status", "")).upper()
    if status != "COMPLETED":
        return error_response("PayPal no completo la captura del pago.", 409, {"status": status})

    capture_id = ""
    payer_name = ""
    payer_email = ""
    purchase_units = capture.get("purchase_units") or []
    if purchase_units:
        payments = purchase_units[0].get("payments") or {}
        captures = payments.get("captures") or []
        if captures:
            capture_id = captures[0].get("id") or ""
    payer = capture.get("payer") or {}
    payer_name = " ".join(
        part for part in [
            (payer.get("name") or {}).get("given_name", ""),
            (payer.get("name") or {}).get("surname", ""),
        ]
        if part
    ).strip()
    payer_email = payer.get("email_address") or ""

    response, status_code = apply_successful_payment(
        context,
        method="paypal",
        transaction_reference=capture_id or order_id,
    )
    response["paypal_order_id"] = order_id
    response["paypal_status"] = status
    response["payer_name"] = payer_name
    response["payer_email"] = payer_email
    return response, status_code


@payments_bp.post("/simulate")
def simulate_payment():
    data = request.get_json(silent=True) or {}
    context_type = str(data.get("context_type", "")).strip().lower()
    method = str(data.get("method", "")).strip().lower() or "card"
    transaction_reference = str(data.get("transaction_reference", "")).strip() or uuid4().hex[:12].upper()
    context, context_error = get_context_resource(context_type, data)
    if context_error:
        return context_error

    response, status_code = apply_successful_payment(
        context,
        method=method,
        transaction_reference=transaction_reference,
    )
    response["message"] = (
        "Pago de reserva simulado correctamente."
        if context_type == "reservation"
        else "Pago de anuncio simulado correctamente."
    )
    return response, status_code
