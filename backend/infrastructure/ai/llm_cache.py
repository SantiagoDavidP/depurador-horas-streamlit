"""
Módulo de caché simple para correcciones de LLM.

Proporciona caché en memoria con TTL para reducir llamadas redundantes al LLM.
Para caché persistente con Redis, modificar LLMCorrector para usar este módulo.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrada de caché con TTL."""
    value: Dict[str, Any]
    timestamp: float
    ttl: float
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado."""
        return time.time() - self.timestamp > self.ttl


class SimpleLLMCache:
    """
    Caché simple en memoria para respuestas de LLM.
    
    Características:
    - Cache en memoria con TTL configurable
    - Genera keys basadas en hash SHA256 del contenido
    - Limpia automáticamente entradas expiradas
    - Thread-safe básico (para uso con AsyncIO)
    
    Para producción con múltiples workers, considere usar Redis.
    """
    
    def __init__(self, default_ttl: int = 86400 * 7, max_size: int = 1000):
        """
        Args:
            default_ttl: Tiempo de vida en segundos (default: 7 días)
            max_size: Tamaño máximo del caché antes de limpiar
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, text: str, role: str, project: str) -> str:
        """Genera una key única para el caché."""
        content = f"{text}|{role}|{project}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, role: str, project: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un valor del caché si existe y no ha expirado.
        
        Returns:
            Dict con la respuesta del LLM o None si no existe/expiró
        """
        key = self._generate_key(text, role, project)
        
        entry = self._cache.get(key)
        if entry is None:
            self.misses += 1
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self.misses += 1
            logger.debug("Cache expired for key %s", key[:16])
            return None
        
        self.hits += 1
        logger.debug("Cache hit for key %s", key[:16])
        return entry.value
    
    def set(self, text: str, role: str, project: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Guarda un valor en el caché.
        
        Args:
            text: Texto original
            role: Rol del usuario
            project: Nombre del proyecto
            value: Respuesta del LLM a cachear
            ttl: Tiempo de vida opcional (usa default si None)
        """
        # Limpiar caché si está muy lleno
        if len(self._cache) >= self.max_size:
            self._cleanup_expired()
            
            # Si sigue lleno después de limpiar, eliminar las más antiguas
            if len(self._cache) >= self.max_size:
                self._evict_oldest(count=self.max_size // 4)
        
        key = self._generate_key(text, role, project)
        ttl = ttl or self.default_ttl
        
        self._cache[key] = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl
        )
        logger.debug("Cached result for key %s", key[:16])
    
    def _cleanup_expired(self) -> int:
        """Elimina todas las entradas expiradas."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info("Cleaned %d expired cache entries", len(expired_keys))
        
        return len(expired_keys)
    
    def _evict_oldest(self, count: int) -> None:
        """Elimina las entradas más antiguas."""
        if not self._cache:
            return
        
        # Ordenar por timestamp y eliminar las más antiguas
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].timestamp
        )
        
        for key, _ in sorted_items[:count]:
            del self._cache[key]
        
        logger.info("Evicted %d oldest cache entries", count)
    
    def clear(self) -> None:
        """Limpia todo el caché."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }


# Instancia global del caché (singleton pattern)
_global_cache: Optional[SimpleLLMCache] = None


def get_llm_cache() -> SimpleLLMCache:
    """Obtiene la instancia global del caché."""
    global _global_cache
    if _global_cache is None:
        _global_cache = SimpleLLMCache()
    return _global_cache
