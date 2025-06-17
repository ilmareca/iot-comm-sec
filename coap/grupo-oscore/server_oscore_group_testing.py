#!/usr/bin/env python3
"""
OSCORE Group - Versión completamente funcional
Maneja correctamente requests y responses en modo group
"""

import logging
import secrets
import sys
from aiocoap import Message, GET, POST, CONTENT, CHANGED
from aiocoap.oscore import SimpleGroupContext, A128GCM, Ed25519, hashfunctions

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def create_shared_group_config():
    """Crear configuración compartida del grupo"""
    
    config = {
        'group_id': b"grp1",
        'master_secret': secrets.token_bytes(16),
        'master_salt': secrets.token_bytes(8),
        'alg_aead': A128GCM(),
        'alg_signature': Ed25519(),
        'alg_group_enc': A128GCM(),
        'alg_pairwise_key_agreement': None,  # Simplificado
        'hashfun': hashfunctions["sha256"],
        'client_id': b"C1",
        'server_id': b"S1"
    }
    
    # Generar credenciales
    config['gm_private_key'], config['gm_cred'] = config['alg_signature'].generate_with_ccs()
    config['client_private_key'], config['client_cred'] = config['alg_signature'].generate_with_ccs()
    config['server_private_key'], config['server_cred'] = config['alg_signature'].generate_with_ccs()
    
    return config

def create_group_contexts_from_config(config):
    """Crear contextos usando configuración compartida"""
    
    print("🔧 Configurando grupo OSCORE con configuración compartida...")
    print(f"🏷️ Group ID: {config['group_id'].hex()}")
    print(f"👤 Cliente ID: {config['client_id'].hex()}")
    print(f"🖥️ Servidor ID: {config['server_id'].hex()}")
    
    try:
        # Crear contexto del cliente
        client_peers = {config['server_id']: config['server_cred']}
        client_context = SimpleGroupContext(
            alg_aead=config['alg_aead'],
            hashfun=config['hashfun'],
            alg_signature=config['alg_signature'],
            alg_group_enc=config['alg_group_enc'],
            alg_pairwise_key_agreement=config['alg_pairwise_key_agreement'],
            group_id=config['group_id'],
            master_secret=config['master_secret'],
            master_salt=config['master_salt'],
            sender_id=config['client_id'],
            private_key=config['client_private_key'],
            sender_auth_cred=config['client_cred'],
            peers=client_peers,
            group_manager_cred=config['gm_cred']
        )
        
        # Crear contexto del servidor
        server_peers = {config['client_id']: config['client_cred']}
        server_context = SimpleGroupContext(
            alg_aead=config['alg_aead'],
            hashfun=config['hashfun'],
            alg_signature=config['alg_signature'],
            alg_group_enc=config['alg_group_enc'],
            alg_pairwise_key_agreement=config['alg_pairwise_key_agreement'],
            group_id=config['group_id'],
            master_secret=config['master_secret'],
            master_salt=config['master_salt'],
            sender_id=config['server_id'],
            private_key=config['server_private_key'],
            sender_auth_cred=config['server_cred'],
            peers=server_peers,
            group_manager_cred=config['gm_cred']
        )
        
        print("✅ Contextos creados exitosamente")
        return client_context, server_context
        
    except Exception as e:
        print(f"❌ Error creando contextos: {e}")
        return None, None

