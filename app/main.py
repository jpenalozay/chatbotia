"""
Main application - Chatbot RAG Demo
Versión simplificada sin WhatsApp, sin login, una sola empresa
"""

import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy.orm import Session
from pathlib import Path

# Importaciones locales
from app.database.connection import engine, get_session
from app.models.current import Base, Message, Conversation, Client
from app.models.rag_models import UserDocument
from app.core.config import settings

# Servicios
from app.services.rag_service import rag_service
from app.services.llm_service import ollama_service

# Crear tablas
Base.metadata.create_all(bind=engine)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializar datos demo al arrancar"""
    try:
        from app.init_demo_data import init_demo_data
        init_demo_data()
        print("✅ Datos demo inicializados")
    except Exception as e:
        print(f"⚠️ Error inicializando datos demo: {e}")
    
    yield
    
    # Cleanup (si es necesario)
    print("👋 Cerrando aplicación...")

# Inicializar FastAPI con lifespan
app = FastAPI(
    title="Chatbot RAG Demo",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar templates
templates_dir = Path(__file__).parent / "webapp" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# ============================================================================
# RUTAS PRINCIPALES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página principal - Panel demo"""
    return templates.TemplateResponse("demo_panel.html", {"request": request})


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "mode": "demo"}


# ============================================================================
# API DE CONVERSACIONES
# ============================================================================

@app.get("/api/conversations")
async def get_conversations(session: Session = Depends(get_session)):
    """Obtener todas las conversaciones"""
    try:
        # Obtener clientes con conversaciones
        clients = session.query(Client).filter(
            Client.company_id == settings.demo.COMPANY_ID
        ).all()
        
        conversations = []
        for client in clients:
            # Obtener última conversación del cliente
            conv = session.query(Conversation).filter(
                Conversation.client_id == client.id
            ).order_by(Conversation.updated_at.desc()).first()
            
            if conv:
                # Obtener último mensaje
                last_msg = session.query(Message).filter(
                    Message.conversation_id == conv.id
                ).order_by(Message.created_at.desc()).first()
                
                conversations.append({
                    "id": conv.id,
                    "client_id": client.id,
                    "client_name": client.first_name or "Cliente",
                    "phone": client.phone_number,
                    "last_message": last_msg.content[:50] if last_msg else "",
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "mode": conv.mode
                })
        
        # Ordenar por fecha de actualización
        conversations.sort(key=lambda x: x["updated_at"] or "", reverse=True)
        
        return conversations
        
    except Exception as e:
        print(f"❌ Error obteniendo conversaciones: {e}")
        return []


