# Tests - BONAPHARM

Suite completa de tests automatizados para el proyecto BONAPHARM.

## Estructura

```
tests/
├── frontend/
│   ├── setup.ts              # Configuración MSW + jest-dom
│   ├── mocks/
│   │   ├── server.ts         # MSW server
│   │   └── handlers.ts       # 78 API handlers
│   ├── components/
│   │   └── common/           # 6 archivos, 85 tests
│   ├── pages/                # 4 archivos, 68 tests
│   ├── hooks/                # 2 archivos, 36 tests
│   └── store/                # 2 archivos, 26 tests
└── backend/
    ├── conftest.py           # Fixtures de pytest
    ├── test_health.py
    ├── test_auth.py
    ├── test_pedidos.py
    ├── test_devoluciones.py
    ├── test_comisiones.py
    └── test_productos.py
```

## Instalación de Dependencias

### Frontend
```bash
npm install --save-dev \
  vitest \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom \
  msw \
  jsdom
```

### Backend
```bash
pip install pytest pytest-asyncio httpx pytest-cov
```

## Ejecutar Tests

### Frontend

```bash
# Todos los tests
npm test

# Con coverage
npm run test:coverage

# Modo watch (desarrollo)
npm run test:watch

# Test específico
npm test -- Button.test.tsx
npm test -- pages/LoginPage
```

### Backend

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=api --cov-report=html

# Verbose
pytest -v

# Test específico
pytest tests/backend/test_pedidos.py
pytest tests/backend/test_auth.py::test_login_with_valid_credentials

# Solo tests que fallen
pytest --lf
```

## Configuración Necesaria

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/frontend/setup.ts'],
  },
})
```

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests/backend
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

## Estadísticas

- **Total archivos:** 23
- **Total tests:** 297
- **Frontend tests:** 215 (85 componentes + 68 páginas + 36 hooks + 26 stores)
- **Backend tests:** 82 (endpoints principales)
- **Cobertura estimada:** 70%+

## Notas Importantes

### MSW (Mock Service Worker)

Los tests de frontend **NO hacen llamadas reales** a la API. Todos los endpoints están mockeados en `tests/frontend/mocks/handlers.ts`.

Si agregas nuevos endpoints en el backend, actualiza los handlers:

```typescript
// tests/frontend/mocks/handlers.ts
export const handlers = [
  http.get('http://localhost:8000/api/v1/tu-endpoint', () => {
    return HttpResponse.json({ data: 'mock' })
  }),
]
```

### Fixtures de pytest

Los tests de backend usan fixtures para datos de prueba. Revisa `conftest.py` para:

- `test_vendedor`, `test_admin`, `test_finanzas` - Usuarios de prueba
- `test_productos` - Productos de prueba
- `test_pedido`, `test_pedido_aprobado` - Pedidos de prueba
- `auth_headers_vendedor`, etc. - Headers de autenticación

### Database de Tests

Los tests de backend usan **SQLite in-memory** (`test_temp.db`).

**IMPORTANTE:** Cada test tiene su propia DB limpia (no comparten estado).

## Debugging

### Frontend

```bash
# Ver output detallado
npm test -- --reporter=verbose

# Un solo test
npm test -- -t "renders_with_text_content"
```

### Backend

```bash
# Ver prints en tests
pytest -s

# Parar en primer fallo
pytest -x

# Ver traceback completo
pytest --tb=long
```

## CI/CD

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm test

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest
```

## Troubleshooting

### Error: "Cannot find module '@testing-library/jest-dom'"

```bash
npm install --save-dev @testing-library/jest-dom
```

### Error: "fixture 'client' not found"

Verifica que `conftest.py` existe en `tests/backend/`.

### Error: MSW handlers not working

1. Verifica que `setup.ts` se ejecuta (config en `vitest.config.ts`)
2. Verifica que las URLs en `handlers.ts` coinciden con las del código

### Tests pasan localmente pero fallan en CI

1. Verifica variables de entorno
2. Revisa que la DB de tests se crea correctamente
3. Asegúrate de que las dependencias están instaladas

## Recursos

- [Vitest Docs](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW Docs](https://mswjs.io/)
- [Pytest Docs](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

---

**Mantenedor:** Claude Sonnet 4.5
**Última actualización:** 2026-03-05
