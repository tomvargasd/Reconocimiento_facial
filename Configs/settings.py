"""
settings.py — Configuraciones globales de la aplicación.

Contiene rutas del sistema, constantes de la aplicación, tema visual
(paleta de colores dark mode) y configuraciones de fuentes.
"""
from pathlib import Path

# ══════════════════════════════════════════════════════════
# Rutas del proyecto
# ══════════════════════════════════════════════════════════
BASE_DIR: Path = Path(__file__).parent.parent   # .../Reconocimiento_facial/
MODULES_DIR: Path = BASE_DIR / "Modulos"        # Carpeta de módulos
DB_PATH: Path = BASE_DIR / "Configs" / "app_data.db"  # BD de la app Tkinter

# ══════════════════════════════════════════════════════════
# Información de la aplicación
# ══════════════════════════════════════════════════════════
APP_NAME: str = "Sistema de Reconocimiento"
APP_VERSION: str = "1.0.0"
WINDOW_SIZE: str = "1150x720"
WINDOW_MIN_SIZE: tuple = (950, 620)

# ══════════════════════════════════════════════════════════
# Configuración de puertos
# ══════════════════════════════════════════════════════════
DEFAULT_PORT_START: int = 5000
PORT_SCAN_RANGE: int = 50   # Intentar hasta N puertos antes de fallar

# ══════════════════════════════════════════════════════════
# Tema visual — Dark Mode
# ══════════════════════════════════════════════════════════
THEME: dict = {
    # ── Fondos ────────────────────────────────────────────
    "bg_dark":         "#0d0d1a",    # Fondo principal (muy oscuro)
    "bg_surface":      "#141428",    # Superficie de cards / panels
    "bg_card":         "#1a1a35",    # Card inactivo
    "bg_card_hover":   "#22224a",    # Card inactivo hover
    "bg_card_active":  "#0a3322",    # Card activo (verde oscuro)
    "bg_card_act_hov": "#0e4530",    # Card activo hover
    "bg_input":        "#0d0d20",    # Fondo de inputs
    "bg_header":       "#111124",    # Barra de navegación
    "bg_dialog":       "#1c1c38",    # Diálogos / tooltips

    # ── Acento principal (púrpura) ─────────────────────────
    "accent":          "#7c3aed",
    "accent_hover":    "#9f67ff",
    "accent_dim":      "#4c1d95",
    "accent_light":    "#ede9fe",

    # ── Estados ───────────────────────────────────────────
    "success":         "#10b981",
    "success_dark":    "#064e3b",
    "danger":          "#ef4444",
    "danger_dark":     "#450a0a",
    "warning":         "#f59e0b",
    "info":            "#3b82f6",
    "info_dark":       "#1e3a5f",

    # ── Texto ─────────────────────────────────────────────
    "text_primary":    "#f1f5f9",
    "text_secondary":  "#94a3b8",
    "text_muted":      "#475569",
    "text_success":    "#34d399",
    "text_danger":     "#f87171",
    "text_warning":    "#fbbf24",
    "text_info":       "#60a5fa",

    # ── Bordes ────────────────────────────────────────────
    "border":          "#2d2d5a",
    "border_active":   "#10b981",
    "border_accent":   "#7c3aed",
    "border_light":    "#3d3d6b",
}

# ══════════════════════════════════════════════════════════
# Fuentes (Segoe UI disponible en Windows)
# ══════════════════════════════════════════════════════════
FONTS: dict = {
    "app_title":   ("Segoe UI", 26, "bold"),
    "title":       ("Segoe UI", 20, "bold"),
    "heading":     ("Segoe UI", 15, "bold"),
    "subheading":  ("Segoe UI", 12, "bold"),
    "body":        ("Segoe UI", 11),
    "body_bold":   ("Segoe UI", 11, "bold"),
    "small":       ("Segoe UI", 9),
    "small_bold":  ("Segoe UI", 9, "bold"),
    "button":      ("Segoe UI", 10, "bold"),
    "label":       ("Segoe UI", 10),
    "mono":        ("Consolas", 10),
    "card_title":  ("Segoe UI", 12, "bold"),
    "card_body":   ("Segoe UI", 9),
    "led":         ("Segoe UI", 9, "bold"),
    "nav":         ("Segoe UI", 10),
}