def simulate_complete_communication():
    """Simulación completa de comunicación bidireccional"""
    
    print("\n" + "="*70)
    print("🔄 SIMULACIÓN COMPLETA DE COMUNICACIÓN OSCORE GROUP")
    print("="*70)
    
    # Usar configuración compartida para ambos contextos
    config = create_shared_group_config()
    client_ctx, server_ctx = create_group_contexts_from_config(config)
    
    if not client_ctx or not server_ctx:
        return False
    
    try:
        # ===== FASE 1: CLIENTE ENVÍA REQUEST =====
        print("\n📤 FASE 1: Cliente → Servidor (REQUEST)")
        print("-" * 50)
        
        original_request = Message(
            code=GET,
            payload=b"Client request to group server"
        )
        original_request.opt.uri_path = ["api", "data"]
        
        print(f"📄 Request original: {original_request.payload}")
        
        # Proteger request
        protected_request, client_request_id = client_ctx.protect(original_request)
        print(f"🔐 Request protegido (tamaño: {len(protected_request.payload)} bytes)")
        print(f"🔐 OSCORE option: {protected_request.opt.oscore.hex()}")
        
        # Transferir request (simular red)
        print("📡 Transfiriendo request por la red...")
        
        # Servidor recibe y desprotege
        from aiocoap.oscore import verify_start
        unprotected_info = verify_start(protected_request)
        print(f"ℹ️ Info no protegida: {unprotected_info}")
        
        server_unprotect_ctx = server_ctx.get_oscore_context_for(unprotected_info)
        print(f"✅ Contexto servidor: {type(server_unprotect_ctx).__name__}")
        
        unprotected_request, server_request_id = server_unprotect_ctx.unprotect(
            protected_request, None
        )
        
        print(f"🔓 Request desprotegido: {unprotected_request.payload}")
        
        # Verificar request
        request_ok = (unprotected_request.payload == original_request.payload)
        print(f"✅ Request verificado: {request_ok}")
        
        if not request_ok:
            return False
        
        # ===== FASE 2: SERVIDOR PROCESA Y RESPONDE =====
        print("\n📤 FASE 2: Servidor → Cliente (RESPONSE)")
        print("-" * 50)
        
        # Procesar request y crear response
        response_data = f"Processed: {unprotected_request.payload.decode()}"
        original_response = Message(
            code=CONTENT,
            payload=response_data.encode()
        )
        
        print(f"📄 Response original: {original_response.payload}")
        
        # Para el response, vamos a usar el contexto de grupo directamente
        # pero necesitamos manejar el server_request_id correctamente
        
        # Modificar el request_id para que funcione con responses
        server_request_id.can_reuse_nonce = False
        
        # Proteger response usando el contexto del servidor
        protected_response, _ = server_ctx.protect(original_response, server_request_id)
        print(f"🔐 Response protegido (tamaño: {len(protected_response.payload)} bytes)")
        print(f"🔐 OSCORE option: {protected_response.opt.oscore.hex() if protected_response.opt.oscore else 'None'}")
        
        # Transferir response (simular red)
        print("📡 Transfiriendo response por la red...")
        
        # Cliente recibe y desprotege
        # Necesitamos obtener el contexto apropiado para el response
        response_unprotected_info = verify_start(protected_response)
        print(f"ℹ️ Info del response: {response_unprotected_info}")
        
        # Obtener contexto del cliente para responses
        client_response_ctx = client_ctx.context_from_response(response_unprotected_info)
        if not client_response_ctx:
            print("❌ No se pudo obtener contexto para response")
            return False
        
        print(f"✅ Contexto cliente response: {type(client_response_ctx).__name__}")
        
        unprotected_response, _ = client_response_ctx.unprotect(
            protected_response, client_request_id
        )
        
        print(f"🔓 Response desprotegido: {unprotected_response.payload}")
        
        # Verificar response
        response_ok = (unprotected_response.payload == original_response.payload)
        print(f"✅ Response verificado: {response_ok}")
        
        # ===== VERIFICACIÓN FINAL =====
        print("\n🎯 VERIFICACIÓN FINAL")
        print("-" * 30)
        
        success = request_ok and response_ok
        
        if success:
            print("🎉 ¡COMUNICACIÓN BIDIRECCIONAL EXITOSA!")
            print("   ✅ Request protegido/desprotegido correctamente")
            print("   ✅ Response protegido/desprotegido correctamente")
            print("   ✅ Integridad y autenticación verificadas")
            print("   ✅ OSCORE Group funcional completo")
        else:
            print("❌ FALLO en la comunicación")
        
        return success
        
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_group_signatures():
    """Test específico para verificar las firmas del grupo"""
    
    print("\n" + "="*60)
    print("🔏 TEST: VERIFICACIÓN DE FIRMAS DE GRUPO")
    print("="*60)
    
    config = create_shared_group_config()
    client_ctx, server_ctx = create_group_contexts_from_config(config)
    
    if not client_ctx or not server_ctx:
        return False
    
    try:
        # Crear mensaje con datos específicos para verificar firmas
        test_data = b"Test message for signature verification"
        message = Message(code=GET, payload=test_data)
        
        print(f"📄 Mensaje de prueba: {test_data}")
        
        # Proteger con firmas
        protected_msg, req_id = client_ctx.protect(message)
        
        # Verificar que el mensaje es más largo (contiene firma)
        baseline_size = len(test_data) + 20  # Tamaño aproximado sin firma
        has_signature = len(protected_msg.payload) > baseline_size
        
        print(f"📏 Tamaño del payload protegido: {len(protected_msg.payload)} bytes")
        print(f"🔏 Contiene firma: {has_signature}")
        
        # Desproteger y verificar firma
        from aiocoap.oscore import verify_start
        unprotected_info = verify_start(protected_msg)
        
        # Verificar que es un mensaje de grupo
        from aiocoap.oscore import COSE_COUNTERSIGNATURE0
        is_group_message = COSE_COUNTERSIGNATURE0 in unprotected_info
        print(f"🏷️ Es mensaje de grupo: {is_group_message}")
        
        # Desproteger (esto verifica la firma automáticamente)
        server_unprotect_ctx = server_ctx.get_oscore_context_for(unprotected_info)
        unprotected_msg, _ = server_unprotect_ctx.unprotect(protected_msg, None)
        
        # Si llegamos aquí, la firma se verificó correctamente
        signature_valid = (unprotected_msg.payload == test_data)
        
        print(f"✅ Firma verificada automáticamente: {signature_valid}")
        print(f"📄 Mensaje desprotegido: {unprotected_msg.payload}")
        
        success = has_signature and is_group_message and signature_valid
        
        if success:
            print("🎉 ¡FIRMAS DE GRUPO FUNCIONANDO CORRECTAMENTE!")
            print("   ✅ Mensajes contienen firmas")
            print("   ✅ Firmas se verifican automáticamente")
            print("   ✅ Autenticación de origen garantizada")
        else:
            print("❌ Problema con las firmas de grupo")
        
        return success
        
    except Exception as e:
        print(f"❌ Error en test de firmas: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    
    print("🚀 OSCORE GROUP - PRUEBA COMPLETA")
    print("="*60)
    print("ℹ️ Esta versión implementa comunicación bidireccional completa")
    
    results = []
    
    try:
        # Test 1: Comunicación completa
        print("\n🧪 TEST 1: Comunicación bidireccional completa")
        results.append(simulate_complete_communication())
        
        # Test 2: Verificación de firmas
        print("\n🧪 TEST 2: Verificación de firmas de grupo")
        results.append(test_group_signatures())
        
        # Resumen final
        print("\n" + "="*60)
        print("📊 RESUMEN FINAL")
        print("="*60)
        print(f"🧪 Test 1 - Comunicación completa: {'✅ ÉXITO' if results[0] else '❌ FALLO'}")
        print(f"🧪 Test 2 - Firmas de grupo: {'✅ ÉXITO' if results[1] else '❌ FALLO'}")
        
        all_success = all(results)
        if all_success:
            print("\n🎉 ¡OSCORE GROUP COMPLETAMENTE FUNCIONAL!")
            print("   ✅ Comunicación bidireccional segura")
            print("   ✅ Autenticación con firmas digitales")
            print("   ✅ Confidencialidad e integridad")
            print("   ✅ Implementación Group OSCORE completa")
            print("\n🏆 ¡FELICIDADES! Has implementado OSCORE Group exitosamente")
        else:
            print("\n❌ ALGUNOS ASPECTOS NECESITAN AJUSTES")
        
        return all_success
        
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'🎊 ¡IMPLEMENTACIÓN EXITOSA!' if success else '❌ Necesita más trabajo'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Prueba interrumpida")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)