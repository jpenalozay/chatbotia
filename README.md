# Chatbot RAG - TechStore Perú

Sistema de chatbot con RAG (Retrieval-Augmented Generation) para asistencia en ventas de productos tecnológicos.

## 🚀 Características

- **RAG**: Búsqueda semántica en catálogo de productos
- **LLM Local**: Ollama con Llama 3.2:3b
- **Panel Web**: Interfaz para asesores de ventas
- **Simulador**: Pruebas de conversaciones con grabación de voz
- **Comparador de Precios**: Búsqueda de precios en tiendas online
- **Fine-Tuning**: Exportación de datos para entrenamiento personalizado

## 📋 Requisitos

- Python 3.10+
- MySQL 8.0+
- Ollama instalado y corriendo
- GPU recomendada (para Ollama)

## ⚙️ Instalación

1. **Clonar repositorio**
```bash
git clone https://github.com/jpenalozay/chatbotia.git
cd chatbotia
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar `.env`**
```ini
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/chatbot_db
OLLAMA_HOST=http://localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2:3b
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

5. **Crear base de datos**
```sql
CREATE DATABASE chatbot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **Iniciar Ollama**
```bash
ollama serve
ollama pull llama3.2:3b
```

7. **Iniciar servidor**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 9090
```

8. **Abrir navegador**
```
http://localhost:9090
```

## 🎯 Uso

### Datos Demo
El sistema crea automáticamente:
- **Empresa**: Demo Company (código: 0001)
- **Usuario**: demo / demo123
- **Email**: demo@demo.com

### Funcionalidades Principales

1. **Simulador de Mensajes**
   - Simular conversaciones de clientes
   - Grabación de voz con Web Speech API
   - Respuestas automáticas con RAG

2. **Gestión de Documentos RAG**
   - Subir documentos (PDF, DOCX, XLSX, TXT, MD)
   - Indexación automática en ChromaDB
   - Búsqueda semántica

3. **Comparador de Precios**
   - Buscar precios en tiendas online
   - Comparación de productos
   - Links directos a tiendas

4. **Fine-Tuning**
   - Exportar conversaciones en formato JSONL
   - Compatible con OpenAI/Ollama/HuggingFace

## 🏗️ Arquitectura

```
Frontend (HTML/JS) → FastAPI → MySQL + ChromaDB → Ollama (LLM)
```

## 📁 Estructura del Proyecto

```
chatbot/
├── app/
│   ├── core/           # Configuración
│   ├── database/       # Conexión BD
│   ├── models/         # Modelos SQLAlchemy
│   ├── services/       # Servicios (RAG, LLM)
│   └── webapp/         # Templates HTML
├── .env                # Variables de entorno
├── catalogo_techstore.md  # Catálogo de productos
├── prompt.txt          # Prompt del sistema
└── requirements.txt    # Dependencias
```

## 🧹 Limpieza de Datos

Para limpiar la base de datos y empezar de cero:

```bash
python limpiar_datos.py
```

Esto eliminará:
- Todas las conversaciones
- Todos los mensajes
- Todos los clientes
- Documentos RAG
- ChromaDB
- Cache Python

## 📚 Documentación

Ver `GUIA_MAESTRA.md` para documentación completa del proyecto.

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto es privado y de uso exclusivo para TechStore Perú.

## 👤 Autor

**TechStore Perú**

## 🙏 Agradecimientos

- Ollama por el LLM local
- Langchain por el framework RAG
- ChromaDB por la base de datos vectorial
