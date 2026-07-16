# Pruebas End-to-End — MicroBus SCZ (UAGRM 2026)

## 0. Configuraciones previas (solo una vez)

### 0.1 No necesitas ninguna API key externa
OpenStreetMap (CartoDB Light) funciona sin registro ni tarjeta de crédito.
Las únicas dependencias externas son Python/Django y Flutter SDK.

### 0.2 Conoce tu IP local (para el .env)
```powershell
# En Windows PowerShell:
ipconfig
# Busca "Dirección IPv4" en tu adaptador activo (ej. 192.168.1.104)
```
Escribe ese valor en `bus_mobile/.env`:
```
BACKEND_URL=http://<TU_IP_LOCAL>:8000
```
El emulador Android NO puede usar `localhost` — siempre usa la IP real de tu PC.

---

## 1. Preparar el backend (Django)

```powershell
cd bus_backend
venv\Scripts\activate

# 1a. Crear las tablas (incluye PuntoTrasbordo)
python manage.py makemigrations
python manage.py migrate

# 1b. Sembrar datos reales desde DatosLineas.xls
python manage.py shell < scripts/seed_from_excel.py

# 1c. Sembrar datos de prueba (conductores + microbuses + recorridos activos)
python manage.py shell < scripts/seed_test_data.py

# 1d. Crear superusuario para Django Admin (una vez)
python manage.py createsuperuser

# 1e. Iniciar servidor (accesible desde el emulador/celular)
python manage.py runserver 0.0.0.0:8000
```

### Verificar que el backend funciona
Abre un navegador en tu PC y accede a:
- `http://localhost:8000/api/lineas/` → debe retornar JSON con 10 líneas
- `http://localhost:8000/api/paradas/` → debe retornar JSON con ~106 paradas (Stop='S')
- `http://localhost:8000/admin/` → panel de administración

---

## 2. Preparar Flutter

```powershell
cd bus_mobile
flutter pub get
flutter run
```
Si usas emulador Android: asegúrate de que esté corriendo antes de `flutter run`.
Si usas celular físico: conecta por USB, activa "Depuración USB".

---

## 3. Pruebas desde la app Flutter

### PANTALLA 1 — Selector de Rol (pantalla de inicio)

**Verificar:**
- Fondo degradado en tonos **rosa/marrón** (Catawba → Deep Puce)
- Icono de bus en blanco sobre cuadro blanco
- Dos tarjetas: "Soy Conductor" y "Soy Pasajero"

**Acción:** Toca **"Soy Pasajero"** → deberías ver el menú de usuario.

---

### PANTALLA 2 — Menú del Pasajero (UsuarioHomeScreen)

**Verificar:**
- Header degradado rosa/marrón con "MicroBus SCZ / Santa Cruz de la Sierra"
- **4 tarjetas** en el menú:
  1. Buscar ruta óptima
  2. Recorrido de línea
  3. ¿Qué líneas pasan aquí?
  4. Esperando microbús

---

### PANTALLA 3 — Buscar Ruta Óptima (FUNCIONALIDAD PRINCIPAL)

**Acceder:** Toca "Buscar ruta óptima" en el menú.

**Verificar al cargar:**
- El mapa OpenStreetMap CartoDB Light aparece centrado en Santa Cruz
- Aparecen **~106 puntos rojos** distribuidos por la ciudad (las paradas)
- Panel superior con dos botones: "Seleccionar Origen" y "Seleccionar Destino"
- Leyenda en esquina superior derecha: Parada (rojo), Origen (verde), Destino (azul)

**Prueba — seleccionar origen:**
1. Asegúrate de que "Seleccionar Origen" está activo (borde verde)
2. Toca cerca de un punto rojo (parada)
3. Debe aparecer SnackBar: "Origen: [nombre de la parada]"
4. El mapa muestra un icono verde grande en esa parada
5. El modo cambia automáticamente a "Seleccionar Destino"

