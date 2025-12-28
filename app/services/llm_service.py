"""
Servicio LLM usando Ollama
Maneja la generación de respuestas con contexto RAG
"""

import logging
from typing import List, Dict, Any, Optional
import requests
import json

logger = logging.getLogger(__name__)


class OllamaService:
    """Servicio para interactuar con Ollama LLM"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """
        Inicializa el servicio Ollama
        
        Args:
            base_url: URL base de Ollama API
            model: Nombre del modelo a usar
        """
        self.base_url = base_url
        self.model = model
        logger.info(f"Ollama Service inicializado - Model: {model}, URL: {base_url}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera una respuesta usando Ollama
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Instrucciones del sistema
            temperature: Temperatura para generación (0.0-1.0)
            max_tokens: Máximo de tokens a generar
            context: Contexto adicional (chunks recuperados)
            
        Returns:
            Dict con la respuesta y metadata
        """
        try:
            # Construir el prompt completo
            full_prompt = self._build_prompt(prompt, system_prompt, context)
            
            # Preparar request a Ollama
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            # Llamar a Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "response": result.get("response", ""),
                "model": result.get("model", self.model),
                "done": result.get("done", False),
                "context": result.get("context", []),
                "total_duration": result.get("total_duration", 0),
                "eval_count": result.get("eval_count", 0)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error llamando a Ollama API: {e}")
            raise Exception(f"Error conectando con Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            raise
    
    def generate_with_rag(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera respuesta usando RAG (Retrieval-Augmented Generation)
        
        Args:
            query: Pregunta del usuario
            retrieved_chunks: Chunks recuperados del vector store
            conversation_history: Historial de conversación
            temperature: Temperatura para generación
            system_prompt: Prompt del sistema personalizado (opcional)
            
        Returns:
            Dict con respuesta y metadata
        """
        # Construir contexto desde chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            content = chunk.get("content", "")
            filename = chunk.get("metadata", {}).get("filename", "documento")
            context_parts.append(f"[Documento {i}: {filename}]\n{content}")
        
        # System prompt para RAG (usar personalizado si se proporciona)
        if not system_prompt:
            system_prompt = """Eres un asistente inteligente que responde preguntas basándote en documentos proporcionados.

INSTRUCCIONES:
1. Usa SOLO la información de los documentos proporcionados para responder
2. Si la información no está en los documentos, di "No tengo información sobre eso en los documentos proporcionados"
3. Sé preciso y conciso
4. Si citas información, menciona de qué documento proviene
5. Mantén un tono profesional y amigable
6. Responde en español

DOCUMENTOS DISPONIBLES:
"""
        else:
            # Si hay prompt personalizado, agregar contexto de documentos
            system_prompt = f"""{system_prompt}

DOCUMENTOS DISPONIBLES:
"""
        
        # Agregar contexto de documentos
        context = "\n\n".join(context_parts) if context_parts else "No hay documentos disponibles."
        
        # Construir prompt con historial
        full_prompt = f"{system_prompt}\n{context}\n\n"
        
        if conversation_history:
            full_prompt += "HISTORIAL DE CONVERSACIÓN:\n"
            for msg in conversation_history[-5:]:  # Últimos 5 mensajes
                role = msg.get("role", "user")
                content = msg.get("content", "")
                full_prompt += f"{role.upper()}: {content}\n"
            full_prompt += "\n"
        
        full_prompt += f"PREGUNTA DEL USUARIO:\n{query}\n\nRESPUESTA:"
        
        # Generar respuesta
        result = self.generate(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=2000
        )
        
        # Agregar información de fuentes
        result["sources"] = [
            {
                "filename": chunk.get("metadata", {}).get("filename", ""),
                "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0)
            }
            for chunk in retrieved_chunks
        ]
        result["chunks_used"] = len(retrieved_chunks)
        
        return result
    
    def _build_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> str:
        """
        Construye el prompt completo
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Instrucciones del sistema
            context: Contexto adicional
            
        Returns:
            Prompt completo formateado
        """
        parts = []
        
        if system_prompt:
            parts.append(f"SISTEMA: {system_prompt}\n")
        
        if context:
            parts.append("CONTEXTO:\n")
            parts.extend(context)
            parts.append("\n")
        
        parts.append(f"USUARIO: {prompt}\n")
        parts.append("ASISTENTE:")
        
        return "\n".join(parts)
    
    def check_health(self) -> bool:
        """
        Verifica que Ollama esté funcionando
        
        Returns:
            True si Ollama está disponible
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """
        Lista los modelos disponibles en Ollama
        
        Returns:
            Lista de nombres de modelos
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listando modelos: {e}")
            return []


# Instancia global del servicio Ollama
from app.core.config import settings
ollama_service = OllamaService(
    base_url=settings.ollama.base_url,
    model=settings.ollama.MODEL
)
