# IoT Communication Security Analysis

**Comparativa de Protocolos Seguros en IoT: Impacto de TLS, DTLS y OSCORE sobre MQTT y CoAP**


## Descripción

Este repositorio contiene la implementación experimental del TFM que analiza comparativamente los protocolos de comunicación IoT MQTT y CoAP junto con sus mecanismos de seguridad: TLS, DTLS, OSCORE y Group OSCORE.

## Objetivos Principales

- Evaluar el rendimiento de protocolos IoT con y sin seguridad  
- Comparar mecanismos de protección criptográfica  
- Medir impacto en latencia, CPU y memoria  
- Analizar vulnerabilidades específicas por protocolo  
- Implementar vectores de ataque para validación  
- Proporcionar guías de selección para implementaciones IoT  

## Estructura del Proyecto

```
iot-comm-sec/
├── coap/
│   ├── basic/
│   │   ├── client_coap.py
│   │   └── server_coap.py
│   ├── dtls/
│   │   ├── client_coap_dtls.py
│   │   └── server_coap_dtls.py
│   ├── oscore/
│   │   ├── client_coap_oscore.py
│   │   ├── server_coap_oscore.py
│   │   ├── client.json
│   │   ├── server.json
│   │   ├── oscore_context.json
│   │   └── oscore_group_credentials.json
│   └── group-oscore/
│       ├── oscore_group_launcher.py
│       └── oscore_group_network_fixed.py
└── mqtt/
    ├── client_mqtt.py
    ├── client_mqtt_tls.py
    ├── mosquito_tls.conf
    └── certs/
        ├── ca.crt
        ├── server.crt
        ├── server.key
        ├── client.crt
        └── client.key
```

## Instalación y Configuración


### Configuración del Entorno

```bash
git clone https://github.com/ilmareca/iot-comm-sec.git
cd iot-comm-sec
python -m venv venv
source venv/bin/activate  # En Linux/macOS
venv\Scripts\activate     # En Windows
pip install -r requirements.txt
```

## Uso y Ejecución

### CoAP - Comunicación Básica

```bash
cd coap/basic
python server_coap.py  # En una terminal
python client_coap.py  # En otra terminal
```

### CoAP - Con DTLS

```bash
cd coap/dtls
python server_coap_dtls.py
python client_coap_dtls.py
```

### CoAP - Con OSCORE

```bash
cd coap/oscore
python server_coap_oscore.py
python client_coap_oscore.py
```

### CoAP - Group OSCORE

```bash
cd coap/group-oscore
python oscore_group_launcher.py
# o bien
```

### MQTT - Básico

```bash
cd mqtt
python client_mqtt.py
```

### MQTT - Con TLS

```bash
mosquitto -c mosquito_tls.conf  # Terminal 1
python client_mqtt_tls.py       # Terminal 2
```

## Experimentos y Evaluación

### Protocolos Implementados

| Protocolo        | Seguridad   | Estado       | Descripción                    |
|------------------|-------------|--------------|--------------------------------|
| CoAP Basic       | Ninguna     | Implementado | CoAP sin protección            |
| CoAP + DTLS      | DTLS 1.2    | Implementado | CoAP con cifrado DTLS          |
| CoAP + OSCORE    | OSCORE      | Implementado | Seguridad end-to-end           |
| Group OSCORE     | Multicast   | Implementado | Comunicación grupal            |
| MQTT Basic       | Ninguna     | Implementado | MQTT sin protección            |
| MQTT + TLS       | TLS 1.3     | Implementado | MQTT con cifrado TLS           |

### Métricas Evaluadas

- Latencia: Tiempo de respuesta extremo a extremo  
- CPU: Uso de procesador durante comunicación  
- Memoria: Consumo de RAM  

