#!/bin/bash

# Script para levantar el entorno de desarrollo completo
# Uso: ./scripts/dev.sh

set -e

echo "🚀 Iniciando entorno de desarrollo BONAPHARM..."

# Copiar variables de entorno si no existe .env
if [ ! -f .env ]; then
    echo "📝 Copiando .env.development a .env..."
    cp .env.development .env
fi

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker no está corriendo. Por favor inicia Docker Desktop."
    exit 1
fi

# Levantar PostgreSQL
echo "🐘 Iniciando PostgreSQL..."
docker-compose up -d db

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 5

# Verificar si Python está disponible
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python no está instalado."
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)

# Instalar dependencias de Python si es necesario
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 Instalando dependencias de Python..."
    $PYTHON_CMD -m pip install -r api/requirements.txt
fi

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones de base de datos..."
alembic upgrade head

# Verificar si npm está disponible
if ! command -v npm &> /dev/null; then
    echo "❌ npm no está instalado."
    exit 1
fi

# Instalar dependencias de Node si es necesario
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias de npm..."
    npm install
fi

echo ""
echo "✅ Entorno preparado!"
echo ""
echo "🎯 Para iniciar el desarrollo:"
echo "   Backend:  uvicorn api.main:app --reload --port 8000"
echo "   Frontend: npm run dev"
echo ""
echo "📚 URLs:"
echo "   Frontend: http://localhost:5173"
echo "   API:      http://localhost:8000"
echo "   Docs:     http://localhost:8000/docs"
echo ""