**Prueba — seleccionar destino:**
1. Toca otro punto rojo en una zona diferente
2. Debe aparecer SnackBar: "Destino: [nombre de la parada]"
3. El mapa muestra un icono azul en esa parada

**Prueba — tap en zona sin paradas:**
1. Toca en el río, en un parque grande o alejado del centro
2. Debe aparecer SnackBar rojo: "No hay paradas en un radio de 2 km..."

**Prueba — buscar ruta:**
1. Con origen y destino seleccionados, toca **"Buscar Ruta Óptima"**
2. Botón muestra "Buscando..." mientras espera
3. Si hay ruta: navega a Resultados
4. Si no hay ruta entre esas paradas: SnackBar rojo de error

---

### PANTALLA 4 — Resultados de Ruta (ResultadosRutaScreen)

**Verificar:**
- AppBar muestra cantidad de rutas encontradas (ej. "3 Ruta(s) Encontradas")
- Cabecera con nombre origen → destino
- Lista de tarjetas ordenadas por tiempo (la más rápida primero)
- Primera tarjeta tiene badge "Mejor ruta" y borde destacado
- Cada tarjeta muestra:
  - Tiempo total (ej. "23 min")
  - Badge "Sin trasbordo" o "N trasbordo(s)"
  - Chips de colores con los nombres de las líneas (L001, etc.)

**Toca cualquier tarjeta** → navega al Detalle.

---

### PANTALLA 5 — Detalle de Ruta (DetalleRutaScreen)

**Verificar:**
- AppBar muestra "Detalle de Ruta" + tiempo en la derecha
- Resumen en 3 columnas: Tiempo total / Trasbordos / Líneas
- Timeline vertical con los pasos:
  - **Paso "ruta"**: ícono de bus del color de la línea, badge con nombre de línea (ej. L001), tiempo del segmento, parada de inicio (punto verde) y parada de fin (punto rojo)
  - **Paso "transbordo"**: ícono de transferencia, "Trasbordo", en qué parada, de qué línea a qué línea, penalización de 5 min
- El timeline conecta los pasos con líneas verticales

**Caso sin trasbordo:** Solo deben aparecer pasos tipo "ruta".
**Caso con trasbordo:** Debe alternar ruta → transbordo → ruta.

---

### PANTALLA 6 — Recorrido de Línea (RecorridoLineaScreen)

**Acceder:** Volver al menú → "Recorrido de línea".

**Verificar:**
- Chips horizontales con las líneas (L001, L002, etc.) en sus colores
- Toggle "Ida" / "Vuelta"
- Mapa OSM con polilínea del color de la línea seleccionada
- Marcador verde (inicio) y rojo (fin)
- Al cambiar de línea o sentido, la polilínea cambia y el mapa hace zoom al recorrido

