"""
Helpers RAG adaptados para modelo híbrido (Company/SystemUser/Client)
Soporta tanto el modelo nuevo como el legacy (filtrando en SystemUser)
"""

from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import logging
import os

logger = logging.getLogger(__name__)

def get_admin_for_client(session: Session, client_phone: str) -> Optional[Dict[str, Any]]:
    """
    Obtener información del admin de la empresa del cliente
    
    Returns:
        dict con admin_id, company_id, is_new_model
        None si no se encuentra
    """
    from app.models.current import Client, SystemUser
    
    # 1. Intentar modelo NUEVO (Client → Company → SystemUser admin)
    client = session.execute(
        select(Client).where(Client.phone_number == client_phone)
    ).scalar_one_or_none()
    
    if client and client.company_id:
        # Buscar el primer admin de esa empresa
        admin = session.execute(
            select(SystemUser).where(
                SystemUser.company_id == client.company_id,
                SystemUser.role == 'admin'
            )
        ).scalars().first()
        
        if admin:
            return {
                'admin_id': admin.id,
                'company_id': client.company_id,
                'client_id': client.id,
                'is_new_model': True,
                'admin_user': admin
            }
    
    # 2. Fallback a SystemUser con role='user' (si existen usuarios legacy ahí)
    user = session.execute(
        select(SystemUser).where(SystemUser.phone_number == client_phone, SystemUser.role == 'user')
    ).scalar_one_or_none()
    
    if user and user.company_id:
        admin = session.execute(
            select(SystemUser).where(
                SystemUser.company_id == user.company_id,
                SystemUser.role == 'admin'
            )
        ).scalars().first()
        
        if admin:
            return {
                'admin_id': admin.id,
                'company_id': user.company_id,
                'client_id': user.id, # En legacy, el user.id actúa como client_id
                'is_new_model': False,
                'admin_user': admin
            }
            
    return None


def get_rag_config_for_admin(session: Session, admin_info: Dict[str, Any]):
    """
    Obtener configuración RAG del admin o de su empresa
    """
    from app.models.rag_models import UserRAGConfig
    
    # Intentar por company_id primero (configuración compartida)
    config = session.execute(
        select(UserRAGConfig).where(
            UserRAGConfig.company_id == admin_info['company_id']
        )
    ).scalar_one_or_none()
    
    # Fallback a configuración individual por system_user_id
    if not config:
        config = session.execute(
            select(UserRAGConfig).where(
                UserRAGConfig.system_user_id == admin_info['admin_id']
            )
        ).scalar_one_or_none()
    
    return config


def search_rag_documents(query: str, admin_info: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Buscar documentos RAG relevantes para la empresa del admin
    """
    from app.services.rag_service import rag_service
    
    # Siempre preferimos buscar por company_id si está disponible
    return rag_service.search_similar_chunks(
        query=query,
        company_id=admin_info.get('company_id'),
        user_id=admin_info.get('admin_id') if not admin_info.get('company_id') else None,
        top_k=top_k
    )


async def generate_rag_response(query: str, admin_info: Dict[str, Any], context_docs: List[Dict[str, Any]], session: Session):
    """
    Generar respuesta RAG usando LLM (OpenAI o Ollama según config)
    """
    from app.services.openai_service import client as openai_client
    from app.services.ollama_service import generate_ollama_response
    
    # Obtener configuración RAG
    config = get_rag_config_for_admin(session, admin_info)
    
    if not config:
        logger.warning(f"No hay config RAG para admin {admin_info['admin_id']}")
        return None
        
    # Construir contexto a partir de los documentos encontrados
    context = "\n\n".join([doc['content'] for doc in context_docs])
    
    # Log del contexto encontrado
    logger.info(f"RAG Context: {len(context)} chars de {len(context_docs)} chunks")
    
    # Prompt de sistema dinámico
    system_prompt = config.system_prompt or "Eres un asistente profesional que responde basado en documentos."
    if config.company_description:
        system_prompt = f"{system_prompt}\n\nInformación de la empresa:\n{config.company_description}"
    
    model_name = config.model_name or "mistral"
    
    # Decidir si el modelo principal es local
    local_models = ["mistral", "llama3", "llama3.1", "llama3.2", "qwen", "deepseek", "phi3"]
    is_local_config = any(m in model_name.lower() for m in local_models)
    
    try:
        # INTENTO 1: LLM Local (Ollama) si está configurado como local
        if is_local_config:
            logger.info(f"🤖 Intentando LLM Local (Ollama): {model_name}")
            full_prompt = f"Consulta: {query}\n\nContexto de documentos:\n{context}"
            response = await generate_ollama_response(
                prompt=full_prompt,
                system_prompt=system_prompt,
                model=model_name,
                temperature=config.temperature or 0.7
            )
            
            if response:
                return response
            
            logger.warning("⚠️ Ollama no retornó respuesta, activando fallback a OpenAI...")

        # INTENTO 2: Fallback a OpenAI (si el local falló o si la config es online)
        logger.info(f"🌐 Generando respuesta con OpenAI (Fallback o Config): gpt-4o-mini")
        openai_response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Contexto de documentos:\n{context}"},
                {"role": "user", "content": query}
            ],
            temperature=config.temperature or 0.7,
            max_tokens=1000
        )
        return openai_response.choices[0].message.content

    except Exception as e:
        logger.error(f"❌ Error crítico en generación de respuesta RAG: {e}")
        # Último intento desesperado si algo falló en el bloque anterior
        if is_local_config:
            try:
                logger.info("🔄 Reintentando fallback final con OpenAI...")
                # ... repetir llamada simple a openai si es necesario ...
                pass 
            except: pass
        return None
