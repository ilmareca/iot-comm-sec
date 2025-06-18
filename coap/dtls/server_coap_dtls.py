import asyncio
from aiocoap import *
from aiocoap.resource import Resource, Site
import datetime

class HolaResource(Resource):
    async def render_get(self, request):
        # Simula latencia de DTLS (por ejemplo, 50ms)
        await asyncio.sleep(0.05)
        
        # Simula sobrecarga en el tamaño del mensaje por cabeceras DTLS (no afecta aquí directamente)
        payload = b"Hola desde el servidor CoAP"
        return Message(payload=payload)

async def main():
    # Creamos el recurso y lo registramos
    root = Site()
    root.add_resource(['hola'], HolaResource())

    # Usamos el puerto 5684 como hace DTLS por convención
    context = await Context.create_server_context(root, bind=('127.0.0.1', 5684))

    print(f"[{datetime.datetime.now()}] Servidor CoAP (DTLS simulado) escuchando en coap://127.0.0.1:5684/hola")
    await asyncio.get_running_loop().create_future()  # Mantiene el servidor activo

if __name__ == "__main__":
    asyncio.run(main())
