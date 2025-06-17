import asyncio
import aiocoap
from aiocoap import Context, Message, Code
from aiocoap.oscore import SimpleGroupManager, GroupOSCORE
from aiocoap.credentials import CredentialsMap
import secrets
import json
import time
from datetime import datetime
import logging

# Configurar logging para ver detalles OSCORE
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OSCOREGroupNode:
    """Nodo CoAP con soporte OSCORE Group"""
    
    def __init__(self, node_id, listen_port=None, group_config=None):
        self.node_id = node_id
        self.listen_port = listen_port or (5683 + hash(node_id) % 100)
        self.context = None
        self.group_config = group_config
        self.received_messages = []
        self.message_count = 0
        
    async def initialize(self):
        """Inicializar contexto CoAP con OSCORE"""
        print(f"🚀 Inicializando {self.node_id} en puerto {self.listen_port}")
        
        # Crear contexto base
        self.context = await Context.create_server_context(
            bind=('127.0.0.1', self.listen_port)
        )
        
        # Configurar OSCORE Group si se proporciona
        if self.group_config:
            await self._setup_oscore_group()
        
        # Registrar recursos CoAP
        await self._register_resources()
        
        print(f"✅ {self.node_id} listo en coap://127.0.0.1:{self.listen_port}")
    
    async def _setup_oscore_group(self):
        """Configurar OSCORE Group"""
        try:
            # Crear manager de grupo OSCORE
            group_manager = SimpleGroupManager()
            
            # Configurar credenciales OSCORE
            master_secret = bytes.fromhex(self.group_config['master_secret'])
            master_salt = bytes.fromhex(self.group_config['master_salt'])
            group_id = self.group_config['group_id'].encode()
            sender_id = self.node_id.encode()
            
            # Configurar contexto OSCORE
            oscore_context = GroupOSCORE(
                master_secret=master_secret,
                master_salt=master_salt,
                group_id=group_id,
                sender_id=sender_id,
                recipient_id=sender_id  # Para pruebas
            )
            
            # Aplicar OSCORE al contexto
            credentials = CredentialsMap()
            credentials[f"coap://127.0.0.1/*"] = oscore_context
            self.context.client_credentials = credentials
            
            print(f"🔐 OSCORE Group configurado para {self.node_id}")
            
        except Exception as e:
            print(f"⚠️ Error configurando OSCORE para {self.node_id}: {e}")
            print("   Continuando sin OSCORE...")
    
    async def _register_resources(self):
        """Registrar recursos CoAP"""
        # Recurso principal del nodo
        self.context.serversite.add_resource(
            ['node', self.node_id],
            NodeResource(self)
        )
        
        # Recurso para datos del sensor (si es sensor)
        if 'sensor' in self.node_id:
            self.context.serversite.add_resource(
                ['sensor', 'data'],
                SensorResource(self)
            )
        
        # Recurso para comandos (si es actuador)
        if 'actuador' in self.node_id:
            self.context.serversite.add_resource(
                ['actuator', 'command'],
                ActuatorResource(self)
            )
    
    async def send_multicast_message(self, payload, group_address="224.0.1.187"):
        """Enviar mensaje multicast OSCORE"""
        try:
            multicast_uri = f"coap://[{group_address}]:5683/group/message"
            
            message = Message(
                code=Code.POST,
                uri=multicast_uri,
                payload=json.dumps({
                    'sender': self.node_id,
                    'data': payload,
                    'timestamp': time.time(),
                    'message_id': self.message_count
                }).encode()
            )
            
            self.message_count += 1
            
            print(f"📤 {self.node_id} enviando multicast: {payload[:50]}...")
            
            # Enviar con OSCORE si está configurado
            response = await self.context.request(message)
            print(f"✅ Multicast enviado, respuesta: {response.code}")
            
        except Exception as e:
            print(f"❌ Error enviando multicast desde {self.node_id}: {e}")
    
    async def send_unicast_message(self, target_port, payload):
        """Enviar mensaje unicast a otro nodo"""
        try:
            target_uri = f"coap://127.0.0.1:{target_port}/node/message"
            
            message = Message(
                code=Code.POST,
                uri=target_uri,
                payload=json.dumps({
                    'sender': self.node_id,
                    'data': payload,
                    'timestamp': time.time()
                }).encode()
            )
            
            print(f"📤 {self.node_id} -> puerto {target_port}: {payload[:30]}...")
            
            response = await self.context.request(message)
            print(f"✅ Respuesta recibida: {response.code}")
            
            return response
            
        except Exception as e:
            print(f"❌ Error enviando unicast: {e}")
    
    async def shutdown(self):
        """Cerrar el nodo"""
        if self.context:
            await self.context.shutdown()
        print(f"🛑 {self.node_id} desconectado")

