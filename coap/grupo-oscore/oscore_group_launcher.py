#!/usr/bin/env python3
"""
Script de lanzamiento para OSCORE Group
Facilita ejecutar servidor y cliente
"""

import subprocess
import sys
import time
import threading

def run_server():
    """Ejecutar servidor en hilo separado"""
    print("🖥️ Iniciando servidor OSCORE Group...")
    try:
        subprocess.run([sys.executable, "oscore_group_network_fixed.py", "server"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en servidor: {e}")
    except KeyboardInterrupt:
        print("🛑 Servidor detenido")

def run_client():
    """Ejecutar cliente después de una pausa"""
    print("⏳ Esperando 3 segundos para que el servidor se inicie...")
    time.sleep(3)
    
    print("👤 Iniciando cliente OSCORE Group...")
    try:
        subprocess.run([sys.executable, "oscore_group_network_fixed.py", "client"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en cliente: {e}")
    except KeyboardInterrupt:
        print("🛑 Cliente detenido")

def main():
    """Función principal"""
    
    print("🚀 LANZADOR OSCORE GROUP")
    print("="*50)
    print("1. Servidor y Cliente automático")
    print("2. Solo Servidor")
    print("3. Solo Cliente")
    print("4. Instrucciones Wireshark")
    print("="*50)
    
    choice = input("Selecciona una opción (1-4): ").strip()
    
    if choice == "1":
        print("\n🔄 Iniciando servidor y cliente automáticamente...")
        print("📡 El tráfico será visible en Wireshark en puerto 5683")
        print("🛑 Presiona Ctrl+C para detener")
        
        # Iniciar servidor en hilo separado
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Ejecutar cliente en el hilo principal
        try:
            run_client()
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo todo...")
        
    elif choice == "2":
        print("\n🖥️ Iniciando solo servidor...")
        print("📡 Servidor escuchando en puerto 5683")
        print("🛑 Presiona Ctrl+C para detener")
        run_server()
        
    elif choice == "3":
        print("\n👤 Iniciando solo cliente...")
        print("⚠️ Asegúrate de que el servidor esté ejecutándose")
        run_client()
        
    elif choice == "4":
        print("\n📊 INSTRUCCIONES PARA WIRESHARK")
        print("="*50)
        print("1. Abre Wireshark")
        print("2. Selecciona la interfaz 'Loopback' o 'lo0'")
        print("3. Aplica el filtro: udp.port == 5683")
        print("4. Inicia la captura")
        print("5. Ejecuta el servidor y cliente")
        print("6. Verás paquetes CoAP con OSCORE")
        print("\n🔍 QUE BUSCAR EN WIRESHARK:")
        print("- Protocolo: CoAP")
        print("- Puerto: 5683")
        print("- Opción OSCORE en los paquetes")
        print("- Payload cifrado en lugar de texto plano")
        print("- Tamaños de paquete más grandes (por las firmas)")
        print("="*50)
        
    else:
        print("❌ Opción inválida")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Programa interrumpido")
    except Exception as e:
        print(f"\n💥 Error: {e}")