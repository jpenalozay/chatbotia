"""
Script para limpiar completamente la base de datos
Elimina: conversaciones, mensajes, clientes, documentos RAG
Mantiene: estructura de tablas, empresa demo, usuario demo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database.connection import SessionLocal
from app.models.current import Client, Conversation, Message
from app.models.rag_models import UserDocument
import shutil

def limpiar_base_datos():
    """Limpiar todas las conversaciones y datos relacionados"""
    session = SessionLocal()
    
    try:
        print("🧹 Iniciando limpieza de base de datos...")
        
        # 1. Eliminar mensajes
        mensajes_count = session.query(Message).count()
        session.query(Message).delete()
        print(f"✅ Eliminados {mensajes_count} mensajes")
        
        # 2. Eliminar conversaciones
        conversaciones_count = session.query(Conversation).count()
        session.query(Conversation).delete()
        print(f"✅ Eliminadas {conversaciones_count} conversaciones")
        
        # 3. Eliminar clientes
        clientes_count = session.query(Client).count()
        session.query(Client).delete()
        print(f"✅ Eliminados {clientes_count} clientes")
        
        # 4. Eliminar documentos RAG de BD
        documentos_count = session.query(UserDocument).count()
        session.query(UserDocument).delete()
        print(f"✅ Eliminados {documentos_count} documentos RAG de BD")
        
        # Commit cambios
        session.commit()
        print("\n✅ Base de datos MySQL limpiada correctamente")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error limpiando base de datos: {e}")
    finally:
        session.close()

def limpiar_chromadb():
    """Limpiar base de datos vectorial ChromaDB"""
    try:
        chroma_path = "./chroma_db"
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)
            print(f"✅ ChromaDB eliminado: {chroma_path}")
        else:
            print("ℹ️  ChromaDB no existe")
    except Exception as e:
        print(f"❌ Error limpiando ChromaDB: {e}")

def limpiar_uploads():
    """Limpiar archivos subidos"""
    try:
        uploads_path = "./uploads"
        if os.path.exists(uploads_path):
            # Eliminar todos los archivos pero mantener el directorio
            for filename in os.listdir(uploads_path):
                file_path = os.path.join(uploads_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"✅ Archivos subidos eliminados: {uploads_path}")
        else:
            print("ℹ️  Directorio uploads no existe")
    except Exception as e:
        print(f"❌ Error limpiando uploads: {e}")

def limpiar_cache():
    """Limpiar cache de Python"""
    try:
        import subprocess
        # Limpiar __pycache__ recursivamente
        subprocess.run(
            ["find", ".", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
            shell=True,
            check=False
        )
        print("✅ Cache de Python eliminado")
    except Exception as e:
        print(f"❌ Error limpiando cache: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧹 LIMPIEZA COMPLETA DEL SISTEMA")
    print("=" * 60)
    print()
    
    # Confirmación
    respuesta = input("⚠️  ¿Estás seguro de eliminar TODOS los datos? (sí/no): ")
    if respuesta.lower() != "sí":
        print("❌ Limpieza cancelada")
        sys.exit(0)
    
    print()
    
    # Ejecutar limpieza
    limpiar_base_datos()
    print()
    limpiar_chromadb()
    print()
    limpiar_uploads()
    print()
    limpiar_cache()
    
    print()
    print("=" * 60)
    print("✅ LIMPIEZA COMPLETA FINALIZADA")
    print("=" * 60)
    print()
    print("📝 Notas:")
    print("  - Estructura de BD mantenida")
    print("  - Empresa demo mantenida")
    print("  - Usuario demo mantenido")
    print("  - ChromaDB se recreará al iniciar el servidor")
    print()
    print("🚀 Reinicia el servidor para aplicar cambios:")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 9090")