class NodeResource(aiocoap.resource.Resource):
    """Recurso CoAP principal del nodo"""
    
    def __init__(self, node):
        super().__init__()
        self.node = node
    
    async def render_get(self, request):
        """Manejar peticiones GET"""
        info = {
            'node_id': self.node.node_id,
            'port': self.node.listen_port,
            'messages_received': len(self.node.received_messages),
            'status': 'active',
            'timestamp': time.time()
        }
        
        return Message(
            code=Code.CONTENT,
            payload=json.dumps(info).encode()
        )
    
    async def render_post(self, request):
        """Manejar mensajes entrantes"""
        try:
            payload = json.loads(request.payload.decode())
            
            self.node.received_messages.append({
                'from': payload.get('sender', 'unknown'),
                'data': payload.get('data'),
                'received_at': time.time(),
                'oscore_protected': hasattr(request, 'oscore_context')
            })
            
            print(f"📥 {self.node.node_id} recibió de {payload.get('sender')}")
            
            return Message(code=Code.CHANGED)
            
        except Exception as e:
            print(f"❌ Error procesando mensaje en {self.node.node_id}: {e}")
            return Message(code=Code.BAD_REQUEST)

class SensorResource(aiocoap.resource.Resource):
    """Recurso específico para sensores"""
    
    def __init__(self, node):
        super().__init__()
        self.node = node
    
    async def render_get(self, request):
        """Devolver datos simulados del sensor"""
        sensor_data = {
            'sensor_id': self.node.node_id,
            'type': 'temperature' if 'temp' in self.node.node_id else 'humidity',
            'value': 20 + (hash(str(time.time())) % 15),  # Valor simulado
            'unit': 'celsius' if 'temp' in self.node.node_id else 'percent',
            'timestamp': time.time(),
            'location': 'lab_room_1'
        }
        
        return Message(
            code=Code.CONTENT,
            payload=json.dumps(sensor_data).encode()
        )

class ActuatorResource(aiocoap.resource.Resource):
    """Recurso específico para actuadores"""
    
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.state = {'active': False, 'speed': 0}
    
    async def render_post(self, request):
        """Ejecutar comando en el actuador"""
        try:
            command = json.loads(request.payload.decode())
            
            if command.get('action') == 'start':
                self.state['active'] = True
                self.state['speed'] = command.get('speed', 50)
                result = f"Actuador iniciado a velocidad {self.state['speed']}"
            
            elif command.get('action') == 'stop':
                self.state['active'] = False
                self.state['speed'] = 0
                result = "Actuador detenido"
            
            else:
                result = f"Estado actual: {self.state}"
            
            print(f"🔧 {self.node.node_id}: {result}")
            
            return Message(
                code=Code.CHANGED,
                payload=json.dumps({
                    'result': result,
                    'state': self.state
                }).encode()
            )
            
        except Exception as e:
            return Message(code=Code.BAD_REQUEST)