**Prueba:**
1. Toca L001 → debe aparecer su recorrido en rojo (#E53935)
2. Toca "Vuelta" → polilínea cambia de dirección
3. Toca L002 → color cambia a morado (#8E24AA)

---

### PANTALLA 7 — Líneas Cercanas (LineasCercanasScreen)

**Acceder:** Menú → "¿Qué líneas pasan aquí?"

**Verificar:**
- Slider de radio (100m – 1000m) con color verde
- Botón "Usar mi GPS" y "Centro ciudad"

**Prueba con "Centro ciudad":**
1. Ajusta el radio a 500m
2. Toca "Centro ciudad"
3. Mapa hace zoom al centro de Santa Cruz
4. Aparece marcador verde de persona y círculo verde semitransparente
5. Lista con las líneas que pasan en ese radio
6. Toca una línea → abre Recorrido de Línea

**Prueba con GPS (celular físico):**
1. Toca "Usar mi GPS"
2. Acepta el permiso de ubicación
3. Debe mostrar tu posición actual con las líneas cercanas

---

### PANTALLA 8 — Esperando Microbús (EsperandoMicrobusScreen)

**Acceder:** Menú → "Esperando microbús".

**Verificar:**
- Lista horizontal de líneas (chips)
- Mapa OSM con íconos de bus (del color de la línea) por cada microbus activo
- Panel inferior con count de microbuses activos
- Toggle de auto-actualización cada 15s

**Prerequisito:** debe haber recorridos activos (los crea `seed_test_data.py`).
Si no hay activos, verás "No hay microbuses activos en esta línea ahora".

**Para activar microbuses:** ve a la pantalla de conductor (ver sección 4) o revisa que `seed_test_data.py` haya creado recorridos con estado activo.

---

## 4. Pruebas del flujo Conductor

### PANTALLA C1 — Login Conductor

**Acceder:** Pantalla inicio → "Soy Conductor".

**Credenciales de prueba (creadas por seed_test_data.py):**
- Email: `conductor1@test.com` / Contraseña: `pass1234`
- Email: `conductor2@test.com` / Contraseña: `pass1234`
- Email: `conductor3@test.com` / Contraseña: `pass1234`

**Verificar:** login exitoso → navega al dashboard del conductor.

### PANTALLA C2 — Dashboard Conductor

**Verificar:**
- Muestra el nombre del conductor y su microbus
- Botón para iniciar recorrido
- Información de la línea asignada

### Iniciar Recorrido GPS

1. Toca "Iniciar Recorrido"
2. Selecciona la línea y sentido
3. Acepta permiso GPS si lo pide
4. La app empieza a enviar posición cada 30 segundos al backend
5. **En otra instancia/emulador** como pasajero → "Esperando microbús" → debe ver el bus moverse en el mapa

---

## 5. Verificar en Django Admin

Accede a `http://localhost:8000/admin/` con el superusuario que creaste.

**Qué revisar:**
| Sección | Cantidad esperada |
|---|---|
| Lineas | 10 |
| Linea Rutas | ~20 (ida + vuelta por línea) |
| Puntos | ~2000+ |
| Linea Puntos | ~4000+ |
| Punto Trasbordos | según PuntosTrasbordos del Excel |
| Conductores | 3 (de seed_test_data) |
| Microbuses | 3 (SCZ001, SCZ002, SCZ003) |
| Recorridos | 2+ activos (de seed_test_data) |

---

## 6. Prueba directa del endpoint Dijkstra (Postman / curl)

```powershell
# Reemplaza las coordenadas por dos paradas reales de tu base de datos
# Puedes obtener coordenadas desde http://localhost:8000/api/paradas/

curl -X POST http://localhost:8000/api/buscar-ruta/ `
  -H "Content-Type: application/json" `
  -d '{"origen_lat": -17.783, "origen_lng": -63.182, "destino_lat": -17.790, "destino_lng": -63.170}'
```

**Respuesta esperada:**
```json
[
  {
    "tiempo_total_min": 18.5,
    "trasbordos": 0,
    "lineas": ["L001"],
    "origen_desc": "Parada ...",
    "destino_desc": "Parada ...",
    "pasos": [
      {
        "tipo": "ruta",
        "linea": "L001",
        "color": "#E53935",
        "desde_desc": "...",
        "hasta_desc": "...",
        "tiempo_min": 18.5
      }
    ]
  }
]
```

---

## 7. Checklist final

- [ ] Backend corre en `0.0.0.0:8000`
- [ ] `bus_mobile/.env` tiene la IP correcta (no `localhost`)
- [ ] `flutter pub get` ejecutado sin errores
- [ ] `/api/paradas/` retorna ~106 paradas
- [ ] `/api/lineas/` retorna 10 líneas
- [ ] App muestra puntos rojos en el mapa de búsqueda
- [ ] Tap → snap a parada cercana + SnackBar con nombre
- [ ] Tap lejos → SnackBar de error rojo
- [ ] Buscar ruta → llega a pantalla de resultados
- [ ] Resultados muestran tiempo, trasbordos y líneas
- [ ] Detalle muestra timeline paso a paso
- [ ] Recorrido de línea muestra polilínea correcta
- [ ] Líneas cercanas funciona con "Centro ciudad"
- [ ] Login de conductor funciona con credenciales de prueba
