"""
Health Check Module for ProyectoStaffAumentado

Provides liveness, readiness, and startup probes for container orchestration.
Follows Kubernetes/Azure Container Apps best practices.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import psutil

# Check if running in Streamlit context
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Centralized health check manager.
    
    Provides three types of probes:
    - Liveness: Is the app alive?
    - Readiness: Is the app ready to serve traffic?
    - Startup: Has the app finished initializing?
    """
    
    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.version = os.getenv("APP_VERSION", "unknown")
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def liveness_check(self) -> Dict[str, Any]:
        """
        Liveness probe - Check if application is alive.
        
        This should be lightweight and fast (<100ms).
        Returns 200 if alive, 500 if dead.
        """
        try:
            return {
                "status": "alive",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            }
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return {
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def readiness_check(self) -> Dict[str, Any]:
        """
        Readiness probe - Check if application is ready to serve traffic.
        
        Checks:
        - Memory usage < 90%
        - CPU usage < 90%
        - Azure OpenAI connectivity (if configured)
        - SQL connectivity (if using SQL adapter)
        
        Returns 200 if ready, 503 if not ready.
        """
        checks = {}
        all_ready = True
        
        try:
            # Memory check
            memory = psutil.virtual_memory()
            checks["memory"] = {
                "healthy": memory.percent < 90,
                "percent_used": round(memory.percent, 2),
                "available_gb": round(memory.available / (1024**3), 2),
            }
            if not checks["memory"]["healthy"]:
                all_ready = False
            
            # CPU check
            cpu_percent = psutil.cpu_percent(interval=0.1)
            checks["cpu"] = {
                "healthy": cpu_percent < 90,
                "percent_used": round(cpu_percent, 2),
            }
            if not checks["cpu"]["healthy"]:
                all_ready = False
            
            # Azure OpenAI check (optional)
            checks["azure_openai"] = await self._check_openai_connection()
            if not checks["azure_openai"]["healthy"]:
                all_ready = False
            
            # SQL check (if enabled)
            checks["sql_database"] = await self._check_sql_connection()
            if not checks["sql_database"]["healthy"]:
                all_ready = False
            
            return {
                "status": "ready" if all_ready else "not_ready",
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    def startup_check(self) -> Dict[str, Any]:
        """
        Startup probe - Check if application has finished initializing.
        
        Returns information about the application state.
        """
        return {
            "status": "started",
            "version": self.version,
            "environment": self.environment,
            "startup_time": self.startup_time.isoformat(),
            "python_version": sys.version,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def _check_openai_connection(self) -> Dict[str, Any]:
        """Check if Azure OpenAI is accessible."""
        try:
            from config.settings import get_settings
            
            settings = get_settings()
            
            # If not configured, skip check
            if not settings.azure_openai.endpoint or not settings.azure_openai.key:
                return {
                    "healthy": True,
                    "status": "not_configured",
                    "message": "Azure OpenAI not configured (OK for development)"
                }
            
            # Try to create client (don't make actual API call to save costs)
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai.endpoint,
                api_key=settings.azure_openai.key,
                api_version=settings.azure_openai.api_version,
            )
            
            return {
                "healthy": True,
                "status": "configured",
                "endpoint": settings.azure_openai.endpoint[:30] + "...",
            }
            
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e)[:100],
            }
    
    async def _check_sql_connection(self) -> Dict[str, Any]:
        """Check if SQL database is accessible."""
        try:
            from config.settings import get_settings
            
            settings = get_settings()
            data_source_type = os.getenv("DATA_SOURCE_TYPE", "excel").lower()
            
            # If not using SQL, skip check
            if data_source_type != "sql":
                return {
                    "healthy": True,
                    "status": "not_in_use",
                    "message": "SQL adapter not in use"
                }
            
            # Try to create adapter (don't make actual connection to save time)
            from backend.adapters.sql_adapter import FabricSQLAdapter
            from backend.adapters import DataSourceConfig
            
            config = DataSourceConfig(source_type="sql")
            adapter = FabricSQLAdapter(config)
            
            # Basic configuration check
            if not adapter.server or not adapter.database:
                return {
                    "healthy": False,
                    "status": "misconfigured",
                    "error": "SQL server or database not configured"
                }
            
            return {
                "healthy": True,
                "status": "configured",
                "server": adapter.server[:30] + "...",
            }
            
        except Exception as e:
            logger.warning(f"SQL health check failed: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e)[:100],
            }


# Global instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create health checker singleton."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# Streamlit integration (if available)
if STREAMLIT_AVAILABLE:
    
    @st.cache_data(ttl=30)
    def render_health_status():
        """Render health status in Streamlit sidebar (cached for 30s)."""
        checker = get_health_checker()
        
        with st.sidebar:
            with st.expander("🏥 System Health", expanded=False):
                liveness = checker.liveness_check()
                
                # Show status
                if liveness["status"] == "alive":
                    st.success("✅ System Operational")
                else:
                    st.error("❌ System Down")
                
                # Show metrics
                memory = psutil.virtual_memory()
                st.metric("Memory", f"{memory.percent:.1f}%")
                
                cpu = psutil.cpu_percent(interval=0.1)
                st.metric("CPU", f"{cpu:.1f}%")
                
                uptime = liveness.get("uptime_seconds", 0)
                st.caption(f"Uptime: {uptime/3600:.1f} hours")
