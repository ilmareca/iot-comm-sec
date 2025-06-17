#!/usr/bin/env python3
"""
Simulación OSCORE Group - Cliente
Requiere: pip install aiocoap[oscore]
"""

import asyncio
import aiocoap
from aiocoap.oscore import SimpleGroupManager
from aiocoap.credentials import CredentialsMap
import binascii
import logging
import random
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)

class OSCOREClient:
    """Cliente OSCORE para comunicación de grupo"""
    
    def __init__(self, client_id="cliente1"):
        self.client_id = client_id
        self.context = None
        
    async def setup(self):
        """Configurar cliente OSCORE"""
        # Misma configuración que el servidor para el grupo
        group_id = b"grupo_demo"
        master_secret = binascii.unhexlify("0123456789abcdef0123456789abcdef")
        master_salt = binascii.unhexlify("9e7ca92223786340")
        
        # Crear gestor de grupo para cliente
        group_manager = SimpleGroupManager(
            group_id=group_id,
            master_secret=master_secret,
            master_salt=master_salt,
            sender_id=self.client_id.encode(),
            algorithm_signature=None
        )
        
        # Configurar credenciales
        credentials = CredentialsMap()
        credentials[f"oscore:group:{group_id.decode()}"] = group_manager
        
        # Crear contexto del cliente
        self.context = await aiocoap.Context.create_client_context(
            credentials=credentials
        )
        
        print(f"🔐 Cliente {self.client_id} configurado para grupo: {group_id.decode()}")
    
    async def send_message(self, message):
        """Enviar mensaje al grupo"""
        try:
            uri = "coap://127.0.0.1:5683/grupo"
            
            request = aiocoap.Message(
                code=aiocoap.POST,
                payload=f"[{self.client_id}] {message}".encode('utf-8'),
                uri=uri
            )
            
            # Configurar para usar OSCORE Group
            request.opt.oscore = b""
            
            print(f"📤 Enviando: {message}")
            response = await self.context.request(request).response
            
            print(f"✅ Respuesta: {response.payload.decode()}")
            return response
            
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return None
    
    async def get_messages(self):
        """Obtener mensajes del grupo"""
        try:
            uri = "coap://127.0.0.1:5683/grupo"
            
            request = aiocoap.Message(
                code=aiocoap.GET,
                uri=uri
            )
            
            # Configurar para usar OSCORE Group
            request.opt.oscore = b""
            
            response = await self.context.request(request).response
            print(f"📋 Estado del grupo:\n{response.payload.decode()}")
            return response
            
        except Exception as e:
            print(f"❌ Error obteniendo mensajes: {e}")
            return None
    
    async def close(self):
        """Cerrar conexión"""
        if self.context:
            await self.context.shutdown()

async def simulate_client(client_id, num_messages=3):
    """Simular actividad de un cliente"""
    client = OSCOREClient(client_id)
    await client.setup()
    
    try:
        # Enviar algunos mensajes
        messages = [
            f"Hola desde {client_id}",
            f"Mensaje {random.randint(1, 100)} de {client_id}",
            f"Prueba de seguridad - {client_id}",
            f"Timestamp: {int(time.time())} - {client_id}",
            f"Último mensaje de {client_id}"
        ]
        
        for i in range(num_messages):
            await client.send_message(messages[i % len(messages)])
            await asyncio.sleep(1)  # Pausa entre mensajes
        
        # Obtener estado del grupo
        await client.get_messages()
        
    finally:
        await client.close()

async def main():
    """Función principal - simular múltiples clientes"""
    print("🚀 Iniciando simulación de clientes OSCORE Group")
    print("🔗 Conectando a servidor en 127.0.0.1:5683")
    
    # Simular múltiples clientes enviando mensajes
    tasks = []
    
    # Crear varios clientes simulados
    for i in range(2):
        client_id = f"cliente_{i+1}"
        task = simulate_client(client_id, 2)
        tasks.append(task)
    
    try:
        # Ejecutar todos los clientes concurrentemente
        await asyncio.gather(*tasks)
        
        print("\n✅ Simulación completada")
        print("💡 Revisa la salida del servidor para ver los mensajes recibidos")
        
    except Exception as e:
        print(f"❌ Error en simulación: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Simulación interrumpida")