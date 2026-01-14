"""
Streamlit UI Theme Module v2
============================
Professional theme system with Light/Dark mode support - Fixed version.
"""

import streamlit as st

# ============================================================================
# THEME INITIALIZATION
# ============================================================================

def init_theme() -> str:
    """Initialize theme in session state."""
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "light"
    return st.session_state["theme_mode"]


def get_theme() -> str:
    """Get the current theme mode."""
    return st.session_state.get("theme_mode", "light")


def set_theme(mode: str) -> None:
    """Set the current theme mode."""
    st.session_state["theme_mode"] = mode


# ============================================================================
# CSS GENERATOR
# ============================================================================

def get_complete_css(is_dark: bool) -> str:
    """Generate complete CSS based on theme."""
    
    if is_dark:
        # Dark theme colors
        colors = {
            "bg_app": "#0a0a0b",
            "bg_main": "#0a0a0b",
            "bg_sidebar": "#111113",
            "bg_card": "#18181b",
            "bg_card_hover": "#1f1f23",
            "bg_input": "#18181b",
            "bg_hover": "#27272a",
            "text_primary": "#fafafa",
            "text_secondary": "#a1a1aa",
            "text_muted": "#71717a",
            "border": "#27272a",
            "border_subtle": "#1f1f23",
            "accent": "#3b82f6",
            "accent_hover": "#60a5fa",
            "success": "#22c55e",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "info": "#06b6d4",
        }
    else:
        # Light theme colors
        colors = {
            "bg_app": "#f8fafc",
            "bg_main": "#ffffff",
            "bg_sidebar": "#f1f5f9",
            "bg_card": "#ffffff",
            "bg_card_hover": "#f8fafc",
            "bg_input": "#ffffff",
            "bg_hover": "#f1f5f9",
            "text_primary": "#0f172a",
            "text_secondary": "#475569",
            "text_muted": "#94a3b8",
            "border": "#e2e8f0",
            "border_subtle": "#f1f5f9",
            "accent": "#2563eb",
            "accent_hover": "#1d4ed8",
            "success": "#16a34a",
            "warning": "#d97706",
            "error": "#dc2626",
            "info": "#0891b2",
        }
    
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* ================================================================
       ROOT VARIABLES
       ================================================================ */
    :root {{
        --bg-app: {colors['bg_app']};
        --bg-main: {colors['bg_main']};
        --bg-sidebar: {colors['bg_sidebar']};
        --bg-card: {colors['bg_card']};
        --bg-card-hover: {colors['bg_card_hover']};
        --bg-input: {colors['bg_input']};
        --bg-hover: {colors['bg_hover']};
        --text-primary: {colors['text_primary']};
        --text-secondary: {colors['text_secondary']};
        --text-muted: {colors['text_muted']};
        --border: {colors['border']};
        --border-subtle: {colors['border_subtle']};
        --accent: {colors['accent']};
        --accent-hover: {colors['accent_hover']};
        --success: {colors['success']};
        --warning: {colors['warning']};
        --error: {colors['error']};
        --info: {colors['info']};
    }}
    
    /* ================================================================
       HIDE STREAMLIT DEFAULTS
       ================================================================ */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* ================================================================
       MAIN APP CONTAINER
       ================================================================ */
    .stApp {{
        background-color: var(--bg-app) !important;
    }}
    
    .stApp > header {{
        background-color: transparent !important;
    }}
    
    .main .block-container {{
        background-color: var(--bg-main) !important;
        padding: 1.5rem 2rem !important;
        max-width: 100% !important;
        width: 100% !important;
        border-radius: 0;
    }}
    
    /* Use full horizontal space next to the sidebar */
    [data-testid="stAppViewContainer"] > .main {{
        padding-left: 0 !important;
        padding-right: 0 !important;
    }}
    
    section.main > div {{
        background-color: var(--bg-main) !important;
    }}
    
    /* ================================================================
       SIDEBAR
       ================================================================ */
    section[data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }}
    
    section[data-testid="stSidebar"] > div {{
        background-color: var(--bg-sidebar) !important;
    }}
    
    section[data-testid="stSidebar"] > div:first-child {{
        background-color: var(--bg-sidebar) !important;
        padding-top: 1.5rem !important;
    }}
    
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] label {{
        color: var(--text-secondary) !important;
    }}
    
    section[data-testid="stSidebar"] hr {{
        border-color: var(--border) !important;
        margin: 1rem 0 !important;
    }}
    
    /* ================================================================
       TYPOGRAPHY
       ================================================================ */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-secondary);
    }}
    
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }}
    
    .stApp h1 {{
        font-size: 1.875rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }}
    
    .stApp h2 {{
        font-size: 1.25rem !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
    }}
    
    /* Gradient title */
    .gradient-title {{
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }}
    
    /* ================================================================
       BUTTONS
       ================================================================ */
    .stButton > button {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
        border: 1px solid var(--border) !important;
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}
    
    .stButton > button:hover {{
        background-color: var(--bg-hover) !important;
        border-color: var(--accent) !important;
    }}
    
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
        opacity: 1 !important;
    }}

    /* Force label and icon of primary buttons to stay white */
    .stButton > button[kind="primary"] *,
    .stButton > button[data-testid="baseButton-primary"] *,
    button[data-testid="baseButton-primary"] span,
    button[data-testid="baseButton-primary"] svg {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}
    
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {{
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        transform: translateY(-1px);
    }}

    .stButton > button:disabled,
    .stButton > button[disabled],
    button[data-testid="baseButton-primary"][disabled] {{
        background: linear-gradient(135deg, #475569, #334155) !important;
        color: #e2e8f0 !important;
        opacity: 0.9 !important;
        text-shadow: none !important;
        box-shadow: none !important;
    }}
    
    /* Download button */
    .stDownloadButton > button {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--accent) !important;
        color: var(--accent) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }}
    
    .stDownloadButton > button:hover {{
        background-color: var(--accent) !important;
        color: white !important;
    }}
    
    /* ================================================================
       INPUTS
       ================================================================ */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }}
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {{
        color: var(--text-muted) !important;
    }}
    
    /* Selectbox */
    .stSelectbox > div > div {{
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }}
    
    .stSelectbox > div > div > div {{
        color: var(--text-primary) !important;
    }}
    
    .stSelectbox [data-baseweb="select"] > div {{
        background-color: var(--bg-input) !important;
    }}
    
    /* Checkbox and Radio */
    .stCheckbox label span,
    .stRadio label span {{
        color: var(--text-secondary) !important;
    }}
    
    .stRadio > div {{
        background-color: transparent !important;
    }}
    
    .stRadio label {{
        color: var(--text-secondary) !important;
    }}
    
    /* ================================================================
       FILE UPLOADER
       ================================================================ */
    [data-testid="stFileUploader"] {{
        background-color: transparent !important;
    }}
    
    [data-testid="stFileUploader"] > section {{
        background-color: var(--bg-card) !important;
        border: 2px dashed var(--border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }}
    
    [data-testid="stFileUploader"] > section:hover {{
        border-color: var(--accent) !important;
        background-color: var(--bg-hover) !important;
    }}
    
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span {{
        color: var(--text-muted) !important;
    }}
    
    [data-testid="stFileUploaderDropzone"] {{
        background-color: var(--bg-card) !important;
    }}
    
    /* ================================================================
       EXPANDER
       ================================================================ */
    .streamlit-expanderHeader {{
        background-color: var(--bg-card) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: var(--bg-card) !important;
        border-radius: 0 0 8px 8px !important;
    }}
    
    [data-testid="stExpander"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        overflow: hidden;
    }}
    
    [data-testid="stExpander"] details {{
        background-color: var(--bg-card) !important;
    }}
    
    [data-testid="stExpander"] summary {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}
    
    [data-testid="stExpander"] summary:hover {{
        background-color: var(--bg-hover) !important;
    }}
    
    /* ================================================================
       METRICS
       ================================================================ */
    [data-testid="stMetric"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.2s ease;
    }}
    
    [data-testid="stMetric"]:hover {{
        border-color: var(--accent) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    [data-testid="stMetric"] label {{
        color: var(--text-muted) !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    
    [data-testid="stMetricValue"] {{
        color: var(--text-primary) !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }}
    
    [data-testid="stMetricDelta"] {{
        font-size: 0.875rem !important;
    }}
    
    /* ================================================================
       DATAFRAME / TABLE
       ================================================================ */
    [data-testid="stDataFrame"] {{
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        overflow: hidden;
    }}
    
    [data-testid="stDataFrame"] [data-testid="glideDataEditor"] {{
        border: none !important;
    }}
    
    /* ================================================================
       TABS
       ================================================================ */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: var(--bg-hover) !important;
        border-radius: 10px !important;
        padding: 4px !important;
        gap: 4px !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent !important;
        border-radius: 8px !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}
    
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}
    
    .stTabs [data-baseweb="tab-panel"] {{
        background-color: transparent !important;
    }}
    
    /* ================================================================
       ALERTS
       ================================================================ */
    .stAlert, [data-baseweb="notification"] {{
        border-radius: 8px !important;
        border: none !important;
        border-left: 4px solid !important;
    }}
    
    .stSuccess, [data-baseweb="notification"][kind="positive"] {{
        background-color: rgba(34, 197, 94, 0.1) !important;
        border-left-color: var(--success) !important;
    }}
    
    .stWarning, [data-baseweb="notification"][kind="warning"] {{
        background-color: rgba(245, 158, 11, 0.1) !important;
        border-left-color: var(--warning) !important;
    }}
    
    .stError, [data-baseweb="notification"][kind="negative"] {{
        background-color: rgba(239, 68, 68, 0.1) !important;
        border-left-color: var(--error) !important;
    }}
    
    .stInfo, [data-baseweb="notification"][kind="info"] {{
        background-color: rgba(6, 182, 212, 0.1) !important;
        border-left-color: var(--info) !important;
    }}
    
    /* Alert text */
    .stAlert p, [data-baseweb="notification"] p {{
        color: var(--text-secondary) !important;
    }}
    
    /* ================================================================
       PROGRESS BAR
       ================================================================ */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #3b82f6, #8b5cf6) !important;
        border-radius: 999px !important;
    }}
    
    .stProgress > div > div > div {{
        background-color: var(--bg-hover) !important;
        border-radius: 999px !important;
    }}
    
    /* ================================================================
       DIVIDER
       ================================================================ */
    hr {{
        border: none !important;
        height: 1px !important;
        background-color: var(--border) !important;
        margin: 1.5rem 0 !important;
    }}
    
    /* ================================================================
       PLOTLY CHARTS
       ================================================================ */
    [data-testid="stPlotlyChart"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }}
    
    /* ================================================================
       CAPTION
       ================================================================ */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
    }}
    
    /* ================================================================
       SLIDER
       ================================================================ */
    .stSlider > div > div > div > div {{
        background-color: var(--accent) !important;
    }}
    
    .stSlider [data-baseweb="slider"] div {{
        background-color: var(--bg-hover) !important;
    }}
    
    .stSlider p, .stSlider label {{
        color: var(--text-secondary) !important;
    }}
    
    /* ================================================================
       CODE BLOCK
       ================================================================ */
    .stCodeBlock, code {{
        background-color: var(--bg-hover) !important;
        border-radius: 6px !important;
        color: var(--accent) !important;
    }}
    
    /* ================================================================
       NUMBER INPUT
       ================================================================ */
    .stNumberInput label {{
        color: var(--text-secondary) !important;
    }}
    
    /* ================================================================
       CUSTOM SCROLLBAR
       ================================================================ */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: var(--bg-sidebar);
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: var(--border);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--text-muted);
    }}
    
    /* ================================================================
       CONTAINER
       ================================================================ */
    [data-testid="stVerticalBlock"] {{
        background-color: transparent !important;
    }}
    
    /* ================================================================
       CUSTOM COMPONENTS
       ================================================================ */
    .theme-toggle-box {{
        background-color: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 12px;
    }}
    
    .empty-state {{
        text-align: center;
        padding: 3rem 2rem;
        background-color: var(--bg-card);
        border: 2px dashed var(--border);
        border-radius: 16px;
        margin: 1.5rem 0;
    }}
    
    .empty-state-icon {{
        font-size: 3rem;
        margin-bottom: 1rem;
    }}
    
    .empty-state-title {{
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }}
    
    .empty-state-desc {{
        font-size: 0.875rem;
        color: var(--text-muted);
    }}
    
    .status-card {{
        padding: 1rem 1.25rem;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 1rem 0;
    }}
    
    .status-card.success {{
        background-color: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
    }}
    
    .status-card.error {{
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    
    .status-card-icon {{
        font-size: 1.5rem;
    }}
    
    .status-card-title {{
        font-weight: 600;
        font-size: 1rem;
        margin: 0;
    }}
    
    .status-card-desc {{
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin: 4px 0 0 0;
    }}
    
    .section-header {{
        margin-bottom: 1rem;
    }}
    
    .section-header-title {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
    }}
    
    .section-header-desc {{
        margin: 4px 0 0 0;
        font-size: 0.875rem;
        color: var(--text-muted);
    }}
    
    .info-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-top: 8px;
    }}
    
    .info-item {{
        background-color: var(--bg-hover);
        border-radius: 8px;
        padding: 12px;
    }}
    
    .info-item-label {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 4px;
    }}
    
    .info-item-value {{
        font-weight: 500;
        color: var(--text-primary);
    }}
    
    .header-container {{
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border);
    }}
    
    .header-icon {{
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }}
    
    .header-text h1 {{
        margin: 0;
        line-height: 1.2;
    }}
    
    .header-subtitle {{
        margin: 4px 0 0 0;
        color: var(--text-muted);
        font-size: 0.9rem;
    }}
    
    </style>
    """


# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def apply_theme() -> None:
    """Apply the complete theme system."""
    current_theme = init_theme()
    is_dark = current_theme == "dark"
    css = get_complete_css(is_dark)
    st.markdown(css, unsafe_allow_html=True)


def render_theme_toggle() -> str:
    """Render theme toggle in sidebar."""
    current_theme = init_theme()
    is_dark = current_theme == "dark"
    
    # Visual indicator
    icon = "🌙" if is_dark else "☀️"
    status_text = "Oscuro" if is_dark else "Claro"
    
    st.markdown(f"""
        <div class="theme-toggle-box">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 1.25rem;">{icon}</span>
                <span style="font-size: 0.85rem; color: var(--text-secondary); font-weight: 500;">Tema {status_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    new_is_dark = st.toggle("Activar modo oscuro", value=is_dark, key="theme_switch")
    
    new_theme = "dark" if new_is_dark else "light"
    if new_theme != current_theme:
        set_theme(new_theme)
        st.rerun()
    
    return new_theme


def render_header(title: str, subtitle: str = "") -> None:
    """Render styled app header."""
    st.markdown(f"""
        <div class="header-container">
            <div class="header-icon">⏱️</div>
            <div class="header-text">
                <h1 class="gradient-title">{title}</h1>
                <p class="header-subtitle">{subtitle}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, icon: str = "", description: str = "") -> None:
    """Render section header."""
    icon_html = f"<span style='font-size: 1.25rem;'>{icon}</span>" if icon else ""
    desc_html = f'<p class="section-header-desc">{description}</p>' if description else ""
    
    st.markdown(f"""
        <div class="section-header">
            <div class="section-header-title">{icon_html} {title}</div>
            {desc_html}
        </div>
    """, unsafe_allow_html=True)


def render_divider() -> None:
    """Render a styled divider."""
    st.markdown("<hr>", unsafe_allow_html=True)


def render_empty_state(icon: str, title: str, description: str) -> None:
    """Render empty state placeholder."""
    st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <div class="empty-state-title">{title}</div>
            <div class="empty-state-desc">{description}</div>
        </div>
    """, unsafe_allow_html=True)


def render_status_card(status: str, title: str, description: str) -> None:
    """Render status card (success/error)."""
    icon = "✅" if status == "success" else "🚫"
    color_class = status
    color = "var(--success)" if status == "success" else "var(--error)"
    
    st.markdown(f"""
        <div class="status-card {color_class}">
            <span class="status-card-icon">{icon}</span>
            <div>
                <p class="status-card-title" style="color: {color};">{title}</p>
                <p class="status-card-desc">{description}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_info_grid(items: list) -> None:
    """Render info items in a grid."""
    html_parts = ['<div class="info-grid">']
    for label, value in items:
        html_parts.append(
            f'<div class="info-item">'
            f'<div class="info-item-label">{label}</div>'
            f'<div class="info-item-value">{value}</div>'
            f'</div>'
        )
    html_parts.append("</div>")
    html = "\n".join(html_parts)

    # st.html renders raw HTML reliably on newer Streamlit versions; fallback keeps older support
    try:
        st.html(html)
    except Exception:
        st.markdown(html, unsafe_allow_html=True)
