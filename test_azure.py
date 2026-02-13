import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Cargar variables
load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

print(f"--- DIAGNÓSTICO AZURE ---")
print(f"1. Endpoint:   '{ENDPOINT}'")
print(f"2. Despliegue: '{DEPLOYMENT}'")
print(f"3. Versión:    '{VERSION}'")
print(f"4. Key (fin):  ...{KEY[-4:] if KEY else 'None'}")

async def test_connection():
    if not KEY or not ENDPOINT:
        print("❌ ERROR: Faltan variables en el .env")
        return

    client = AsyncAzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=KEY,
        api_version=VERSION
    )

    print("\n📡 Intentando conectar con Azure OpenAI...")
    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[{"role": "user", "content": "Hola, ¿estás activo?"}],
            max_tokens=10
        )
        print("✅ ¡ÉXITO! Azure respondió:")
        print(response.choices[0].message.content)
    except Exception as e:
        print("\n❌ FALLÓ LA CONEXIÓN:")
        print(e)
        print("\n--- POSIBLES CAUSAS ---")
        if "404" in str(e):
            print("👉 CAUSA PROBABLE: La CLAVE no pertenece a este ENDPOINT.")
            print(f"   Asegúrate de copiar la Key 1 del recurso '{ENDPOINT.split('.')[0].replace('https://', '')}' en Azure Portal.")
            print("👉 OTRA CAUSA: El nombre del despliegue está mal escrito en el .env.")
        elif "401" in str(e):
            print("👉 CAUSA PROBABLE: Clave incorrecta o expirada.")

if __name__ == "__main__":
    asyncio.run(test_connection())