#!/usr/bin/env python3
"""
OSCORE Group - Servidor y Cliente con credenciales persistentes
Las credenciales se generan una vez y se guardan en archivos
"""

import asyncio
import logging
import secrets
import sys
import argparse
import json
import os
from aiocoap import *
from aiocoap.resource import Site, Resource
from aiocoap.oscore import SimpleGroupContext, A128GCM, Ed25519, hashfunctions
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper
from aiocoap.credentials import CredentialsMap

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Archivo para guardar credenciales
CREDENTIALS_FILE = "oscore_group_credentials.json"

# Configuración del grupo
GROUP_CONFIG = {
    'group_id': b"grp1",
    'master_secret': bytes.fromhex("425a524d5a32f7d0d386603359fa3832"),
    'master_salt': bytes.fromhex("1b0b57f74ef4099c"),
    'client_id': b"C1",
    'server_id': b"S1"
}

def generate_and_save_credentials():
    """Generar credenciales una sola vez y guardarlas"""
    
    logger.info("🔑 Generando credenciales nuevas...")
    
    # Algoritmos
    alg_signature = Ed25519()
    
    # Generar credenciales
    gm_private_key, gm_cred = alg_signature.generate_with_ccs()
    client_private_key, client_cred = alg_signature.generate_with_ccs()
    server_private_key, server_cred = alg_signature.generate_with_ccs()
    
    # Crear estructura para guardar
    credentials = {
        'group_manager': {
            'private_key': gm_private_key.hex(),
            'credential': gm_cred.hex()
        },
        'client': {
            'private_key': client_private_key.hex(),
            'credential': client_cred.hex()
        },
        'server': {
            'private_key': server_private_key.hex(),
            'credential': server_cred.hex()
        }
    }
    
    # Guardar en archivo
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    logger.info(f"✅ Credenciales guardadas en {CREDENTIALS_FILE}")
    return credentials

def load_credentials():
    """Cargar credenciales desde archivo"""
    
    if not os.path.exists(CREDENTIALS_FILE):
        logger.info("📄 Archivo de credenciales no existe, generando...")
        return generate_and_save_credentials()
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
        logger.info("✅ Credenciales cargadas desde archivo")
        return credentials
    except Exception as e:
        logger.error(f"❌ Error cargando credenciales: {e}")
        logger.info("🔄 Regenerando credenciales...")
        return generate_and_save_credentials()

