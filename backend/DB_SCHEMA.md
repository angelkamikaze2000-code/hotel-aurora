# Esquema de Base de Datos

## Tablas principales

### `users`

- `id`
- `first_name`
- `last_name`
- `email`
- `phone`
- `password_hash`
- `role`
- `is_active`
- `created_at`
- `updated_at`

Uso:
- registro e inicio de sesion
- datos del huesped
- administracion futura

### `rooms`

- `id`
- `name`
- `slug`
- `category`
- `description`
- `price_per_night`
- `capacity`
- `size_m2`
- `bed_type`
- `is_available`
- `featured_image`
- `created_at`
- `updated_at`

Uso:
- catalogo de habitaciones
- filtros
- disponibilidad

### `reservations`

- `id`
- `user_id`
- `room_id`
- `reservation_code`
- `check_in`
- `check_out`
- `adults`
- `children`
- `country`
- `document_id`
- `travel_reason`
- `special_requests`
- `status`
- `subtotal`
- `taxes`
- `total`
- `created_at`
- `updated_at`

Uso:
- guardar reservas
- validar cruces de fechas
- historial del cliente

### `reservation_services`

- `id`
- `reservation_id`
- `name`
- `price`
- `created_at`

Uso:
- desayuno
- spa
- transporte
- extras que afectan el total

### `payments`

- `id`
- `reservation_id`
- `ad_id`
- `payment_code`
- `context_type`
- `method`
- `status`
- `amount`
- `currency`
- `transaction_reference`
- `created_at`

Uso:
- pago de reserva
- pago de anuncio
- simulacion academica

### `ad_plans`

- `id`
- `name`
- `price`
- `duration_days`
- `max_active_ads`
- `is_featured`
- `created_at`
- `updated_at`

Uso:
- planes Basico, Pro y Premium

### `ads`

- `id`
- `ad_plan_id`
- `title`
- `company_name`
- `contact_name`
- `contact_email`
- `contact_phone`
- `category`
- `description`
- `status`
- `starts_at`
- `ends_at`
- `is_paid`
- `created_at`
- `updated_at`

Uso:
- anuncios pagados
- anuncios activos por plan
- relacion con pagos

## Relaciones

- Un `user` puede tener muchas `reservations`.
- Una `room` puede tener muchas `reservations`.
- Una `reservation` puede tener muchos `reservation_services`.
- Una `reservation` puede tener muchos `payments`.
- Un `ad_plan` puede tener muchos `ads`.
- Un `ad` puede tener muchos `payments`.

## Regla clave de negocio

La disponibilidad de una habitacion no se decide solo por `rooms.is_available`. Tambien depende de si existe una reserva en conflicto de fechas con estado activo.
