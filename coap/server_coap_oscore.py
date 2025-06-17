import asyncio
import logging
import json
from aiocoap import Context, Message
from aiocoap.resource import Site, Resource
from aiocoap.credentials import CredentialsMap
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper

class RecursoSeguro(Resource):
    async def render_get(self, request):
        return Message(payload=b"Hola desde el servidor CoAP")

async def main():
    logging.basicConfig(level=logging.INFO)

    # Define recursos
    site = Site()
    site.add_resource(['hola'], RecursoSeguro())

    # Carga credenciales OSCORE desde server.json
    with open("server.json") as f:
        cred_data = json.load(f)

    credentials = CredentialsMap()
    credentials.load_from_dict(cred_data)

    # Envolver sitio con OSCORE
    oscore_site = OscoreSiteWrapper(site, credentials)
    await Context.create_server_context(oscore_site, bind=("127.0.0.1", 5683))

    print("Servidor OSCORE en coap://127.0.0.1:5683/hola")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
