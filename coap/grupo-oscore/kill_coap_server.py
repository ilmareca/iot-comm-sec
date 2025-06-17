#!/usr/bin/env python3
"""
Script para matar procesos que usan puertos CoAP
"""

import psutil
import sys

def kill_processes_on_port(port):
    """Matar procesos que usan un puerto específico"""
    
    killed_count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            # Verificar conexiones del proceso
            for conn in proc.info['connections'] or []:
                if conn.laddr.port == port:
                    print(f"🔫 Matando proceso {proc.info['name']} (PID: {proc.info['pid']}) en puerto {port}")
                    proc.kill()
                    killed_count += 1
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count

def main():
    ports_to_check = [5683, 5684, 5685]
    
    print("🔍 Buscando procesos CoAP...")
    
    total_killed = 0
    for port in ports_to_check:
        killed = kill_processes_on_port(port)
        total_killed += killed
        if killed > 0:
            print(f"   ✅ Puerto {port}: {killed} procesos eliminados")
        else:
            print(f"   ✅ Puerto {port}: libre")
    
    if total_killed > 0:
        print(f"\n🎯 Total eliminados: {total_killed} procesos")
        print("✅ Puertos CoAP liberados")
    else:
        print("\n✅ No hay procesos CoAP ejecutándose")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada")
    except Exception as e:
        print(f"\n💥 Error: {e}")