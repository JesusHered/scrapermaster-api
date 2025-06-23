#!/bin/bash

# Script de inicio para EasyPanel
echo "Iniciando ScraperMaster API..."

# Verificar que el archivo main.py existe
if [ ! -f "main.py" ]; then
    echo "Error: main.py no encontrado"
    exit 1
fi

# Ejecutar la aplicación
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