def create_group_context(is_client=True):
    """Crear contexto OSCORE Group usando credenciales persistentes"""
    
    # Cargar credenciales
    creds = load_credentials()
    
    # Algoritmos
    alg_aead = A128GCM()
    alg_signature = Ed25519()
    alg_group_enc = A128GCM()
    alg_pairwise_key_agreement = None
    hashfun = hashfunctions["sha256"]
    
    # Credenciales del group manager
    gm_private_key = bytes.fromhex(creds['group_manager']['private_key'])
    gm_cred = bytes.fromhex(creds['group_manager']['credential'])
    
    if is_client:
        sender_id = GROUP_CONFIG['client_id']
        private_key = bytes.fromhex(creds['client']['private_key'])
        sender_cred = bytes.fromhex(creds['client']['credential'])
        # El cliente conoce al servidor
        peers = {
            GROUP_CONFIG['server_id']: bytes.fromhex(creds['server']['credential'])
        }
    else:
        sender_id = GROUP_CONFIG['server_id']
        private_key = bytes.fromhex(creds['server']['private_key'])
        sender_cred = bytes.fromhex(creds['server']['credential'])
        # El servidor conoce al cliente
        peers = {
            GROUP_CONFIG['client_id']: bytes.fromhex(creds['client']['credential'])
        }
    
    try:
        context = SimpleGroupContext(
            alg_aead=alg_aead,
            hashfun=hashfun,
            alg_signature=alg_signature,
            alg_group_enc=alg_group_enc,
            alg_pairwise_key_agreement=alg_pairwise_key_agreement,
            group_id=GROUP_CONFIG['group_id'],
            master_secret=GROUP_CONFIG['master_secret'],
            master_salt=GROUP_CONFIG['master_salt'],
            sender_id=sender_id,
            private_key=private_key,
            sender_auth_cred=sender_cred,
            peers=peers,
            group_manager_cred=gm_cred
        )
        
        logger.info(f"✅ Contexto {'cliente' if is_client else 'servidor'} creado")
        logger.info(f"   Sender ID: {sender_id.hex()}")
        logger.info(f"   Group ID: {GROUP_CONFIG['group_id'].hex()}")
        
        return context
        
    except Exception as e:
        logger.error(f"❌ Error creando contexto: {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== SERVIDOR ====================

class GroupOscoreResource(Resource):
    """Recurso del servidor OSCORE Group"""
    
    async def render_get(self, request):
        logger.info("📨 Servidor recibió GET request protegido con OSCORE Group")
        logger.info(f"   Remote: {request.remote}")
        logger.info(f"   Payload: {request.payload}")
        logger.info(f"   URI Path: {getattr(request.opt, 'uri_path', 'N/A')}")
        
        response_text = f"Hello from OSCORE Group Server! Received: {request.payload.decode('utf-8', errors='ignore')}"
        return Message(payload=response_text.encode('utf-8'), code=CONTENT)

    async def render_post(self, request):
        logger.info("📨 Servidor recibió POST request protegido con OSCORE Group")
        logger.info(f"   Remote: {request.remote}")
        logger.info(f"   Payload: {request.payload}")
        logger.info(f"   URI Path: {getattr(request.opt, 'uri_path', 'N/A')}")
        
        response_text = f"Processed by Group Server: {request.payload.decode('utf-8', errors='ignore')}"
        return Message(payload=response_text.encode('utf-8'), code=CHANGED)

async def run_server(port=5683):
    """Ejecutar servidor OSCORE Group"""
    
    logger.info("🚀 Iniciando servidor OSCORE Group...")
    
    # Crear contexto OSCORE Group
    server_context = create_group_context(is_client=False)
    if not server_context:
        logger.error("❌ No se pudo crear contexto del servidor")
        return
    
    # Configurar credenciales para OSCORE
    server_credentials = CredentialsMap()
    server_credentials[":"] = server_context
    
    # Crear sitio web
    root = Site()
    root.add_resource(['hello'], GroupOscoreResource())
    root.add_resource(['api', 'data'], GroupOscoreResource())
    root.add_resource(['test'], GroupOscoreResource())
    
    # Envolver con OSCORE
    try:
        wrapped_site = OscoreSiteWrapper(root, server_credentials)
        logger.info("✅ Sitio envuelto con OSCORE Group")
    except Exception as e:
        logger.error(f"❌ Error envolviendo sitio: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Crear contexto del servidor
    try:
        context = await Context.create_server_context(
            bind=('localhost', port),
            site=wrapped_site
        )
        
        logger.info(f"🌐 Servidor OSCORE Group ejecutándose en puerto {port}")
        logger.info("📡 ¡El tráfico OSCORE Group ahora es visible en Wireshark!")
        logger.info("🔍 Filtro Wireshark: udp.port == 5683")
        logger.info("🔍 Busca paquetes CoAP con opción OSCORE y payload cifrado")
        logger.info("🛑 Presiona Ctrl+C para detener")
        
        # Mantener servidor ejecutándose
        try:
            await asyncio.Future()  # Ejecutar para siempre
        except KeyboardInterrupt:
            logger.info("🛑 Deteniendo servidor...")
        finally:
            await context.shutdown()
            
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor: {e}")
        import traceback
        traceback.print_exc()

# ==================== CLIENTE ====================

async def run_client(server_host='localhost', server_port=5683):
    """Ejecutar cliente OSCORE Group"""
    
    logger.info("🚀 Iniciando cliente OSCORE Group...")
    
    # Crear contexto OSCORE Group
    client_context = create_group_context(is_client=True)
    if not client_context:
        logger.error("❌ No se pudo crear contexto del cliente")
        return
    
    # Crear contexto del cliente sin credenciales primero
    try:
        context = await Context.create_client_context()
        logger.info("✅ Cliente OSCORE Group configurado")
        
        # Esperar para asegurar conexión
        await asyncio.sleep(2)
        
        logger.info("📡 Enviando requests protegidos con OSCORE Group...")
        logger.info("🔍 Monitorea Wireshark para ver el tráfico cifrado!")
        
        # Para cada request, tendremos que proteger/desproteger manualmente
        # ya que la versión de aiocoap no soporta el wrapper automático
        
        # ===== TEST 1: GET Request =====
        logger.info("\n📤 TEST 1: GET request manual a /hello")
        
        # Crear request original
        original_request = Message(
            code=GET,
            payload=b"Hello from OSCORE Group client!"
        )
        original_request.opt.uri_path = ["hello"]
        
        # Proteger con OSCORE Group
        protected_request, request_id = client_context.protect(original_request)
        
        # Establecer URI para el request protegido
        protected_request.set_request_uri(f"coap://{server_host}:{server_port}/")
        
        logger.info(f"🔐 Request protegido - OSCORE option: {protected_request.opt.oscore.hex()}")
        logger.info(f"🔐 Payload cifrado: {len(protected_request.payload)} bytes")
        
        try:
            # Enviar request protegido
            response = await context.request(protected_request).response
            logger.info(f"✅ Response recibido del servidor (tamaño: {len(response.payload)} bytes)")
            logger.info(f"📊 Response code: {response.code}")
            
            # Para este test, no desprotegemos la response ya que es más complejo
            # El objetivo principal es generar tráfico OSCORE visible en Wireshark
            
        except Exception as e:
            logger.error(f"❌ Error en GET request: {e}")
        
        await asyncio.sleep(1)
        
        # ===== TEST 2: POST Request =====
        logger.info("\n📤 TEST 2: POST request manual a /api/data")
        
        original_post = Message(
            code=POST,
            payload=b"Data from Group client for processing"
        )
        original_post.opt.uri_path = ["api", "data"]
        
        protected_post, post_request_id = client_context.protect(original_post)
        protected_post.set_request_uri(f"coap://{server_host}:{server_port}/")
        
        logger.info(f"🔐 POST protegido - OSCORE option: {protected_post.opt.oscore.hex()}")
        logger.info(f"🔐 Payload cifrado: {len(protected_post.payload)} bytes")
        
        try:
            post_response = await context.request(protected_post).response
            logger.info(f"✅ POST Response recibido (tamaño: {len(post_response.payload)} bytes)")
            logger.info(f"📊 Response code: {post_response.code}")
        except Exception as e:
            logger.error(f"❌ Error en POST request: {e}")
        
        await asyncio.sleep(1)
        
        # ===== TEST 3: Múltiples requests =====
        logger.info("\n📤 TEST 3: Múltiples requests para generar más tráfico")
        for i in range(5):
            test_message = Message(
                code=GET,
                payload=f"OSCORE Group test message #{i+1}".encode()
            )
            test_message.opt.uri_path = ["test"]
            
            protected_test, test_req_id = client_context.protect(test_message)
            protected_test.set_request_uri(f"coap://{server_host}:{server_port}/")
            
            try:
                test_response = await context.request(protected_test).response
                logger.info(f"✅ Test {i+1}: Response recibido ({len(test_response.payload)} bytes)")
            except Exception as e:
                logger.error(f"❌ Error en test {i+1}: {e}")
            
            await asyncio.sleep(0.5)
        
        logger.info("\n🎉 Cliente OSCORE Group completado!")
        logger.info("📊 Revisa Wireshark para ver todos los paquetes OSCORE intercambiados")
        logger.info("🔍 Busca:")
        logger.info("   - Protocolo: CoAP")
        logger.info("   - Opción OSCORE en los headers")
        logger.info("   - Payload binario cifrado (no texto plano)")
        logger.info("   - Paquetes de tamaño mayor por las firmas")
        
    except Exception as e:
        logger.error(f"❌ Error en cliente: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'context' in locals():
            await context.shutdown()

# ==================== UTILIDADES ====================

def reset_credentials():
    """Eliminar credenciales para regenerarlas"""
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
        logger.info(f"🗑️ Credenciales eliminadas. Se regenerarán en la próxima ejecución.")
    else:
        logger.info("❌ No hay credenciales para eliminar.")

def show_credentials_info():
    """Mostrar información de las credenciales"""
    if not os.path.exists(CREDENTIALS_FILE):
        logger.info("❌ No hay credenciales guardadas.")
        return
    
    try:
        creds = load_credentials()
        logger.info("📋 INFORMACIÓN DE CREDENCIALES:")
        logger.info(f"   Group ID: {GROUP_CONFIG['group_id'].hex()}")
        logger.info(f"   Cliente ID: {GROUP_CONFIG['client_id'].hex()}")
        logger.info(f"   Servidor ID: {GROUP_CONFIG['server_id'].hex()}")
        logger.info(f"   Master Secret: {GROUP_CONFIG['master_secret'].hex()}")
        logger.info(f"   Master Salt: {GROUP_CONFIG['master_salt'].hex()}")
        logger.info("   ✅ Credenciales cargadas correctamente")
    except Exception as e:
        logger.error(f"❌ Error leyendo credenciales: {e}")

# ==================== MAIN ====================

async def main():
    """Función principal"""
    
    parser = argparse.ArgumentParser(description='OSCORE Group Server/Client para Wireshark')
    parser.add_argument('mode', choices=['server', 'client', 'reset', 'info'], 
                       help='Modo: server, client, reset (credenciales), info')
    parser.add_argument('--port', type=int, default=5683, help='Puerto del servidor')
    parser.add_argument('--host', default='localhost', help='Host del servidor')
    
    args = parser.parse_args()
    
    if args.mode == 'reset':
        reset_credentials()
        return
    elif args.mode == 'info':
        show_credentials_info()
        return
    elif args.mode == 'server':
        logger.info("🖥️ Modo: SERVIDOR OSCORE GROUP")
        await run_server(args.port)
    else:
        logger.info("👤 Modo: CLIENTE OSCORE GROUP")
        await run_client(args.host, args.port)

if __name__ == "__main__":
    print("🚀 OSCORE Group - Red Real con Credenciales Persistentes")
    print("="*60)
    print("🔍 Este código genera tráfico visible en Wireshark")
    print("📁 Las credenciales se guardan en archivo para consistencia")
    print("="*60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Programa interrumpido")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)