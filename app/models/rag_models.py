"""
Modelos de base de datos para RAG
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.current import Base
import enum


class FileType(str, enum.Enum):
    """Tipos de archivos soportados"""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"
    OTHER = "other"


class MemoryType(str, enum.Enum):
    """Tipos de memoria conversacional"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ENTITY = "entity"


class UserDocument(Base):
    """Documentos subidos por usuarios"""
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    system_user_id = Column(Integer, ForeignKey("system_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="System user who uploaded this document")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True, comment="Company who owns this document")
    filename = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False, comment="Tamaño en bytes")
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False, index=True)
    chunk_count = Column(Integer, default=0)
    doc_metadata = Column(JSON, comment="Metadata adicional del documento")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    system_user = relationship("SystemUser")
    company = relationship("Company")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunks de documentos"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, comment="Índice del chunk en el documento")
    content = Column(Text, nullable=False, comment="Contenido del chunk")
    embedding_id = Column(String(100), index=True, comment="ID en la vector DB (Chroma)")
    token_count = Column(Integer, comment="Número de tokens en el chunk")
    chunk_metadata = Column(JSON, comment="Metadata del chunk")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("UserDocument", back_populates="chunks")


class UserRAGConfig(Base):
    """Configuración RAG por usuario"""
    __tablename__ = "user_rag_config"
    
    id = Column(Integer, primary_key=True, index=True)
    system_user_id = Column(Integer, ForeignKey("system_users.id", ondelete="CASCADE"), nullable=True, index=True, comment="System user (individual config)")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True, comment="Company (shared config)")
    chunk_size = Column(Integer, default=512, comment="Tamaño de chunks en tokens")
    chunk_overlap = Column(Integer, default=50, comment="Overlap entre chunks")
    top_k = Column(Integer, default=5, comment="Número de chunks a recuperar")
    temperature = Column(Float, default=0.7, comment="Temperatura del LLM")
    model_name = Column(String(50), default="mistral", comment="Modelo LLM a usar")
    enable_hybrid_search = Column(Boolean, default=True, comment="Búsqueda híbrida keyword+semantic")
    enable_rag = Column(Boolean, default=True, comment="RAG habilitado para este usuario")
    system_prompt = Column(Text, nullable=True, comment="Prompt de sistema para RAG")
    company_description = Column(Text, nullable=True, comment="Descripción de la empresa para el contexto")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    system_user = relationship("SystemUser")
    company = relationship("Company")


class ConversationMemory(Base):
    """Memoria conversacional"""
    __tablename__ = "conversation_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = Column(Enum(MemoryType), nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_metadata = Column(JSON, comment="Metadata adicional de la memoria")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("Conversation")


class RAGUsageStats(Base):
    """Estadísticas de uso de RAG"""
    __tablename__ = "rag_usage_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    system_user_id = Column(Integer, ForeignKey("system_users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    query = Column(Text, nullable=False)
    retrieved_chunks_count = Column(Integer, default=0)
    response_time_ms = Column(Integer, comment="Tiempo de respuesta en milisegundos")
    model_used = Column(String(50))
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("SystemUser")
    conversation = relationship("Conversation")
