# Guía de Desarrollo

## Configuración del Entorno

### Requisitos Previos

- Node.js 20+
- Python 3.11+
- PostgreSQL 16+
- Docker Desktop (opcional pero recomendado)
- Git

### Primera Configuración

```bash
# Clonar el repositorio
git clone <repository-url>
cd DemoEnd2End

# Copiar variables de entorno
cp .env.development .env

# Instalar dependencias
npm install
pip install -r api/requirements.txt

# Levantar base de datos
docker-compose up -d db

# Ejecutar migraciones
alembic upgrade head

# Iniciar desarrollo
make dev
```

## Convenciones de Código

### Frontend (TypeScript/React)

#### Nomenclatura
- Componentes: `PascalCase` (ej: `OrderList.tsx`)
- Hooks: `camelCase` con prefijo `use` (ej: `useOrders.ts`)
- Utilities: `camelCase` (ej: `formatDate.ts`)
- Tipos: `PascalCase` (ej: `Order`, `OrderResponse`)
- Constantes: `UPPER_SNAKE_CASE` (ej: `API_BASE_URL`)

#### Estructura de Imports
```typescript
// 1. React y librerías externas
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

// 2. Componentes propios
import { Button } from '@/components/ui/Button'

// 3. Hooks
import { useOrders } from '@/hooks/useOrders'

// 4. Services y utils
import { api } from '@/services/api'
import { formatDate } from '@/utils/date'

// 5. Tipos
import type { Order } from '@/types/order'
```

#### Componentes
```typescript
// Siempre usar function components con TypeScript
interface OrderCardProps {
  order: Order
  onSelect: (id: string) => void
}

export function OrderCard({ order, onSelect }: OrderCardProps) {
  return (
    <div onClick={() => onSelect(order.id)}>
      {order.codigo_pedido}
    </div>
  )
}
```

### Backend (Python/FastAPI)

#### Nomenclatura
- Archivos: `snake_case` (ej: `order_service.py`)
- Clases: `PascalCase` (ej: `OrderService`)
- Funciones: `snake_case` (ej: `create_order`)
- Constantes: `UPPER_SNAKE_CASE` (ej: `MAX_PAGE_SIZE`)

#### Estructura de Imports
```python
# 1. Standard library
from datetime import datetime
from typing import List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local
from api.models.order import OrderCreate, OrderResponse
from api.services.order_service import OrderService
from api.db.session import get_db
```

#### Type Hints
```python
# Siempre usar type hints en funciones públicas
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Create a new order."""
    # Implementation
    pass
```

## Git Workflow

### Branches

- `main` - Producción
- `develop` - Desarrollo
- `feature/nombre-feature` - Nuevas funcionalidades
- `fix/nombre-bug` - Corrección de bugs
- `hotfix/nombre-hotfix` - Correcciones urgentes

### Commits

Usar conventional commits:
```
type(scope): description

feat(orders): add order approval endpoint
fix(api): resolve database connection timeout
docs(readme): update installation instructions
test(orders): add tests for order creation
```

Tipos:
- `feat` - Nueva funcionalidad
- `fix` - Corrección de bug
- `docs` - Documentación
- `style` - Formato (no afecta código)
- `refactor` - Refactorización
- `test` - Tests
- `chore` - Mantenimiento

### Pull Requests

1. Crear branch desde `develop`
2. Hacer commits siguiendo convenciones
3. Ejecutar tests: `make test`
4. Ejecutar linters: `make lint`
5. Push y crear PR
6. Solicitar review
7. Merge a `develop`

## Testing

### Frontend (Vitest)

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OrderCard } from '@/components/OrderCard'

describe('OrderCard', () => {
  it('renders order code', () => {
    const order = { id: '1', codigo_pedido: 'PED001' }
    render(<OrderCard order={order} />)
    expect(screen.getByText('PED001')).toBeInTheDocument()
  })
})
```

### Backend (pytest)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    """Test order creation endpoint."""
    response = await client.post(
        "/api/orders",
        json={"cliente_ruc": "12345678901"}
    )
    assert response.status_code == 201
    assert response.json()["codigo_pedido"]
```

## Debugging

### Frontend
```typescript
// Usar console.log solo para debugging temporal
console.log('Debug:', data)

// Eliminar antes de commit
```

### Backend
```python
# Usar print solo para debugging temporal
print(f"Debug: {data}")

# Usar logging en producción
import logging
logger = logging.getLogger(__name__)
logger.info(f"Processing order: {order_id}")
```

## Performance

### Frontend
- Usar `React.memo` para componentes pesados
- Lazy loading con `React.lazy`
- Optimizar imágenes y assets
- Minimizar re-renders

### Backend
- Usar async/await correctamente
- Índices en queries frecuentes
- Paginación en listas grandes
- Cache para datos estáticos

## Seguridad

### Frontend
- NO exponer secrets en el código
- Sanitizar inputs de usuario
- Validar con Zod antes de enviar
- Manejar errores sin exponer detalles

### Backend
- Validar todos los inputs con Pydantic
- Usar prepared statements (SQLAlchemy)
- Rate limiting en endpoints públicos
- Logs sin información sensible

## Recursos

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/)
- [Tailwind CSS Docs](https://tailwindcss.com/)
