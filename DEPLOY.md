# Publicar Hotel Aurora

## 1. Backend en Render

1. Sube este proyecto a GitHub.
2. En Render, crea un nuevo Blueprint desde el repositorio.
3. Render detectara `render.yaml`.
4. El servicio se llamara `hotel-aurora-backend`.
5. Render tambien creara la base PostgreSQL `hotel-aurora-db`.
6. Cuando termine, copia la URL publica del backend, por ejemplo:

```text
https://hotel-aurora-backend.onrender.com
```

La API debe responder en:

```text
https://hotel-aurora-backend.onrender.com/api/health
```

## 2. Conectar el frontend al backend publico

Edita `frontend-hotel-main/config.js` y cambia:

```js
window.HOTEL_API_BASE_URL = window.HOTEL_API_BASE_URL || 'http://127.0.0.1:5000/api';
```

por:

```js
window.HOTEL_API_BASE_URL = 'https://hotel-aurora-backend.onrender.com/api';
```

Usa la URL real que te entregue Render.

## 3. Frontend en Netlify

1. En Netlify, crea un nuevo sitio desde el mismo repositorio.
2. Netlify detectara `netlify.toml`.
3. El directorio publicado sera `frontend-hotel-main`.
4. Cuando termine, abre el link publico del sitio.

## 4. Prueba final

Desde el link publico de Netlify:

1. Abre `auth.html` y registra un usuario.
2. Abre `reservas.html` y crea una reserva.
3. Continua a `pago.html` y simula el pago.
4. Entra con un admin y revisa `admin.html`.

