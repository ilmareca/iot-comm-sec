import asyncio
from aiocoap import resource, Message, Context
from aiocoap.numbers.codes import Code

class HelloResource(resource.Resource):
    async def render_get(self, request):
        payload = b"Hola desde el servidor CoAP"
        return Message(code=Code.CONTENT, payload=payload)

async def main():
    # Crear el árbol de recursos
    root = resource.Site()
    root.add_resource(('hola',), HelloResource())

    # Crear el contexto del servidor
    context = await Context.create_server_context(root, bind=('127.0.0.1', 5683))

    # Mantener el servidor activo
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
