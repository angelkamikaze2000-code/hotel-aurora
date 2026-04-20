import argparse

from app import create_app
from app.extensions import db
from app.models import User


def parse_args():
    parser = argparse.ArgumentParser(description="Crea o promueve un usuario admin en Hotel Aurora.")
    parser.add_argument("--email", required=True, help="Correo del administrador")
    parser.add_argument("--password", required=True, help="Contrasena del administrador")
    parser.add_argument("--first-name", default="Admin", help="Nombre del administrador")
    parser.add_argument("--last-name", default="Hotel", help="Apellido del administrador")
    parser.add_argument("--phone", default="", help="Telefono opcional")
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()

    with app.app_context():
        db.create_all()

        email = args.email.strip().lower()
        user = User.query.filter_by(email=email).first()
        created = False

        if not user:
            user = User(
                first_name=args.first_name.strip() or "Admin",
                last_name=args.last_name.strip() or "Hotel",
                email=email,
                phone=args.phone.strip() or None,
                role="admin",
                is_active=True,
            )
            db.session.add(user)
            created = True
        else:
            user.first_name = args.first_name.strip() or user.first_name
            user.last_name = args.last_name.strip() or user.last_name
            user.phone = args.phone.strip() or user.phone

        user.role = "admin"
        user.is_active = True
        user.set_password(args.password)

        db.session.commit()

        if created:
            print(f"Administrador creado correctamente: {user.email}")
        else:
            print(f"Usuario actualizado como administrador: {user.email}")


if __name__ == "__main__":
    main()