@app.get("/api/conversation/{conv_id}")
async def get_conversation(conv_id: int, session: Session = Depends(get_session)):
    """Obtener detalles de una conversación"""
    try:
        conv = session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()
        
        if not conv:
            return JSONResponse(
                {"ok": False, "detail": "Conversación no encontrada"},
                status_code=404
            )
        
        return {
            "id": conv.id,
            "client_id": conv.client_id,
            "mode": conv.mode,
            "status": conv.status,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo conversación: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


@app.put("/api/conversation/{conv_id}/mode")
async def update_conversation_mode(conv_id: int, payload=Body(...), session: Session = Depends(get_session)):
    """Actualizar modo de conversación"""
    try:
        mode = payload.get("mode")
        
        if mode not in ["auto", "manual", "review"]:
            return JSONResponse(
                {"ok": False, "detail": "Modo inválido. Debe ser: auto, manual o review"},
                status_code=400
            )
        
        conv = session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()
        
        if not conv:
            return JSONResponse(
                {"ok": False, "detail": "Conversación no encontrada"},
                status_code=404
            )
        
        conv.mode = mode
        conv.updated_at = datetime.now()
        session.commit()
        
        print(f"✅ Modo de conversación {conv_id} cambiado a: {mode}")
        
        return {"ok": True, "mode": mode}
        
    except Exception as e:
        print(f"❌ Error actualizando modo: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


@app.get("/api/messages/{conv_id}")
async def get_messages(conv_id: int, session: Session = Depends(get_session)):
    """Obtener mensajes de una conversación"""
    try:
        messages = session.query(Message).filter(
            Message.conversation_id == conv_id
        ).order_by(Message.created_at.asc()).all()
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
        
    except Exception as e:
        print(f"❌ Error obteniendo mensajes: {e}")
        return []


# ============================================================================
# API DE SIMULACIÓN DE MENSAJES
# ============================================================================

@app.post("/api/simulate-message")
async def simulate_message(payload=Body(...), session: Session = Depends(get_session)):
    """
    Simula un mensaje de un cliente
    Crea/busca cliente, crea conversación, procesa con RAG y genera respuesta
    """
    try:
        phone_number = payload.get("phone_number", "").strip()
        message = payload.get("message", "").strip()
        system_prompt = payload.get("system_prompt", "").strip()
        
        if not phone_number or not message:
            return JSONResponse(
                {"ok": False, "detail": "phone_number y message son requeridos"},
                status_code=400
            )
        
        # Usar prompt por defecto si no se proporciona
        if not system_prompt:
            system_prompt = "Eres un asistente útil que responde preguntas basándote en los documentos proporcionados. Sé conciso y preciso."
        
        print(f"📱 Simulando mensaje de {phone_number}: {message[:50]}...")
        print(f"🎯 System Prompt: {system_prompt[:100]}...")
        
        # 1. Buscar o crear cliente
        client = session.query(Client).filter(
            Client.phone_number == phone_number,
            Client.company_id == settings.demo.COMPANY_ID
        ).first()
        
        if not client:
            # Crear nuevo cliente
            client = Client(
                company_id=settings.demo.COMPANY_ID,
                phone_number=phone_number,
                name=f"Cliente {phone_number[-4:]}",
                first_name=f"Cliente {phone_number[-4:]}",
                is_active=True,
                first_contact_at=datetime.now(),
                last_contact_at=datetime.now()
            )
            session.add(client)
            session.commit()
            session.refresh(client)
            print(f"✅ Cliente creado: {client.id}")
        else:
            # Actualizar última interacción
            client.last_contact_at = datetime.now()
            session.commit()
            print(f"✅ Cliente existente: {client.id}")
        
        # 2. Buscar o crear conversación
        conv = session.query(Conversation).filter(
            Conversation.client_id == client.id,
            Conversation.status == "active"
        ).first()
        
        if not conv:
            conv = Conversation(
                client_id=client.id,
                status="active",
                mode="auto",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(conv)
            session.commit()
            session.refresh(conv)
            print(f"✅ Conversación creada: {conv.id}")
        else:
            conv.updated_at = datetime.now()
            session.commit()
            print(f"✅ Conversación existente: {conv.id}")
        
        # 3. Guardar mensaje del cliente
        user_msg = Message(
            conversation_id=conv.id,
            client_id=client.id,
            role="user",
            content=message,
            created_at=datetime.now()
        )
        session.add(user_msg)
        session.commit()
        print(f"✅ Mensaje del usuario guardado: {user_msg.id}")
        
        # 4. Procesar con RAG
        response_text = "Lo siento, no tengo información sobre eso."
        sources = []
        
        try:
            # Buscar en documentos RAG
            chunks = rag_service.search_similar_chunks(
                query=message,
                company_id=settings.demo.COMPANY_ID,
                top_k=5
            )
            
            if chunks:
                print(f"✅ Encontrados {len(chunks)} chunks relevantes")
                
                # Obtener historial de conversación (últimos 10 mensajes)
                history_messages = session.query(Message).filter(
                    Message.conversation_id == conv.id
                ).order_by(Message.created_at.desc()).limit(10).all()
                
                # Formatear historial para el LLM (orden cronológico)
                conversation_history = [
                    {
                        "role": msg.role,
                        "content": msg.content
                    }
                    for msg in reversed(history_messages)
                ]
                
                # Generar respuesta con LLM usando el prompt personalizado y contexto
                result = ollama_service.generate_with_rag(
                    query=message,
                    retrieved_chunks=chunks,
                    conversation_history=conversation_history,
                    temperature=0.7,
                    system_prompt=system_prompt  # Pasar el prompt personalizado
                )
                
                response_text = result.get("response", response_text)
                sources = result.get("sources", [])
                print(f"✅ Respuesta generada con RAG (con {len(conversation_history)} mensajes de contexto)")
            else:
                print("⚠️ No se encontraron chunks relevantes")
                response_text = "No encontré información relevante en los documentos. Por favor, sube documentos relacionados con tu consulta."
                
        except Exception as e:
            print(f"❌ Error en RAG: {e}")
            response_text = "Ocurrió un error al procesar tu consulta. Por favor, intenta de nuevo."
        
        # 5. Guardar respuesta del asistente
        assistant_msg = Message(
            conversation_id=conv.id,
            client_id=client.id,
            role="assistant",
            content=response_text,
            created_at=datetime.now()
        )
        session.add(assistant_msg)
        session.commit()
        print(f"✅ Respuesta del asistente guardada: {assistant_msg.id}")
        
        return {
            "ok": True,
            "conversation_id": conv.id,
            "response": response_text,
            "sources": sources
        }
        
    except Exception as e:
        print(f"❌ Error en simulate_message: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


# ============================================================================
# API DE CHAT (Respuesta manual del asesor)
# ============================================================================

@app.post("/api/chat")
async def send_chat_message(payload=Body(...), session: Session = Depends(get_session)):
    """Enviar mensaje desde el panel (respuesta del asesor)"""
    try:
        conversation_id = payload.get("conversation_id")
        message = payload.get("message", "").strip()
        
        if not conversation_id or not message:
            return JSONResponse(
                {"ok": False, "detail": "conversation_id y message son requeridos"},
                status_code=400
            )
        
        # Buscar conversación
        conv = session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conv:
            return JSONResponse(
                {"ok": False, "detail": "Conversación no encontrada"},
                status_code=404
            )
        
        # Guardar mensaje del asistente
        assistant_msg = Message(
            conversation_id=conv.id,
            client_id=conv.client_id,
            role="assistant",
            content=message,
            created_at=datetime.now()
        )
        session.add(assistant_msg)
        
        # Actualizar conversación
        conv.updated_at = datetime.now()
        session.commit()
        
        return {"ok": True}
        
    except Exception as e:
        print(f"❌ Error en send_chat_message: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


# ============================================================================
# API DE DOCUMENTOS RAG
# ============================================================================

@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Subir y procesar documento para RAG"""
    try:
        from app.models.rag_models import FileType, UserRAGConfig
        import shutil
        
        # Validar extensión
        file_ext = file.filename.split(".")[-1].lower()
        allowed = {"pdf": FileType.PDF, "docx": FileType.DOCX, "xlsx": FileType.XLSX, "txt": FileType.TXT, "md": FileType.MD}
        
        if file_ext not in allowed:
            return JSONResponse(
                {"ok": False, "detail": f"Tipo de archivo no soportado. Permitidos: {', '.join(allowed.keys())}"},
                status_code=400
            )
        
        # Crear directorio de uploads
        upload_dir = Path("uploads/documents")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # Crear registro en BD
        doc = UserDocument(
            system_user_id=settings.demo.USER_ID,
            company_id=settings.demo.COMPANY_ID,
            filename=file.filename,
            file_type=allowed[file_ext],
            file_path=str(file_path),
            file_size=file_size,
            processed=False
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        
        # Procesar documento
        try:
            # Extraer texto
            text = rag_service.process_document(str(file_path), file_ext)
            
            # Obtener configuración RAG
            config = session.query(UserRAGConfig).filter(
                UserRAGConfig.company_id == settings.demo.COMPANY_ID
            ).first()
            
            chunk_size = config.chunk_size if config else 512
            chunk_overlap = config.chunk_overlap if config else 50
            
            # Dividir en chunks
            chunks = rag_service.chunk_text(text, chunk_size, chunk_overlap)
            
            # Agregar al vector store
            rag_service.add_document_to_vectorstore(
                chunks=chunks,
                system_user_id=settings.demo.USER_ID,
                company_id=settings.demo.COMPANY_ID,
                document_id=doc.id,
                filename=file.filename,
                metadata={"file_type": file_ext}
            )
            
            # Actualizar documento
            doc.processed = True
            doc.chunk_count = len(chunks)
            session.commit()
            
            print(f"✅ Documento procesado: {file.filename} - {len(chunks)} chunks")
            
            return {
                "ok": True,
                "document_id": doc.id,
                "filename": file.filename,
                "chunks": len(chunks)
            }
            
        except Exception as e:
            print(f"❌ Error procesando documento: {e}")
            doc.processed = False
            session.commit()
            return JSONResponse(
                {"ok": False, "detail": f"Error procesando documento: {str(e)}"},
                status_code=500
            )
        
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


@app.get("/api/rag/documents")
async def list_documents(session: Session = Depends(get_session)):
    """Listar documentos RAG"""
    try:
        documents = session.query(UserDocument).filter(
            UserDocument.company_id == settings.demo.COMPANY_ID
        ).order_by(UserDocument.upload_date.desc()).all()
        
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.file_type.value,
                    "file_size": doc.file_size,
                    "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
                    "processed": doc.processed,
                    "chunk_count": doc.chunk_count
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        print(f"❌ Error listando documentos: {e}")
        return {"documents": []}


@app.delete("/api/rag/document/{document_id}")
async def delete_document(document_id: int, session: Session = Depends(get_session)):
    """Eliminar un documento RAG"""
    try:
        # Buscar documento
        doc = session.query(UserDocument).filter(
            UserDocument.id == document_id
        ).first()
        
        if not doc:
            return JSONResponse(
                {"ok": False, "detail": "Documento no encontrado"},
                status_code=404
            )
        
        # Eliminar archivo físico si existe
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        
        # Eliminar de la base de datos
        session.delete(doc)
        session.commit()
        
        print(f"✅ Documento eliminado: {doc.filename}")
        
        return {"ok": True, "message": "Documento eliminado correctamente"}
        
    except Exception as e:
        print(f"❌ Error eliminando documento: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


@app.post("/api/scrape-prices")
async def scrape_prices(request: dict):
    """
    Buscar precios de productos en tiendas online
    Por ahora retorna datos simulados - implementar scraping real después
    """
    try:
        brand = request.get("brand", "").strip()
        model = request.get("model", "").strip()
        
        if not brand or not model:
            return JSONResponse(
                {"ok": False, "detail": "Marca y modelo son requeridos"},
                status_code=400
            )
        
        print(f"🔍 Buscando precios para: {brand} {model}")
        
        # TODO: Implementar web scraping real
        # Por ahora, retornar datos simulados
        import random
        
        base_price = random.randint(3500, 5500)
        
        results = [
            {
                "store": "Saga Falabella",
                "url": f"https://www.falabella.com.pe/search?q={brand}+{model}",
                "price": base_price + random.randint(-200, 300),
                "currency": "PEN",
                "availability": "En stock",
                "title": f"Laptop {brand} {model}"
            },
            {
                "store": "Ripley",
                "url": f"https://simple.ripley.com.pe/search/{brand}+{model}",
                "price": base_price + random.randint(-150, 250),
                "currency": "PEN",
                "availability": "En stock",
                "title": f"Laptop {brand} {model}"
            },
            {
                "store": "Plaza Vea",
                "url": f"https://www.plazavea.com.pe/search?q={brand}+{model}",
                "price": base_price + random.randint(-100, 200),
                "currency": "PEN",
                "availability": "Pocas unidades",
                "title": f"Laptop {brand} {model}"
            }
        ]
        
        print(f"✅ Encontrados {len(results)} resultados simulados")
        
        return {
            "ok": True,
            "results": results,
            "query": f"{brand} {model}",
            "note": "⚠️ Datos simulados - Web scraping real pendiente de implementación"
        }
        
    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


@app.post("/api/export-training-data")
async def export_training_data(request: dict):
    """
    Exportar conversaciones en formato JSONL para fine-tuning
    """
    try:
        company_id = request.get("company_id", 2)
        
        print(f"📤 Exportando datos de entrenamiento para company_id: {company_id}")
        
        # Obtener conversaciones con mensajes
        session = SessionLocal()
        conversations = session.query(Conversation).filter(
            Conversation.company_id == company_id
        ).limit(100).all()
        
        if len(conversations) < 10:
            return JSONResponse(
                {"ok": False, "detail": "Necesitas al menos 10 conversaciones"},
                status_code=400
            )
        
        # Formatear en JSONL para OpenAI
        training_data = []
        for conv in conversations:
            messages_query = session.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at).all()
            
            if len(messages_query) < 2:
                continue
            
            # Formato OpenAI
            conversation_messages = [
                {"role": "system", "content": "Eres un asesor de ventas experto de TechStore Perú, especializado en productos tecnológicos."}
            ]
            
            for msg in messages_query:
                role = "user" if msg.sender_type == "client" else "assistant"
                conversation_messages.append({
                    "role": role,
                    "content": msg.content
                })
            
            training_data.append({
                "messages": conversation_messages
            })
        
        session.close()
        
        # Convertir a JSONL
        import json
        jsonl_data = "\n".join([json.dumps(item, ensure_ascii=False) for item in training_data])
        
        print(f"✅ {len(training_data)} conversaciones exportadas")
        
        return {
            "ok": True,
            "training_data": jsonl_data,
            "count": len(training_data),
            "format": "JSONL (OpenAI compatible)"
        }
        
    except Exception as e:
        print(f"❌ Error exportando datos: {e}")
        return JSONResponse(
            {"ok": False, "detail": str(e)},
            status_code=500
        )


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.web.HOST,
        port=settings.web.PORT,
        reload=settings.web.RELOAD
    )
