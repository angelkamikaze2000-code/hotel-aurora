# Backend Hotel Aurora

## Stack elegido

El backend esta preparado para desarrollarse con:

- Python 3.12+
- Flask
- PostgreSQL o SQLite para desarrollo local
- SQLAlchemy
- Flask-Migrate
- JWT para autenticacion

## Por que este stack

- Flask es ligero y rapido para un proyecto academico.
- PostgreSQL modela bien relaciones como usuarios, habitaciones, reservas y pagos.
- SQLAlchemy permite crecer sin atar toda la logica a SQL manual.
- JWT encaja bien con el frontend actual, que luego consumira endpoints REST.

## Entidades principales que exige el frontend actual

- `users`
- `rooms`
- `reservations`
- `reservation_services`
- `payments`
- `ads`
- `ad_plans`

## Estructura propuesta

```text
backend/
  app/
    __init__.py
    config.py
    extensions.py
    routes/
      auth.py
      rooms.py
      reservations.py
      ads.py
      payments.py
  requirements.txt
  .env.example
```

## Orden recomendado de trabajo

1. Configuracion del proyecto y conexion a base de datos.
2. Modelado de tablas.
3. Registro e inicio de sesion.
4. Habitaciones y disponibilidad.
5. Reservas.
6. Anuncios pagados.
7. Pago simulado.

## Endpoints que probablemente necesitaremos

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `GET /api/rooms`
- `GET /api/rooms/:id`
- `GET /api/rooms/availability`
- `POST /api/reservations`
- `GET /api/reservations/:id`
- `POST /api/ads`
- `GET /api/ads`
- `POST /api/payments/simulate`

## Ejecucion local rapida

Si no defines `DATABASE_URL`, el backend usa automaticamente SQLite local en `backend/instance/hotel_aurora.db`.

Si no defines `SECRET_KEY` o `JWT_SECRET_KEY`, o dejas valores inseguros de ejemplo, el backend genera claves fuertes y persistentes en `backend/instance/runtime_secrets.json`.

Si prefieres controlarlas manualmente, copia `.env.example` a `.env` y reemplaza ambas claves por valores largos y aleatorios.

Para levantarlo rapidamente:

```powershell
.\start_backend.ps1
```

## Smoke test del flujo principal

Para validar el flujo completo de integracion:

- registro
- inicio de sesion
- consulta de habitaciones
- disponibilidad
- reserva
- pago simulado de reserva
- creacion de anuncio
- pago simulado de anuncio

ejecuta:

```powershell
.\smoke_test_flow.ps1
```

Si prefieres PostgreSQL, define `DATABASE_URL` en `.env` o en variables de entorno y el backend usara esa conexion.

## Panel admin

El backend ahora expone endpoints internos protegidos en `/api/admin` para:

- resumen del dashboard
- listado y gestion de usuarios
- CRUD de reservas
- CRUD de habitaciones
- CRUD de anuncios
- listado de planes publicitarios

Para crear o promover un admin local:

```powershell
python create_admin.py --email admin@aurora.com --password Admin123! --first-name Admin --last-name Aurora
```

## Recuperacion de contrasena

El backend expone un flujo de recuperacion academico:

- `POST /api/auth/forgot-password` genera un token temporal firmado
- `POST /api/auth/reset-password` valida el token y actualiza la contrasena

El vencimiento del token se controla con `PASSWORD_RESET_TOKEN_MAX_AGE` y por defecto es de 1800 segundos.

## Semilla de habitaciones

Con SQLite local o con la base que prefieras, puedes cargar habitaciones base con:

```bash
python seed_rooms.py
```

El script crea las tablas si no existen y luego inserta o actualiza habitaciones usando el `slug` como clave estable.
