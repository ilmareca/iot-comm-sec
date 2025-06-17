#!/usr/bin/env python3
"""
OSCORE Group Benchmark - Estadísticas de rendimiento completas
Mide latencia, CPU, memoria y I/O para requests OSCORE Group
"""

import asyncio
import time
import statistics
import psutil
import tracemalloc
import logging
import sys
import argparse
import json
import os
import secrets
from aiocoap import *
from aiocoap.resource import Site, Resource
from aiocoap.oscore import SimpleGroupContext, A128GCM, Ed25519, hashfunctions
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper
from aiocoap.credentials import CredentialsMap

# Configurar logging (menos verboso para benchmark)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Configuración
CREDENTIALS_FILE = "oscore_group_credentials.json"
GROUP_CONFIG = {
    'group_id': b"grp1",
    'master_secret': bytes.fromhex("425a524d5a32f7d0d386603359fa3832"),
    'master_salt': bytes.fromhex("1b0b57f74ef4099c"),
    'client_id': b"C1",
    'server_id': b"S1"
}

# ==================== ESTADÍSTICAS ====================

class BenchmarkStats:
    """Clase para recopilar estadísticas de benchmark"""
    
    def __init__(self):
        self.latencies = []
        self.start_time = None
        self.end_time = None
        self.process = psutil.Process()
        self.start_cpu_times = None
        self.start_io_counters = None
        self.start_memory_info = None
        self.peak_memory = 0
        
    def start_monitoring(self):
        """Iniciar monitoreo de recursos"""
        # Memoria
        tracemalloc.start()
        
        # CPU e I/O
        self.start_cpu_times = self.process.cpu_times()
        try:
            self.start_io_counters = self.process.io_counters()
        except AttributeError:
            self.start_io_counters = None  # No disponible en todos los sistemas
        
        self.start_memory_info = self.process.memory_info()
        self.start_time = time.time()
        
    def record_latency(self, latency_ms):
        """Registrar latencia de un request"""
        self.latencies.append(latency_ms)
        
        # Actualizar memoria pico
        current_memory = self.process.memory_info().rss / 1024  # KB
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
    
    def stop_monitoring(self):
        """Detener monitoreo y calcular estadísticas"""
        self.end_time = time.time()
        
    def get_stats(self):
        """Obtener estadísticas completas"""
        if not self.latencies:
            return None
            
        # CPU
        end_cpu_times = self.process.cpu_times()
        cpu_user = end_cpu_times.user - self.start_cpu_times.user
        cpu_system = end_cpu_times.system - self.start_cpu_times.system
        
        # I/O
        disk_reads = 0
        disk_writes = 0
        if self.start_io_counters:
            try:
                end_io_counters = self.process.io_counters()
                disk_reads = end_io_counters.read_count - self.start_io_counters.read_count
                disk_writes = end_io_counters.write_count - self.start_io_counters.write_count
            except:
                pass
        
        # Memoria
        end_memory_info = self.process.memory_info()
        current_memory_kb = end_memory_info.rss / 1024
        
        # Memoria de Python (tracemalloc)
        try:
            python_memory_kb = tracemalloc.get_traced_memory()[1] / 1024
            tracemalloc.stop()
        except:
            python_memory_kb = 0
        
        return {
            'requests': len(self.latencies),
            'latency_mean': statistics.mean(self.latencies),
            'latency_stdev': statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0,
            'cpu_user': cpu_user,
            'cpu_system': cpu_system,
            'disk_reads': disk_reads,
            'disk_writes': disk_writes,
            'python_memory_kb': python_memory_kb,
            'rss_memory_kb': current_memory_kb,
            'total_time': self.end_time - self.start_time
        }

# ==================== CREDENCIALES ====================

def load_or_create_credentials():
    """Cargar credenciales o crearlas si no existen"""
    
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Generar credenciales
    alg_signature = Ed25519()
    gm_private_key, gm_cred = alg_signature.generate_with_ccs()
    client_private_key, client_cred = alg_signature.generate_with_ccs()
    server_private_key, server_cred = alg_signature.generate_with_ccs()
    
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
    
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    return credentials

# ==================== CONTEXTO CORREGIDO ====================

