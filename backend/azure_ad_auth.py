"""
Azure AD Authentication Module for Streamlit

Provides authentication and authorization using Azure Active Directory.
Supports group-based access control.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Dict, Optional, Tuple

import msal
import requests
import streamlit as st

from config.settings import get_settings

logger = logging.getLogger(__name__)

def _clear_auth_query_params() -> None:
    """Clear auth-related query params from the URL."""
    try:
        st.query_params.clear()
    except Exception:
        pass


class AzureADAuthenticator:
    """
    Handles Azure AD authentication flow for Streamlit apps.
    
    Features:
    - OAuth 2.0 authorization code flow
    - Group membership validation
    - Token caching in Streamlit session state
    - Automatic token refresh
    """
    
    def __init__(self):
        settings = get_settings()
        self.config = settings.azure_ad
        
        if not self.config.enabled:
            logger.info("Azure AD authentication is disabled")
            return
        
        # Validate configuration
        if not all([self.config.client_id, self.config.client_secret, self.config.tenant_id]):
            raise ValueError(
                "Azure AD authentication is enabled but missing required configuration. "
                "Please set AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, and AZURE_AD_TENANT_ID"
            )
        
        # MSAL Configuration
        self.authority = f"https://login.microsoftonline.com/{self.config.tenant_id}"
        self.scopes = ["User.Read", "GroupMember.Read.All"]
        
        # Create MSAL app
        self.msal_app = msal.ConfidentialClientApplication(
            self.config.client_id,
            authority=self.authority,
            client_credential=self.config.client_secret,
        )
        
        logger.info("Azure AD authenticator initialized")
    
    def is_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.config.enabled
    
    def get_authorization_url(self) -> str:
        """
        Generate the authorization URL for user login.
        
        Returns:
            str: URL to redirect user for authentication
        """
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.config.redirect_uri,
        )
        return auth_url
    
    def acquire_token_by_auth_code(self, auth_code: str) -> Optional[Dict]:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code received from redirect
            
        Returns:
            Dict with token information or None if failed
        """
        try:
            result = self.msal_app.acquire_token_by_authorization_code(
                auth_code,
                scopes=self.scopes,
                redirect_uri=self.config.redirect_uri,
            )
            
            if "access_token" in result:
                logger.info("Successfully acquired access token")
                return result
            else:
                error = result.get("error_description", result.get("error"))
                logger.error(f"Failed to acquire token: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error acquiring token: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """
        Get user profile information from Microsoft Graph.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dict with user information or None if failed
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Retrieved user info for: {user_info.get('userPrincipalName')}")
                return user_info
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def check_group_membership(self, access_token: str) -> bool:
        """
        Check if user is member of the allowed security group.
        
        Args:
            access_token: Valid access token
            
        Returns:
            bool: True if user is member of allowed group or no group restriction
        """
        # If no group restriction, allow all authenticated users
        if not self.config.allowed_group_id:
            logger.info("No group restriction configured, allowing all authenticated users")
            return True
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me/memberOf",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                groups = response.json().get("value", [])
                group_ids = [group.get("id") for group in groups if group.get("id")]
                
                is_member = self.config.allowed_group_id in group_ids
                
                if is_member:
                    logger.info(f"User is member of allowed group: {self.config.allowed_group_id}")
                else:
                    logger.warning(f"User is NOT member of allowed group: {self.config.allowed_group_id}")
                    logger.debug(f"User groups: {group_ids}")
                
                return is_member
            else:
                logger.error(f"Failed to check group membership: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking group membership: {e}")
            return False
    
    def logout(self):
        """Clear authentication state."""
        if "auth_token" in st.session_state:
            del st.session_state["auth_token"]
        if "user_info" in st.session_state:
            del st.session_state["user_info"]
        if "authenticated" in st.session_state:
            del st.session_state["authenticated"]
        logger.info("User logged out")


def require_authentication() -> Tuple[bool, Optional[Dict]]:
    """
    Streamlit decorator-style function to require authentication.
    
    Call this at the start of your Streamlit app to enforce authentication.
    
    Returns:
        Tuple[bool, Optional[Dict]]: (is_authenticated, user_info)
        
    Example:
        ```python
        from backend.azure_ad_auth import require_authentication
        
        authenticated, user_info = require_authentication()
        if not authenticated:
            st.stop()
        
        st.write(f"Welcome {user_info['displayName']}")
        ```
    """
    settings = get_settings()
    
    # If authentication is disabled, allow access
    if not settings.azure_ad.enabled:
        return True, None
    
    # Initialize authenticator
    try:
        authenticator = AzureADAuthenticator()
    except ValueError as e:
        st.error(f"❌ Error de configuración: {e}")
        return False, None
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["auth_token"] = None
        st.session_state["user_info"] = None
    
    # Check for authorization code in URL (OAuth callback)
    query_params = st.query_params
    auth_code = query_params.get("code")
    
    if auth_code and not st.session_state["authenticated"]:
        # Exchange code for token
        with st.spinner("Autenticando..."):
            token_result = authenticator.acquire_token_by_auth_code(auth_code)
            
            if token_result and "access_token" in token_result:
                access_token = token_result["access_token"]
                
                # Get user info
                user_info = authenticator.get_user_info(access_token)
                
                if user_info:
                    # Check group membership
                    if authenticator.check_group_membership(access_token):
                        st.session_state["authenticated"] = True
                        st.session_state["auth_token"] = token_result
                        st.session_state["user_info"] = user_info
                        
                        # Clear query params (sin rerun para que se refleje la URL)
                        _clear_auth_query_params()
                    else:
                        st.error("❌ No tienes permisos para acceder a esta aplicación")
                        st.info("Contacta al administrador para solicitar acceso al grupo de seguridad requerido.")
                        return False, None
                else:
                    st.error("❌ Error al obtener información del usuario")
                    return False, None
            else:
                st.error("❌ Error en la autenticación")
                return False, None
    
    # If not authenticated, show login screen
    if not st.session_state["authenticated"]:
        st.markdown("# 🔐 Autenticación requerida")
        st.markdown("---")
        
        st.info("Esta aplicación requiere autenticación con tu cuenta de Microsoft.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Iniciar sesión con Microsoft", use_container_width=True, type="primary"):
                auth_url = authenticator.get_authorization_url()
                st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
                st.markdown(f"Si no se redirige automáticamente, [haz clic aquí]({auth_url})")
        
        st.markdown("---")
        st.caption("🔒 La autenticación se realiza de forma segura a través de Azure Active Directory")
        
        return False, None
    
    # User is authenticated
    if st.session_state.get("authenticated"):
        if query_params.get("code") or query_params.get("session_state"):
            _clear_auth_query_params()
    return True, st.session_state["user_info"]


def get_current_user() -> Optional[Dict]:
    """
    Get currently authenticated user information.
    
    Returns:
        Dict with user info or None if not authenticated
    """
    return st.session_state.get("user_info")


def render_user_info_sidebar():
    """
    Render user information in sidebar.
    
    Shows user name, email, and logout button.
    """
    user_info = get_current_user()
    
    if user_info:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Usuario")
            st.markdown(f"**{user_info.get('displayName', 'Usuario')}**")
            st.caption(user_info.get('mail') or user_info.get('userPrincipalName', ''))
            
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                authenticator = AzureADAuthenticator()
                authenticator.logout()
                st.rerun()