class OSCOREGroupSimulator:
    """Simulador principal de red OSCORE Group con CoAP"""
    
    def __init__(self):
        self.nodes = {}
        self.group_config = self._generate_group_config()
        
    def _generate_group_config(self):
        """Generar configuración del grupo OSCORE"""
        return {
            'group_id': 'iot_sensors_group',
            'master_secret': secrets.token_bytes(32).hex(),
            'master_salt': secrets.token_bytes(16).hex(),
            'algorithm': 'AES-CCM-16-64-128'
        }
    
    async def create_network(self):
        """Crear red de nodos CoAP"""
        print("🌐 Creando red OSCORE Group con aiocoap...")
        
        # Definir nodos con puertos específicos
        node_configs = [
            ('sensor_temperatura', 5683),
            ('sensor_humedad', 5684),
            ('actuador_ventilador', 5685),
            ('gateway_principal', 5686),
            ('cliente_monitor', 5687)
        ]
        
        # Crear e inicializar nodos
        for node_id, port in node_configs:
            node = OSCOREGroupNode(node_id, port, self.group_config)
            await node.initialize()
            self.nodes[node_id] = node
            
            # Pequeña pausa entre inicializaciones
            await asyncio.sleep(0.3)
        
        print(f"✅ {len(self.nodes)} nodos CoAP creados")
    
    async def run_communication_scenarios(self):
        """Ejecutar escenarios de comunicación"""
        print("\n📡 Ejecutando escenarios de comunicación CoAP/OSCORE...")
        
        # Esperar que todos los nodos estén listos
        await asyncio.sleep(2)
        
        scenarios = [
            {
                'sender': 'sensor_temperatura',
                'type': 'multicast',
                'payload': {'type': 'temperature_reading', 'value': 24.8, 'alert': False}
            },
            {
                'sender': 'sensor_humedad', 
                'type': 'multicast',
                'payload': {'type': 'humidity_reading', 'value': 67.3, 'alert': False}
            },
            {
                'sender': 'gateway_principal',
                'type': 'unicast',
                'target': 'actuador_ventilador',
                'payload': {'command': 'start', 'speed': 75, 'duration': 300}
            },
            {
                'sender': 'cliente_monitor',
                'type': 'discovery',
                'payload': {'action': 'discover_sensors', 'request_id': 'req_001'}
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🎬 Escenario {i}: {scenario['sender']} - {scenario['type']}")
            
            sender = self.nodes[scenario['sender']]
            
            if scenario['type'] == 'multicast':
                await sender.send_multicast_message(scenario['payload'])
            
            elif scenario['type'] == 'unicast':
                target_node = self.nodes[scenario['target']]
                await sender.send_unicast_message(target_node.listen_port, scenario['payload'])
            
            elif scenario['type'] == 'discovery':
                # Enviar a todos los sensores
                for node_id, node in self.nodes.items():
                    if 'sensor' in node_id:
                        await sender.send_unicast_message(node.listen_port, scenario['payload'])
            
            # Pausa para observar tráfico
            await asyncio.sleep(3)
        
        print("\n✅ Todos los escenarios ejecutados")
    
    async def generate_continuous_traffic(self, duration=60):
        """Generar tráfico continuo para análisis"""
        print(f"\n🔄 Generando tráfico CoAP continuo por {duration}s...")
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Seleccionar nodo aleatorio
            sender_id = secrets.choice(list(self.nodes.keys()))
            sender = self.nodes[sender_id]
            
            # Datos simulados
            data = {
                'node': sender_id,
                'value': secrets.randbelow(100),
                'timestamp': time.time(),
                'type': 'periodic_update'
            }
            
            # Alternar entre multicast y unicast
            if secrets.randbelow(2):
                await sender.send_multicast_message(data)
            else:
                target_id = secrets.choice([n for n in self.nodes.keys() if n != sender_id])
                target_port = self.nodes[target_id].listen_port
                await sender.send_unicast_message(target_port, data)
            
            await asyncio.sleep(secrets.randbelow(4) + 1)
        
        print("🏁 Tráfico continuo finalizado")
    
    def show_network_status(self):
        """Mostrar estado de la red"""
        print(f"\n📊 Estado de la red CoAP/OSCORE:")
        print(f"  • Grupo ID: {self.group_config['group_id']}")
        print(f"  • Algoritmo: {self.group_config['algorithm']}")
        print(f"  • Nodos activos: {len(self.nodes)}")
        
        for node_id, node in self.nodes.items():
            msg_count = len(node.received_messages)
            print(f"    - {node_id}: puerto {node.listen_port}, {msg_count} msgs recibidos")
    
    async def cleanup(self):
        """Limpiar recursos"""
        print("\n🧹 Cerrando nodos...")
        for node in self.nodes.values():
            await node.shutdown()
        print("✅ Red cerrada correctamente")

async def main():
    """Función principal"""
    print("=" * 70)
    print("🌐 SIMULADOR OSCORE GROUP con aiocoap - TRÁFICO CoAP REAL")
    print("=" * 70)
    
    simulator = OSCOREGroupSimulator()
    
    try:
        # Crear red
        await simulator.create_network()
        
        # Instrucciones para Wireshark
        print(f"\n🔍 CONFIGURACIÓN WIRESHARK:")
        print(f"   1. Captura interfaz: Loopback (127.0.0.1)")
        print(f"   2. Filtros CoAP:")
        print(f"      • Básico: coap")
        print(f"      • Puertos: udp.port >= 5683 and udp.port <= 5687")
        print(f"      • OSCORE: coap.oscore")
        print(f"   3. ¡Wireshark reconocerá automáticamente CoAP y OSCORE!")
        
        input(f"\n⏸️  Presiona ENTER cuando Wireshark esté capturando...")
        
        # Ejecutar comunicación
        await simulator.run_communication_scenarios()
        
        # Mostrar estado
        simulator.show_network_status()
        
        # Opción de tráfico continuo
        print(f"\n❓ ¿Generar tráfico continuo para análisis extendido?")
        choice = input("   (s/n): ").lower().strip()
        
        if choice == 's':
            duration = input("⏱️  Duración en segundos (default 30): ").strip()
            duration = int(duration) if duration.isdigit() else 30
            await simulator.generate_continuous_traffic(duration)
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Simulación interrumpida")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import aiocoap
        print("✅ aiocoap encontrado")
    except ImportError:
        print("❌ Instala aiocoap: pip install aiocoap[all]")
        exit(1)
    
    # Ejecutar simulación
    asyncio.run(main())