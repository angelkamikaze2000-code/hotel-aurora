from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Room


ROOMS = [
    {
        "name": "Habitacion Classic",
        "slug": "habitacion-classic",
        "category": "estandar",
        "description": "Confort esencial en 28 m2 con cama queen, escritorio de trabajo y vista al jardin interior.",
        "price_per_night": Decimal("95.00"),
        "capacity": 2,
        "size_m2": 28,
        "bed_type": "Queen",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=900&q=80&fit=crop",
    },
    {
        "name": "Habitacion Doble",
        "slug": "habitacion-doble",
        "category": "estandar",
        "description": "Espacio perfecto para dos personas con dos camas individuales o cama doble y bano completo.",
        "price_per_night": Decimal("110.00"),
        "capacity": 2,
        "size_m2": 32,
        "bed_type": "Doble",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1505693314120-0d443867891c?w=900&q=80&fit=crop",
    },
    {
        "name": "Suite Junior Deluxe",
        "slug": "suite-junior-deluxe",
        "category": "deluxe",
        "description": "Elegancia y amplitud en 45 m2 con cama king, sala compacta y bano de marmol.",
        "price_per_night": Decimal("175.00"),
        "capacity": 2,
        "size_m2": 45,
        "bed_type": "King",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=900&q=80&fit=crop",
    },
    {
        "name": "Deluxe Vista Mar",
        "slug": "deluxe-vista-mar",
        "category": "deluxe",
        "description": "Habitacion premium de 55 m2 con terraza privada y vistas destacadas.",
        "price_per_night": Decimal("220.00"),
        "capacity": 2,
        "size_m2": 55,
        "bed_type": "King",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=900&q=80&fit=crop",
    },
    {
        "name": "Suite Aurora",
        "slug": "suite-aurora",
        "category": "suite",
        "description": "Nuestra suite insignia con dormitorio principal, sala independiente y jacuzzi privado.",
        "price_per_night": Decimal("310.00"),
        "capacity": 3,
        "size_m2": 75,
        "bed_type": "King + Sofa cama",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=900&q=80&fit=crop",
    },
    {
        "name": "Suite Familiar",
        "slug": "suite-familiar",
        "category": "suite",
        "description": "Opcion ideal para familias con dos dormitorios, sala de estar y dos banos completos.",
        "price_per_night": Decimal("360.00"),
        "capacity": 4,
        "size_m2": 80,
        "bed_type": "2 King",
        "is_available": False,
        "featured_image": "https://images.unsplash.com/photo-1631049552057-403cdb8f0658?w=900&q=80&fit=crop",
    },
    {
        "name": "Suite Presidencial",
        "slug": "suite-presidencial",
        "category": "presidencial",
        "description": "La cuspide del lujo con comedor privado, vestidor y terraza panoramica.",
        "price_per_night": Decimal("480.00"),
        "capacity": 2,
        "size_m2": 120,
        "bed_type": "King Presidencial",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=900&q=80&fit=crop",
    },
    {
        "name": "Penthouse Aurora",
        "slug": "penthouse-aurora",
        "category": "presidencial",
        "description": "Experiencia premium de 180 m2 con terraza 360, piscina privada y privacidad total.",
        "price_per_night": Decimal("850.00"),
        "capacity": 4,
        "size_m2": 180,
        "bed_type": "2 King + Living",
        "is_available": True,
        "featured_image": "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=900&q=80&fit=crop",
    },
]


def seed_rooms():
    app = create_app()
    with app.app_context():
        db.create_all()

        created = 0
        updated = 0
        for room_data in ROOMS:
            room = Room.query.filter_by(slug=room_data["slug"]).first()
            if room:
                for key, value in room_data.items():
                    setattr(room, key, value)
                updated += 1
            else:
                db.session.add(Room(**room_data))
                created += 1

        db.session.commit()
        print(f"Seed completado. Creadas: {created}. Actualizadas: {updated}.")


if __name__ == "__main__":
    seed_rooms()
