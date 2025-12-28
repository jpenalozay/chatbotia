import os
from contextlib import contextmanager
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Cargar .env de python/ de forma explícita para asegurar consistencia entre procesos
_base_dir = Path(__file__).resolve().parents[1]
_env_path = _base_dir / '.env'
if _env_path.exists():
    load_dotenv(_env_path.as_posix())
else:
    load_dotenv(find_dotenv())

DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "chatbot_db")


def _ensure_database():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


_ensure_database()

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def _ensure_schema():
    """Auto‑migración mínima para columnas nuevas sin usar Alembic."""
    try:
        with engine.begin() as conn:
            # Asegurar que email permita NULL
            conn.execute(text("ALTER TABLE `users` MODIFY `email` VARCHAR(180) NULL"))
            # Agregar columna phone si no existe
            result = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'phone'"))
            if result.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `phone` VARCHAR(30) NULL"))
                # Índice único para phone
                conn.execute(text("CREATE UNIQUE INDEX `uq_users_phone` ON `users` (`phone`)"))

            # Crear tabla conversations si no existe
            tables = conn.execute(text("SHOW TABLES LIKE 'conversations'"))
            if tables.fetchone() is None:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS `conversations` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `user_id` INT NOT NULL,
                      `title` VARCHAR(200) NOT NULL DEFAULT 'Conversación',
                      `openai_thread_id` VARCHAR(100) NULL,
                      `mode` VARCHAR(20) NOT NULL DEFAULT 'inherit',
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      INDEX `idx_conversations_user_id` (`user_id`),
                      CONSTRAINT `fk_conversations_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ))

            # Agregar columna conversation_id a messages si no existe
            conv_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'conversation_id'"))
            if conv_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `conversation_id` INT NULL"))
                conn.execute(text("ALTER TABLE `messages` ADD INDEX `idx_messages_conversation_id` (`conversation_id`)"))

            # Agregar columna role a messages si no existe
            role_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'role'"))
            if role_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `role` VARCHAR(10) NOT NULL DEFAULT 'user'"))

            # Agregar columna direction a messages si no existe
            dir_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'direction'"))
            if dir_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `direction` VARCHAR(10) NULL"))

            # Agregar columna review_status a messages si no existe
            rev_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'review_status'"))
            if rev_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `review_status` VARCHAR(20) NULL"))
            rb_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'reviewed_by'"))
            if rb_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `reviewed_by` INT NULL"))
            sent_col = conn.execute(text("SHOW COLUMNS FROM `messages` LIKE 'sent_at'"))
            if sent_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `messages` ADD COLUMN `sent_at` DATETIME NULL"))

            # Tabla settings para modo global
            tables = conn.execute(text("SHOW TABLES LIKE 'settings'"))
            if tables.fetchone() is None:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS `settings` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `key` VARCHAR(100) NOT NULL,
                      `value` VARCHAR(200) NOT NULL,
                      `description` TEXT NULL,
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      UNIQUE KEY `uq_settings_key` (`key`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ))

            # Agregar columna role a users si no existe
            role_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'role'"))
            if role_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `role` VARCHAR(20) NOT NULL DEFAULT 'user'"))

            # Agregar columna avatar_url a users si no existe
            avatar_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'avatar_url'"))
            if avatar_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `avatar_url` VARCHAR(300) NULL"))

            # Agregar columna alias a users si no existe
            alias_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'alias'"))
            if alias_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `alias` VARCHAR(120) NULL"))

            # Nuevas columnas para perfil completo
            first_name_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'first_name'"))
            if first_name_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `first_name` VARCHAR(60) NULL"))

            last_name_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'last_name'"))
            if last_name_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `last_name` VARCHAR(60) NULL"))

            company_name_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'company_name'"))
            if company_name_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `company_name` VARCHAR(120) NULL"))

            position_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'position'"))
            if position_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `position` VARCHAR(80) NULL"))

            bio_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'bio'"))
            if bio_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `bio` TEXT NULL"))

            is_active_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'is_active'"))
            if is_active_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `is_active` BOOLEAN NOT NULL DEFAULT TRUE"))

            must_change_password_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'must_change_password'"))
            if must_change_password_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `must_change_password` BOOLEAN NOT NULL DEFAULT FALSE"))

            manager_id_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'manager_id'"))
            if manager_id_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `manager_id` INT NULL"))
                conn.execute(text("ALTER TABLE `users` ADD INDEX `idx_users_manager_id` (`manager_id`)"))

            # Crear tabla chat_assignments si no existe
            tables = conn.execute(text("SHOW TABLES LIKE 'chat_assignments'"))
            if tables.fetchone() is None:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS `chat_assignments` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `conversation_id` INT NOT NULL,
                      `asesor_id` INT NOT NULL,
                      `assigned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `status` VARCHAR(20) NOT NULL DEFAULT 'active',
                      `priority` VARCHAR(20) NOT NULL DEFAULT 'normal',
                      `notes` TEXT NULL,
                      PRIMARY KEY (`id`),
                      INDEX `idx_chat_assignments_conversation_id` (`conversation_id`),
                      INDEX `idx_chat_assignments_asesor_id` (`asesor_id`),
                      CONSTRAINT `fk_chat_assignments_conversation_id` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
                      CONSTRAINT `fk_chat_assignments_asesor_id` FOREIGN KEY (`asesor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ))

            # Crear tabla user_sessions si no existe
            tables = conn.execute(text("SHOW TABLES LIKE 'user_sessions'"))
            if tables.fetchone() is None:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS `user_sessions` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `user_id` INT NOT NULL,
                      `session_token` VARCHAR(255) NOT NULL,
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `expires_at` DATETIME NOT NULL,
                      `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
                      `ip_address` VARCHAR(45) NULL,
                      `user_agent` TEXT NULL,
                      PRIMARY KEY (`id`),
                      UNIQUE KEY `uq_user_sessions_session_token` (`session_token`),
                      INDEX `idx_user_sessions_user_id` (`user_id`),
                      CONSTRAINT `fk_user_sessions_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ))

            # Crear tabla audit_logs si no existe
            tables = conn.execute(text("SHOW TABLES LIKE 'audit_logs'"))
            if tables.fetchone() is None:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS `audit_logs` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `user_id` INT NOT NULL,
                      `action` VARCHAR(100) NOT NULL,
                      `resource_type` VARCHAR(50) NOT NULL,
                      `resource_id` INT NULL,
                      `details` JSON NULL,
                      `ip_address` VARCHAR(45) NULL,
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      INDEX `idx_audit_logs_user_id` (`user_id`),
                      INDEX `idx_audit_logs_action` (`action`),
                      INDEX `idx_audit_logs_resource` (`resource_type`, `resource_id`),
                      CONSTRAINT `fk_audit_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ))

            # Agregar columna username a users si no existe
            username_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'username'"))
            if username_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `username` VARCHAR(60) NULL"))
                conn.execute(text("CREATE UNIQUE INDEX `uq_users_username` ON `users` (`username`)"))

            # Agregar columna chat_bag_limit a users si no existe
            chat_bag_limit_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'chat_bag_limit'"))
            if chat_bag_limit_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `chat_bag_limit` INT NULL"))

            # Agregar columna notes a users si no existe
            notes_col = conn.execute(text("SHOW COLUMNS FROM `users` LIKE 'notes'"))
            if notes_col.fetchone() is None:
                conn.execute(text("ALTER TABLE `users` ADD COLUMN `notes` TEXT NULL"))

            # Asegurar rol administrador a partir de variable de entorno ADMIN_PHONE (9 dígitos Perú)
            admin_phone = os.getenv("ADMIN_PHONE")
            if admin_phone:
                # Normalizar solo dígitos
                import re as _re
                admin_digits = _re.sub(r"\D", "", admin_phone)
                if admin_digits:
                    conn.execute(text("UPDATE `users` SET `role`='admin' WHERE `phone`=:p"), {"p": admin_digits})
                    # Opcional: degradar otros a 'user' si hubiese más admins accidentales
                    conn.execute(text("UPDATE `users` SET `role`='user' WHERE `phone`<>:p AND `role`<>'user'"), {"p": admin_digits})

            # TABLA user_rag_config - Nuevas columnas system_prompt y company_description
            rag_tables = conn.execute(text("SHOW TABLES LIKE 'user_rag_config'"))
            if rag_tables.fetchone():
                # system_prompt
                sp_col = conn.execute(text("SHOW COLUMNS FROM `user_rag_config` LIKE 'system_prompt'"))
                if sp_col.fetchone() is None:
                    conn.execute(text("ALTER TABLE `user_rag_config` ADD COLUMN `system_prompt` TEXT NULL"))
                
                # company_description
                cd_col = conn.execute(text("SHOW COLUMNS FROM `user_rag_config` LIKE 'company_description'"))
                if cd_col.fetchone() is None:
                    conn.execute(text("ALTER TABLE `user_rag_config` ADD COLUMN `company_description` TEXT NULL"))
    except Exception:
        # Evitar que el arranque caiga si la tabla aún no existe (primera vez)
        # Será creada por Base.metadata.create_all en main.py
        pass


# Intentar alinear el esquema antes de servir dependencias
_ensure_schema()


def get_session():
    """FastAPI dependency: yields a DB session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for imperative use (commit/rollback)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


