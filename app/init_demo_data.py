"""
Script de inicialización de datos de demostración
Crea empresa y usuario predeterminados para el sistema demo
"""

from sqlalchemy.orm import Session
from app.database.connection import engine
from app.models.current import Base, Company, SystemUser
from app.models.rag_models import UserRAGConfig
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_demo_data():
    """
    Inicializa los datos de demostración:
    - 1 empresa (Demo Company)
    - 1 usuario de prueba (demo)
    - Configuración RAG por defecto
    """
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    # Crear sesión
    session = Session(engine)

    
    try:
        # Verificar si ya existe la empresa demo
        existing_company = session.query(Company).filter_by(code="0001").first()
        
        if existing_company:
            print("✅ Empresa demo ya existe")
            company = existing_company
        else:
            # Crear empresa demo
            company = Company(
                code="0001",
                name="Demo Company",
                whatsapp_number="+51999999999",
                phone_number="+51999999999",
                email="demo@demo.com",
                is_active=True,
                created_at=datetime.now()
            )
            session.add(company)
            session.commit()
            session.refresh(company)
            print(f"✅ Empresa demo creada: {company.name} (ID: {company.id})")

        
        # Verificar si ya existe el usuario demo
        existing_user = session.query(SystemUser).filter_by(username="demo").first()
        
        if existing_user:
            print("✅ Usuario demo ya existe")
            user = existing_user
        else:
            # Crear usuario demo
            user = SystemUser(
                company_id=company.id,
                username="demo",
                email="demo@demo.com",
                password_hash=pwd_context.hash("demo123"),  # Contraseña: demo123
                first_name="Demo",
                paternal_last_name="User",
                maternal_last_name="Test",
                role="admin",
                is_active=True,
                phone_number="+51999999999",
                created_at=datetime.now(),
                must_change_password=False
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ Usuario demo creado: {user.username} (ID: {user.id})")

        
        # Verificar si ya existe configuración RAG
        existing_config = session.query(UserRAGConfig).filter_by(company_id=company.id).first()
        
        if existing_config:
            print("✅ Configuración RAG ya existe")
        else:
            # Crear configuración RAG por defecto
            rag_config = UserRAGConfig(
                company_id=company.id,
                chunk_size=512,
                chunk_overlap=50,
                top_k=5,
                temperature=0.7,
                model_name="mistral",
                enable_hybrid_search=True,
                enable_rag=True,
                system_prompt="Eres un asistente útil que responde preguntas basándote en los documentos proporcionados.",
                company_description="Empresa de demostración"
            )
            session.add(rag_config)
            session.commit()
            print("✅ Configuración RAG creada")
        
        print("\n" + "="*50)
        print("✅ DATOS DE DEMOSTRACIÓN INICIALIZADOS")
        print("="*50)
        print(f"Empresa: {company.name} (Código: {company.code})")
        print(f"Usuario: {user.username}")
        print(f"Contraseña: demo123")
        print(f"Email: {user.email}")
        print("="*50)
        
        return company, user
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error al inicializar datos: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Inicializando datos de demostración...")
    init_demo_data()
