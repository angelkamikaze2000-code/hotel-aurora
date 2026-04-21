from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="guest")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    reservations = db.relationship("Reservation", back_populates="user", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Room(TimestampMixin, db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    price_per_night = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    capacity = db.Column(db.Integer, nullable=False)
    size_m2 = db.Column(db.Integer, nullable=False)
    bed_type = db.Column(db.String(80), nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    featured_image = db.Column(db.String(500))

    reservations = db.relationship("Reservation", back_populates="room", lazy=True)

    def to_dict(self, is_available=None):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "category": self.category,
            "description": self.description,
            "price_per_night": float(self.price_per_night or 0),
            "capacity": self.capacity,
            "size_m2": self.size_m2,
            "bed_type": self.bed_type,
            "is_available": self.is_available if is_available is None else is_available,
            "featured_image": self.featured_image,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Reservation(TimestampMixin, db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False, index=True)
    reservation_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    check_in = db.Column(db.Date, nullable=False, index=True)
    check_out = db.Column(db.Date, nullable=False, index=True)
    adults = db.Column(db.Integer, nullable=False, default=1)
    children = db.Column(db.Integer, nullable=False, default=0)
    country = db.Column(db.String(80), nullable=False)
    document_id = db.Column(db.String(80), nullable=False)
    travel_reason = db.Column(db.String(40))
    special_requests = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending")
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    taxes = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    user = db.relationship("User", back_populates="reservations")
    room = db.relationship("Room", back_populates="reservations")
    services = db.relationship(
        "ReservationService",
        back_populates="reservation",
        cascade="all, delete-orphan",
        lazy=True,
    )
    payments = db.relationship("Payment", back_populates="reservation", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "room_id": self.room_id,
            "reservation_code": self.reservation_code,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "adults": self.adults,
            "children": self.children,
            "country": self.country,
            "document_id": self.document_id,
            "travel_reason": self.travel_reason,
            "special_requests": self.special_requests,
            "status": self.status,
            "subtotal": float(self.subtotal or 0),
            "taxes": float(self.taxes or 0),
            "total": float(self.total or 0),
            "user": self.user.to_dict() if self.user else None,
            "room": self.room.to_dict() if self.room else None,
            "services": [service.to_dict() for service in self.services],
            "payments": [payment.to_dict() for payment in self.payments],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReservationService(db.Model):
    __tablename__ = "reservation_services"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer,
        db.ForeignKey("reservations.id"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reservation = db.relationship("Reservation", back_populates="services")

    def to_dict(self):
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "name": self.name,
            "price": float(self.price or 0),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AdPlan(TimestampMixin, db.Model):
    __tablename__ = "ad_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    max_active_ads = db.Column(db.Integer, nullable=False, default=1)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)

    ads = db.relationship("Ad", back_populates="plan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": float(self.price or 0),
            "duration_days": self.duration_days,
            "max_active_ads": self.max_active_ads,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Ad(TimestampMixin, db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    ad_plan_id = db.Column(db.Integer, db.ForeignKey("ad_plans.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    company_name = db.Column(db.String(160), nullable=False)
    contact_name = db.Column(db.String(120), nullable=False)
    contact_email = db.Column(db.String(255), nullable=False)
    contact_phone = db.Column(db.String(30), nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending")
    starts_at = db.Column(db.DateTime)
    ends_at = db.Column(db.DateTime)
    is_paid = db.Column(db.Boolean, nullable=False, default=False)

    plan = db.relationship("AdPlan", back_populates="ads")
    payments = db.relationship("Payment", back_populates="ad", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "ad_plan_id": self.ad_plan_id,
            "title": self.title,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "is_paid": self.is_paid,
            "plan": self.plan.to_dict() if self.plan else None,
            "payments": [payment.to_dict() for payment in self.payments],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"), index=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), index=True)
    payment_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    context_type = db.Column(db.String(20), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency = db.Column(db.String(10), nullable=False, default="USD")
    transaction_reference = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reservation = db.relationship("Reservation", back_populates="payments")
    ad = db.relationship("Ad", back_populates="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "ad_id": self.ad_id,
            "payment_code": self.payment_code,
            "context_type": self.context_type,
            "method": self.method,
            "status": self.status,
            "amount": float(self.amount or 0),
            "currency": self.currency,
            "transaction_reference": self.transaction_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
