from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import User


auth_bp = Blueprint("auth", __name__)


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return payload, status_code


def normalize_email(value):
    return (value or "").strip().lower()


def build_reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def build_password_reset_token(user):
    serializer = build_reset_serializer()
    return serializer.dumps({"user_id": user.id, "email": user.email})


def parse_password_reset_token(token):
    serializer = build_reset_serializer()
    max_age_seconds = int(current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 1800))
    data = serializer.loads(token, max_age=max_age_seconds)
    return data


def validate_register_payload(data):
    required_fields = {
        "first_name": "El nombre es obligatorio.",
        "last_name": "El apellido es obligatorio.",
        "email": "El correo es obligatorio.",
        "password": "La contrasena es obligatoria.",
    }
    errors = {}

    for field, message in required_fields.items():
        if not str(data.get(field, "")).strip():
            errors[field] = message

    email = normalize_email(data.get("email"))
    if email and "@" not in email:
        errors["email"] = "Ingrese un correo valido."

    password = str(data.get("password", ""))
    if password and len(password) < 8:
        errors["password"] = "La contrasena debe tener al menos 8 caracteres."

    return errors


def validate_password_reset_request_payload(data):
    email = normalize_email(data.get("email"))
    if not email:
        return {"email": "El correo es obligatorio."}
    if "@" not in email:
        return {"email": "Ingrese un correo valido."}
    return {}


def validate_password_reset_payload(data):
    errors = {}
    token = str(data.get("token", "")).strip()
    password = str(data.get("password", ""))
    password_confirmation = str(data.get("password_confirmation", ""))

    if not token:
        errors["token"] = "El token de recuperacion es obligatorio."
    if not password:
        errors["password"] = "La nueva contrasena es obligatoria."
    elif len(password) < 8:
        errors["password"] = "La nueva contrasena debe tener al menos 8 caracteres."

    if password_confirmation != password:
        errors["password_confirmation"] = "Las contrasenas no coinciden."

    return errors


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_register_payload(data)
    if errors:
        return error_response("Datos de registro invalidos.", 400, errors)

    email = normalize_email(data.get("email"))
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return error_response("Ya existe un usuario con ese correo.", 409)

    user = User(
        first_name=str(data.get("first_name", "")).strip(),
        last_name=str(data.get("last_name", "")).strip(),
        email=email,
        phone=str(data.get("phone", "")).strip() or None,
    )
    user.set_password(str(data.get("password")))

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"email": user.email, "role": user.role},
    )

    return {
        "message": "Usuario registrado correctamente.",
        "access_token": access_token,
        "user": user.to_dict(),
    }, 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    password = str(data.get("password", ""))

    if not email or not password:
        return error_response("Correo y contrasena son obligatorios.")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return error_response("Credenciales invalidas.", 401)

    if not user.is_active:
        return error_response("La cuenta se encuentra desactivada.", 403)

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"email": user.email, "role": user.role},
    )

    return {
        "message": "Inicio de sesion exitoso.",
        "access_token": access_token,
        "user": user.to_dict(),
    }


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    errors = validate_password_reset_request_payload(data)
    if errors:
        return error_response("Datos invalidos.", 400, errors)

    email = normalize_email(data.get("email"))
    user = User.query.filter_by(email=email).first()
    message = (
        "Si existe una cuenta asociada a ese correo, puede continuar con el cambio "
        "de contrasena usando el token generado."
    )

    if not user or not user.is_active:
        return {"message": message}, 200

    reset_token = build_password_reset_token(user)
    return {
        "message": message,
        "reset_token": reset_token,
        "expires_in_minutes": int(current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 1800) / 60),
    }, 200


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    errors = validate_password_reset_payload(data)
    if errors:
        return error_response("Datos invalidos.", 400, errors)

    token = str(data.get("token", "")).strip()
    try:
        token_data = parse_password_reset_token(token)
    except SignatureExpired:
        return error_response("El token de recuperacion ha expirado.", 400)
    except BadSignature:
        return error_response("El token de recuperacion no es valido.", 400)

    user = User.query.get(token_data.get("user_id"))
    if not user or user.email != token_data.get("email"):
        return error_response("No se encontro un usuario valido para este token.", 404)

    if not user.is_active:
        return error_response("La cuenta se encuentra desactivada.", 403)

    user.set_password(str(data.get("password", "")))
    db.session.commit()

    return {"message": "Contrasena actualizada correctamente."}, 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return error_response("Usuario no encontrado.", 404)

    return {"user": user.to_dict()}
