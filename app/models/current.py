from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, DateTime, func, ForeignKey, Boolean, JSON, Numeric
from typing import Optional, List
from decimal import Decimal


class Base(DeclarativeBase):
    pass


# =====================================================
# NEW MODELS - Separated tables
# =====================================================

class Company(Base):
    """Companies/Organizations using the system"""
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, index=True, nullable=False, comment='Unique 4-digit company code')
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment='Company name')

    # Contact
    whatsapp_number: Mapped[str] = mapped_column(String(30), nullable=True, unique=True, index=True, comment='Company WhatsApp contact number (unique)')
    phone_number: Mapped[str] = mapped_column(String(30), nullable=True, comment='Company phone number')
    email: Mapped[str] = mapped_column(String(180), nullable=True, comment='Company email')

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment='Whether company is active')

    # Timestamps
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), comment='Creation timestamp')
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment='Last update timestamp')

    # Relationships
    system_users: Mapped[List['SystemUser']] = relationship('SystemUser', back_populates='company', cascade='all, delete-orphan')
    clients: Mapped[List['Client']] = relationship('Client', back_populates='company')

    def __repr__(self):
        return f"<Company(id={self.id}, code={self.code}, name={self.name})>"


class SystemUser(Base):
    """System users (admin, asesor, coordinador)"""
    __tablename__ = 'system_users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True, comment='Company ID')

    # Authentication
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True, comment='Unique username for login')
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True, comment='Email address')
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False, comment='Hashed password')

    # Profile (Peruvian naming: first_name, paternal_last_name, maternal_last_name)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False, comment='First name')
    paternal_last_name: Mapped[str] = mapped_column(String(60), nullable=False, comment='Paternal last name (apellido paterno)')
    maternal_last_name: Mapped[str] = mapped_column(String(60), nullable=True, comment='Maternal last name (apellido materno) - Perú')

    phone_number: Mapped[str] = mapped_column(String(30), nullable=True, comment='Personal phone number')
    alias: Mapped[str] = mapped_column(String(60), nullable=True, comment='Alias or nickname')
    photo_path: Mapped[str] = mapped_column(String(500), nullable=True, comment='Path to profile photo file')
    position: Mapped[str] = mapped_column(String(80), nullable=True, comment='Job position/title')
    bio: Mapped[str] = mapped_column(Text, nullable=True, comment='Biography or description')

    # Role and permissions
    role: Mapped[str] = mapped_column(String(20), default='asesor', nullable=False, index=True, comment='User role: admin, asesor, coordinador')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment='Whether user is active')
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment='Force password change on next login')

    # Hierarchical management
    supervisor_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='SET NULL'), nullable=True, index=True, comment='Supervisor user ID (manager)')

    # Chat management (for asesores)
    chat_bag_limit: Mapped[int] = mapped_column(Integer, nullable=True, comment='Maximum concurrent chats allowed (for asesores)')
    active_chats_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Current number of active chats assigned')

    notes: Mapped[str] = mapped_column(Text, nullable=True, comment='Internal notes about this user')

    # Timestamps
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), comment='Creation timestamp')
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment='Last update timestamp')
    last_login_at: Mapped[str] = mapped_column(DateTime, nullable=True, comment='Last successful login timestamp')

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='system_users')

    # Hierarchical (self-referencing)
    supervisor: Mapped[Optional['SystemUser']] = relationship(
        'SystemUser',
        back_populates='supervised_users',
        remote_side='SystemUser.id',
        foreign_keys=[supervisor_id]
    )
    supervised_users: Mapped[List['SystemUser']] = relationship(
        'SystemUser',
        back_populates='supervisor',
        foreign_keys=[supervisor_id]
    )

    # Assigned chats (as asesor)
    assigned_chats: Mapped[List['ChatAssignment']] = relationship(
        'ChatAssignment',
        back_populates='system_user',
        foreign_keys='ChatAssignment.system_user_id'
    )

    # User sessions
    sessions: Mapped[List['UserSession']] = relationship(
        'UserSession',
        back_populates='system_user',
        foreign_keys='UserSession.system_user_id'
    )

    # Audit logs
    audit_logs: Mapped[List['AuditLog']] = relationship(
        'AuditLog',
        back_populates='system_user',
        foreign_keys='AuditLog.system_user_id'
    )

    # Reviewed messages
    reviewed_messages: Mapped[List['Message']] = relationship(
        'Message',
        back_populates='reviewed_by_user',
        foreign_keys='Message.reviewed_by_id'
    )

    # Uploaded knowledge base files
    uploaded_files: Mapped[List['KnowledgeBaseFile']] = relationship(
        'KnowledgeBaseFile',
        back_populates='uploaded_by_user',
        foreign_keys='KnowledgeBaseFile.uploaded_by_id'
    )

    @property
    def name(self):
        """Full name for compatibility"""
        parts = [self.first_name, self.paternal_last_name]
        if self.maternal_last_name:
            parts.append(self.maternal_last_name)
        return " ".join(parts)

    @property
    def full_name(self):
        """Full name including maternal last name"""
        return self.name

    @property
    def company_code(self):
        """Compatibility property"""
        return self.company.code if self.company else None

    @property
    def company_name(self):
        """Compatibility property"""
        return self.company.name if self.company else None

    @property
    def phone(self):
        """Compatibility property for old code"""
        return self.phone_number

    def __repr__(self):
        return f"<SystemUser(id={self.id}, username={self.username}, role={self.role})>"


