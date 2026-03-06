# Documentación de API

## Endpoints Base

### Health Check
```
GET /health
```
Verifica el estado del servicio.

**Response:**
```json
{
  "status": "ok",
  "service": "bonapharm-api",
  "version": "0.1.0",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Root
```
GET /
```
Información general de la API.

**Response:**
```json
{
  "message": "BONAPHARM - API de Pedidos y Devoluciones",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

## Endpoints de Negocio

Los siguientes endpoints serán implementados por el backend agent:

### Productos
- `GET /api/productos` - Listar productos
- `GET /api/productos/{id}` - Obtener producto
- `POST /api/productos` - Crear producto
- `PUT /api/productos/{id}` - Actualizar producto
- `DELETE /api/productos/{id}` - Eliminar producto

### Pedidos
- `GET /api/pedidos` - Listar pedidos
- `GET /api/pedidos/{id}` - Obtener pedido
- `POST /api/pedidos` - Crear pedido
- `PUT /api/pedidos/{id}` - Actualizar pedido
- `PATCH /api/pedidos/{id}/aprobar` - Aprobar pedido
- `PATCH /api/pedidos/{id}/rechazar` - Rechazar pedido

### Devoluciones
- `GET /api/devoluciones` - Listar devoluciones
- `GET /api/devoluciones/{id}` - Obtener devolución
- `POST /api/devoluciones` - Crear devolución
- `PUT /api/devoluciones/{id}` - Actualizar devolución
- `PATCH /api/devoluciones/{id}/aprobar` - Aprobar devolución

### Comisiones
- `GET /api/comisiones` - Listar comisiones
- `POST /api/comisiones/calcular` - Calcular comisiones del mes
- `GET /api/comisiones/reporte/{mes}` - Generar reporte

## Autenticación

Todos los endpoints (excepto `/health` y `/`) requieren autenticación via JWT.

**Header:**
```
Authorization: Bearer <access_token>
```

## Códigos de Estado

- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Documentación Interactiva

Swagger UI disponible en: http://localhost:8000/docs
ReDoc disponible en: http://localhost:8000/redoc
