#!/usr/bin/env python3
"""
Script para verificar qué clases OSCORE están disponibles en aiocoap
"""

import sys

def check_aiocoap_oscore():
    try:
        import aiocoap
        #print(f"✅ aiocoap versión: {aiocoap.__version__}")
        
        # Verificar módulo OSCORE
        try:
            import aiocoap.oscore
            print("✅ Módulo aiocoap.oscore importado correctamente")
            
            # Listar clases disponibles
            oscore_classes = [attr for attr in dir(aiocoap.oscore) 
                            if not attr.startswith('_') and attr[0].isupper()]
            print(f"📋 Clases OSCORE disponibles: {oscore_classes}")
            
            # Verificar clases específicas
            classes_to_check = [
                'SimpleGroupManager',
                'SecurityContext', 
                'GroupContext',
                'FilesystemSecurityContext',
                'CanUnprotect',
                'CanProtect'
            ]
            
            for class_name in classes_to_check:
                if hasattr(aiocoap.oscore, class_name):
                    print(f"✅ {class_name} - Disponible")
                else:
                    print(f"❌ {class_name} - No disponible")
                    
        except ImportError as e:
            print(f"❌ Error importando aiocoap.oscore: {e}")
            
        # Verificar credenciales
        try:
            from aiocoap.credentials import CredentialsMap
            print("✅ CredentialsMap disponible")
        except ImportError:
            print("❌ CredentialsMap no disponible")
            
    except ImportError as e:
        print(f"❌ Error importando aiocoap: {e}")

def check_dependencies():
    """Verificar dependencias adicionales"""
    dependencies = [
        ('cryptography', 'Criptografía para OSCORE'),
        ('cbor2', 'CBOR encoding/decoding'),
        ('hkdf', 'HKDF key derivation')
    ]
    
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (No instalado)")

if __name__ == "__main__":
    check_aiocoap_oscore()
    print("\n" + "="*50)
    check_dependencies()