# 🚀 Guía de Deploy Backend en Render

## Prerequisitos
- ✅ Base de datos PostgreSQL ya desplegada en Render
- ✅ Repositorio backend en GitHub
- ✅ Cuenta en Render.com

---

## Paso 1: Crear un nuevo Web Service en Render

1. Ve a **https://dashboard.render.com/**
2. Haz clic en **+ New** → **Web Service**
3. Selecciona **Deploy an existing repository**
4. Conecta tu cuenta GitHub si no lo has hecho
5. Busca y selecciona: `buses_sig` (o el nombre de tu repo)
6. Selecciona la rama: `main` (o la rama donde está el backend)

---

## Paso 2: Configurar el Web Service

En la pantalla de creación del nuevo servicio:

### Name
```
buses-sig-backend
```

### Environment
```
Python 3
```

### Build Command
```
pip install -r requirements.txt
```

### Start Command
```
gunicorn config.wsgi:application
```

### Region
```
Ohio (o la más cercana a ti)
```

### Plan
```
Free (o el plan que prefieras)
```

---

## Paso 3: Agregar Variables de Entorno

Haz clic en **Environment** (lado izquierdo) y agrega:

| Key | Value | Descripción |
|-----|-------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` | URL de tu BD PostgreSQL |
| `DEBUG` | `False` | Desactivar debug en producción |
| `SECRET_KEY` | `tu-clave-secreta-larga-aleatoria` | Clave Django segura |
| `ALLOWED_HOSTS` | `buses-sig-backend.onrender.com` | Tu dominio de Render |

**Para obtener `DATABASE_URL`:**
- Abre tu BD PostgreSQL en Render
- Copia la conexión externa (External Database URL)
- Debe ser algo como: `postgresql://user:password@host.render.internal:5432/dbname`

---

## Paso 4: Desplegar

1. Haz clic en **Create Web Service**
2. Render comenzará a compilar e instalar dependencias (5-10 minutos)
3. Cuando veas **"Your service is live"**, ¡está listo!
4. Tu URL será: `https://buses-sig-backend.onrender.com`

---

## Paso 5: Verificar el Deploy

1. Abre en el navegador:
   ```
   https://buses-sig-backend.onrender.com/api/lineas/
   ```
2. Debe devolver JSON con las líneas

---

## Paso 6: Actualizar Flutter `.env`

En `bus_mobile/.env`, reemplaza:

```
API_BASE_URL=http://192.168.100.68:8000
```

Con:

```
API_BASE_URL=https://buses-sig-backend.onrender.com
```

---

## Paso 7: Build Final del APK

En tu carpeta `bus_mobile/`:

```bash
flutter pub get
flutter build apk --release
```

El APK estará en:
```
bus_mobile/build/app/outputs/flutter-apk/app-release.apk
```

---

## Troubleshooting

**Error: "server closed the connection unexpectedly"**
- Verifica que `DATABASE_URL` sea correcto
- Asegúrate que la BD tiene memoria suficiente

**Error: "ModuleNotFoundError"**
- Verifica que `requirements.txt` esté actualizado
- Build command debe ser: `pip install -r requirements.txt`

**Logs en vivo:**
- En Render, abre **Logs** (lado derecho) para ver errores en tiempo real

---

## URLs Importantes

- 🌐 Backend: `https://buses-sig-backend.onrender.com`
- 📊 API: `https://buses-sig-backend.onrender.com/api/`
- 🗄️ BD PostgreSQL: (en tu dashboard de Render)

