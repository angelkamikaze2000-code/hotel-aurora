# Hotel Aurora

Proyecto con frontend estatico y backend Flask para autenticacion, habitaciones, reservas, anuncios y pagos simulados.

## Estructura

- `frontend-hotel-main/`: vistas HTML del hotel
- `backend/`: API Flask y base de datos local SQLite
- `start_frontend.ps1`: servidor local simple para el frontend

## Requisitos

- Python 3.12 instalado en `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`

## Levantar el proyecto

### 1. Backend

Desde [backend/start_backend.ps1](C:\Users\Loyal Gaming\Desktop\hotel proyecto\backend\start_backend.ps1):

```powershell
cd "C:\Users\Loyal Gaming\Desktop\hotel proyecto\backend"
.\start_backend.ps1
```

Backend disponible en [http://127.0.0.1:5000](http://127.0.0.1:5000).

### 2. Frontend

Desde [start_frontend.ps1](C:\Users\Loyal Gaming\Desktop\hotel proyecto\start_frontend.ps1):

```powershell
cd "C:\Users\Loyal Gaming\Desktop\hotel proyecto"
.\start_frontend.ps1
```

Frontend disponible en [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html).

## Flujo recomendado de prueba

1. Abrir `habitaciones.html` y seleccionar una habitacion.
2. Completar la reserva en `reservas.html`.
3. Continuar al pago desde `pago.html?context=reserva`.
4. Probar registro e inicio de sesion en `auth.html`.
5. Crear un anuncio en `anuncios.html` y completar su pago.

## Panel de administracion

Se agrego un panel interno en `frontend-hotel-main/admin.html` conectado a la API bajo `/api/admin`.

Actualmente el panel permite:

- ver metricas internas
- gestionar usuarios
- crear, editar y eliminar reservas
- crear, editar y eliminar habitaciones
- crear, editar y eliminar anuncios

Para crear o promover un administrador:

```powershell
cd "C:\Users\Loyal Gaming\Desktop\hotel proyecto\backend"
python create_admin.py --email admin@aurora.com --password Admin123! --first-name Admin --last-name Aurora
```

Luego inicie sesion con esa cuenta en `auth.html` y abra `admin.html`.

## Validacion automatica

El smoke test vive en [backend/smoke_test_flow.ps1](C:\Users\Loyal Gaming\Desktop\hotel proyecto\backend\smoke_test_flow.ps1).

```powershell
cd "C:\Users\Loyal Gaming\Desktop\hotel proyecto\backend"
.\smoke_test_flow.ps1
```

El script:

- asegura habitaciones base con `seed_rooms.py`
- levanta el backend temporalmente
- valida registro, login y `me`
- valida habitaciones y disponibilidad
- crea una reserva y simula su pago
- crea un anuncio y simula su pago

## Estado actual

- Backend integrado con SQLite local
- Frontend conectado a la API
- Flujo principal validado end-to-end
- Pagos simulados para demo academica