class BenchmarkGroupContext(SimpleGroupContext):
    """Contexto optimizado para benchmark"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.echo_recovery = secrets.token_bytes(8)
        
        # Inicializar replay windows
        for peer_id in self.peers:
            if peer_id in self.recipient_replay_windows:
                self.recipient_replay_windows[peer_id].initialize_empty()
    
    def pairwise_for(self, recipient_id):
        """Usar Group mode para evitar problemas pairwise"""
        return self

def create_benchmark_context(is_client=True):
    """Crear contexto optimizado para benchmark"""
    
    creds = load_or_create_credentials()
    
    # Algoritmos
    alg_aead = A128GCM()
    alg_signature = Ed25519()
    alg_group_enc = A128GCM()
    alg_pairwise_key_agreement = None
    hashfun = hashfunctions["sha256"]
    
    # Credenciales
    gm_private_key = bytes.fromhex(creds['group_manager']['private_key'])
    gm_cred = bytes.fromhex(creds['group_manager']['credential'])
    
    if is_client:
        sender_id = GROUP_CONFIG['client_id']
        private_key = bytes.fromhex(creds['client']['private_key'])
        sender_cred = bytes.fromhex(creds['client']['credential'])
        peers = {GROUP_CONFIG['server_id']: bytes.fromhex(creds['server']['credential'])}
    else:
        sender_id = GROUP_CONFIG['server_id']
        private_key = bytes.fromhex(creds['server']['private_key'])
        sender_cred = bytes.fromhex(creds['server']['credential'])
        peers = {GROUP_CONFIG['client_id']: bytes.fromhex(creds['client']['credential'])}
    
    return BenchmarkGroupContext(
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

# ==================== SERVIDOR ====================

class HolaResource(Resource):
    """Recurso /hola optimizado para benchmark"""
    
    def __init__(self):
        super().__init__()
        self.request_count = 0
    
    async def render_get(self, request):
        self.request_count += 1
        return Message(
            payload=b"Hola desde el servidor CoAP",
            code=CONTENT
        )

async def run_benchmark_server(port=5683):
    """Servidor optimizado para benchmark"""
    
    print(f"🖥️ Iniciando servidor benchmark en puerto {port}...")
    
    # Crear contexto
    server_context = create_benchmark_context(is_client=False)
    server_credentials = CredentialsMap()
    server_credentials[":"] = server_context
    
    # Sitio con recurso /hola
    root = Site()
    hola_resource = HolaResource()
    root.add_resource(['hola'], hola_resource)
    
    # Envolver con OSCORE
    wrapped_site = OscoreSiteWrapper(root, server_credentials)
    
    # Crear servidor
    context = await Context.create_server_context(
        bind=('localhost', port),
        site=wrapped_site
    )
    
    print(f"✅ Servidor benchmark listo en puerto {port}")
    return context, hola_resource

# ==================== CLIENTE BENCHMARK ====================

async def run_benchmark_client(num_requests=100, server_host='localhost', server_port=5683):
    """Cliente que ejecuta benchmark"""
    
    print(f"👤 Iniciando benchmark con {num_requests} requests...")
    
    # Crear contexto
    client_context = create_benchmark_context(is_client=True)
    context = await Context.create_client_context()
    
    # Estadísticas
    stats = BenchmarkStats()
    stats.start_monitoring()
    
    successful_requests = 0
    failed_requests = 0
    
    try:
        # Warmup (no contar en estadísticas)
        print("🔥 Warming up...")
        for _ in range(5):
            try:
                original_request = Message(code=GET, payload=b"")
                original_request.opt.uri_path = ["hola"]
                protected_request, _ = client_context.protect(original_request)
                protected_request.set_request_uri(f"coap://{server_host}:{server_port}/")
                await context.request(protected_request).response
            except:
                pass
        
        print(f"📊 Ejecutando {num_requests} requests...")
        
        # Benchmark real
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                # Crear request
                original_request = Message(code=GET, payload=b"")
                original_request.opt.uri_path = ["hola"]
                
                # Proteger con OSCORE Group
                protected_request, _ = client_context.protect(original_request)
                protected_request.set_request_uri(f"coap://{server_host}:{server_port}/")
                
                # Enviar request
                response = await context.request(protected_request).response
                
                # Medir latencia
                latency_ms = (time.time() - start_time) * 1000
                stats.record_latency(latency_ms)
                
                if response.code.is_successful():
                    successful_requests += 1
                else:
                    failed_requests += 1
                    
            except Exception as e:
                failed_requests += 1
                # Registrar latencia incluso si falla (para estadísticas completas)
                latency_ms = (time.time() - start_time) * 1000
                stats.record_latency(latency_ms)
            
            # Progreso cada 10 requests
            if (i + 1) % 10 == 0:
                print(f"   Completados: {i + 1}/{num_requests}")
        
        stats.stop_monitoring()
        
        # Mostrar resultados
        show_results(stats.get_stats(), successful_requests, failed_requests)
        
    finally:
        await context.shutdown()

def show_results(stats, successful, failed):
    """Mostrar resultados del benchmark"""
    
    if not stats:
        print("❌ No hay estadísticas disponibles")
        return
    
    print("\n" + "="*50)
    print("📊 RESULTADOS DEL BENCHMARK OSCORE GROUP")
    print("="*50)
    print(f"Número de solicitudes: {stats['requests']}")
    print(f"Solicitudes exitosas: {successful}")
    print(f"Solicitudes fallidas: {failed}")
    print(f"Latencia media: {stats['latency_mean']:.2f} ms")
    print(f"Desviación estándar: {stats['latency_stdev']:.2f} ms")
    print(f"CPU modo usuario: {stats['cpu_user']:.2f} s")
    print(f"CPU modo sistema: {stats['cpu_system']:.2f} s")
    print(f"Lecturas de disco: {stats['disk_reads']}")
    print(f"Escrituras de disco: {stats['disk_writes']}")
    print(f"Memoria pico usada (Python): {stats['python_memory_kb']:.2f} KB")
    print(f"Memoria residente total (RSS): {stats['rss_memory_kb']:.2f} KB")
    print(f"Tiempo total: {stats['total_time']:.2f} s")
    print(f"Throughput: {stats['requests']/stats['total_time']:.2f} requests/segundo")
    print("="*50)
    
    # Análisis adicional
    if stats['latency_mean'] > 100:
        print("⚠️ Latencia alta detectada (>100ms)")
    if failed > 0:
        print(f"⚠️ {failed} requests fallaron ({failed/stats['requests']*100:.1f}%)")
    
    success_rate = successful / stats['requests'] * 100
    print(f"✅ Tasa de éxito: {success_rate:.1f}%")

# ==================== DEMO COMPLETO ====================

async def run_full_benchmark_demo(num_requests=100):
    """Demo completo con servidor y cliente"""
    
    print("🚀 DEMO BENCHMARK OSCORE GROUP COMPLETO")
    print("="*60)
    
    server_context = None
    try:
        # Iniciar servidor
        server_context, hola_resource = await run_benchmark_server()
        
        # Esperar a que el servidor se estabilice
        await asyncio.sleep(1)
        
        # Ejecutar benchmark
        await run_benchmark_client(num_requests)
        
        # Estadísticas del servidor
        print(f"\n📈 Estadísticas del servidor:")
        print(f"   Requests procesados: {hola_resource.request_count}")
        
    except Exception as e:
        print(f"❌ Error en benchmark: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if server_context:
            await server_context.shutdown()

# ==================== MAIN ====================

async def main():
    """Función principal"""
    
    parser = argparse.ArgumentParser(description='OSCORE Group Benchmark')
    parser.add_argument('mode', choices=['server', 'client', 'demo'], 
                       help='Modo: server, client, demo')
    parser.add_argument('--requests', '-n', type=int, default=100, 
                       help='Número de requests (default: 100)')
    parser.add_argument('--port', type=int, default=5683, 
                       help='Puerto del servidor')
    parser.add_argument('--host', default='localhost', 
                       help='Host del servidor')
    
    args = parser.parse_args()
    
    if args.mode == 'demo':
        await run_full_benchmark_demo(args.requests)
    elif args.mode == 'server':
        print("🖥️ Modo: SERVIDOR BENCHMARK")
        context, _ = await run_benchmark_server(args.port)
        try:
            await asyncio.Future()  # Ejecutar para siempre
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servidor...")
        finally:
            await context.shutdown()
    else:
        print("👤 Modo: CLIENTE BENCHMARK")
        await run_benchmark_client(args.requests, args.host, args.port)

if __name__ == "__main__":
    print("🚀 OSCORE Group Benchmark - Estadísticas de Rendimiento")
    print("="*60)
    print("📊 Mide latencia, CPU, memoria y I/O para OSCORE Group")
    print("🎯 Recurso: GET /hola → 'Hola desde el servidor CoAP'")
    print("="*60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Benchmark interrumpido")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)