class Client(Base):
    """Clients interacting via WhatsApp"""
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id', ondelete='SET NULL'), nullable=True, index=True, comment='Company ID (optional)')

    # Identification (WhatsApp)
    phone_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True, comment='Phone number (WhatsApp)')
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment='Client name')
    email: Mapped[str] = mapped_column(String(180), nullable=True, comment='Email address (optional)')

    # Profile
    first_name: Mapped[str] = mapped_column(String(60), nullable=True, comment='First name')
    paternal_last_name: Mapped[str] = mapped_column(String(60), nullable=True, comment='Paternal last name')
    maternal_last_name: Mapped[str] = mapped_column(String(60), nullable=True, comment='Maternal last name (Perú)')

    alias: Mapped[str] = mapped_column(String(120), nullable=True, comment='Alias or nickname')
    photo_path: Mapped[str] = mapped_column(String(500), nullable=True, comment='Path to profile photo')
    notes: Mapped[str] = mapped_column(Text, nullable=True, comment='Notes about this client')

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment='Whether client is active')

    # WhatsApp metadata
    whatsapp_name: Mapped[str] = mapped_column(String(120), nullable=True, comment='Name from WhatsApp profile')
    whatsapp_profile_pic_url: Mapped[str] = mapped_column(String(500), nullable=True, comment='WhatsApp profile picture URL')

    # Statistics
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total messages sent/received')
    total_conversations: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total conversations')
    first_contact_at: Mapped[str] = mapped_column(DateTime, nullable=True, comment='First contact date and time')
    last_contact_at: Mapped[str] = mapped_column(DateTime, nullable=True, comment='Last contact date and time')
    last_seen_at: Mapped[str] = mapped_column(DateTime, nullable=True, comment='Last seen timestamp')

    # Tokens & Costs (accumulated totals)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total tokens consumed by this client')
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total prompt tokens')
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total completion tokens')
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, nullable=False, comment='Total cost in USD')

    # Timestamps
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), comment='Creation timestamp')
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment='Last update timestamp')

    # Relationships
    company: Mapped[Optional['Company']] = relationship('Company', back_populates='clients')
    conversations: Mapped[List['Conversation']] = relationship(
        'Conversation',
        back_populates='client',
        foreign_keys='Conversation.client_id',
        cascade='all, delete-orphan'
    )
    messages: Mapped[List['Message']] = relationship(
        'Message',
        back_populates='client',
        foreign_keys='Message.client_id'
    )

    @property
    def role(self):
        """Compatibility property"""
        return 'user'

    @property
    def company_code(self):
        """Compatibility property"""
        return self.company.code if self.company else None

    @property
    def company_name(self):
        """Compatibility property"""
        return self.company.name if self.company else None

    @property
    def full_name(self):
        """Full name including maternal last name"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.paternal_last_name:
            parts.append(self.paternal_last_name)
        if self.maternal_last_name:
            parts.append(self.maternal_last_name)
        return " ".join(parts) if parts else self.name

    @property
    def phone(self):
        """Compatibility property for old code"""
        return self.phone_number

    def __repr__(self):
        return f"<Client(id={self.id}, phone={self.phone_number}, name={self.name})>"


# =====================================================
class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey('clients.id', ondelete='CASCADE'), index=True, nullable=True, comment='Client ID (new FK)')
    title: Mapped[str] = mapped_column(String(200), default='Conversación')
    openai_thread_id: Mapped[str] = mapped_column(String(100), nullable=True)
    # 'inherit' | 'play' | 'pause' | 'stop'
    mode: Mapped[str] = mapped_column(String(20), default='inherit')
    status: Mapped[str] = mapped_column(String(20), default='active', comment='Status: active, archived, closed')

    # Tokens & Costs (per conversation)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total tokens used in this conversation')
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total prompt tokens')
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total completion tokens')
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, nullable=False, comment='Total cost in USD for this conversation')

    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_message_at: Mapped[str] = mapped_column(DateTime, nullable=True, comment='Last message timestamp')

    # Relationships
    client: Mapped[Optional['Client']] = relationship('Client', back_populates='conversations')

    # Nuevo: asignación de chat a asesor
    chat_assignments: Mapped[list['ChatAssignment']] = relationship('ChatAssignment', back_populates='conversation')


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey('clients.id', ondelete='CASCADE'), index=True, nullable=True, comment='Client ID (new FK)')
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(10))  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text)
    # metadata para modos y revisión
    direction: Mapped[str] = mapped_column(String(10), nullable=True)  # 'inbound' | 'outbound'
    review_status: Mapped[str] = mapped_column(String(20), nullable=True)  # 'none'|'pending'|'approved'|'rejected'
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)  # Legacy - user_id
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='SET NULL'), nullable=True, comment='System user who reviewed')

    # Tokens & Costs (per message)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Prompt tokens used for this message')
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Completion tokens generated')
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='Total tokens (prompt + completion)')

    # Cost per token (puede variar según modelo usado)
    cost_per_prompt_token: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0, nullable=False, comment='Cost per prompt token in USD')
    cost_per_completion_token: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0, nullable=False, comment='Cost per completion token in USD')
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, nullable=False, comment='Total cost for this message in USD')

    # Model info
    model_used: Mapped[str] = mapped_column(String(50), nullable=True, comment='OpenAI model used (e.g., gpt-4-turbo-preview)')

    sent_at: Mapped[str] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    conversation: Mapped[Optional['Conversation']] = relationship('Conversation')
    client: Mapped[Optional['Client']] = relationship('Client', back_populates='messages')
    reviewed_by_user: Mapped[Optional['SystemUser']] = relationship('SystemUser', foreign_keys=[reviewed_by_id])


class Setting(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(String(200))


# Nuevos modelos para el sistema de gestión

class ChatAssignment(Base):
    """Asignación de chats a asesores"""
    __tablename__ = 'chat_assignments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), index=True)
    system_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='SET NULL'), index=True, nullable=True, comment='System user ID (new FK)')
    assigned_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default='active')  # 'active' | 'completed' | 'transferred' | 'archived'
    priority: Mapped[str] = mapped_column(String(20), default='normal')  # 'low' | 'normal' | 'high' | 'urgent'
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relaciones
    conversation: Mapped['Conversation'] = relationship('Conversation', back_populates='chat_assignments')
    system_user: Mapped[Optional['SystemUser']] = relationship('SystemUser', back_populates='assigned_chats', foreign_keys=[system_user_id])


class UserSession(Base):
    """Sesiones de usuario para control de acceso"""
    __tablename__ = 'user_sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='CASCADE'), index=True, nullable=True, comment='System user ID (new FK)')
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[str] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    system_user: Mapped[Optional['SystemUser']] = relationship('SystemUser', foreign_keys=[system_user_id])


class AuditLog(Base):
    """Log de auditoría para acciones importantes"""
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='SET NULL'), index=True, nullable=True, comment='System user ID (new FK)')
    action: Mapped[str] = mapped_column(String(100))  # 'login', 'logout', 'create_user', 'assign_chat', etc.
    resource_type: Mapped[str] = mapped_column(String(50))  # 'user', 'conversation', 'chat_assignment'
    resource_id: Mapped[int] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(JSON, nullable=True)  # Datos adicionales en formato JSON
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    system_user: Mapped[Optional['SystemUser']] = relationship('SystemUser', back_populates='audit_logs', foreign_keys=[system_user_id])


class KnowledgeBaseFile(Base):
    """Archivos de base de conocimiento para el chatbot"""
    __tablename__ = 'knowledge_base_files'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey('system_users.id', ondelete='SET NULL'), index=True, nullable=True, comment='System user ID who uploaded (new FK)')
    filename: Mapped[str] = mapped_column(String(255))  # Nombre original del archivo
    stored_filename: Mapped[str] = mapped_column(String(255))  # Nombre en el servidor
    file_path: Mapped[str] = mapped_column(String(500))  # Ruta completa del archivo
    file_type: Mapped[str] = mapped_column(String(50))  # 'document', 'image', 'video', 'audio', 'other'
    mime_type: Mapped[str] = mapped_column(String(100))  # MIME type del archivo
    file_size: Mapped[int] = mapped_column(Integer)  # Tamaño en bytes
    openai_file_id: Mapped[str] = mapped_column(String(255), nullable=True)  # ID del archivo en OpenAI
    openai_vector_store_id: Mapped[str] = mapped_column(String(255), nullable=True)  # ID del vector store en OpenAI
    status: Mapped[str] = mapped_column(String(20), default='pending')  # 'pending', 'processing', 'ready', 'error'
    processing_error: Mapped[str] = mapped_column(Text, nullable=True)  # Mensaje de error si falla
    file_metadata: Mapped[str] = mapped_column(JSON, nullable=True)  # Metadatos adicionales (dimensiones, duración, etc.)
    description: Mapped[str] = mapped_column(Text, nullable=True)  # Descripción opcional del archivo
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Si está activo y disponible para el chatbot
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relación con usuario

    uploaded_by_user: Mapped[Optional['SystemUser']] = relationship('SystemUser', back_populates='uploaded_files', foreign_keys=[uploaded_by_id])


