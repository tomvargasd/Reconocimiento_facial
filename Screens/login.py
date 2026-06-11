"""
login.py — Pantalla de inicio de sesión.

Valida las credenciales del usuario contra la base de datos SQLite.
Al autenticarse exitosamente navega a IndexScreen.

Características visuales:
    - Diseño centrado con card dark mode.
    - Barra de acento superior.
    - Highlight de foco en campos.
    - Mensajes de error inline sin popups.
    - Soporte para tecla Enter.
"""
import tkinter as tk
from Configs.settings import THEME, FONTS, APP_NAME


class LoginScreen(tk.Frame):
    """
    Frame de inicio de sesión con diseño premium dark mode.

    Hereda de tk.Frame y vive dentro del contenedor principal de App.
    Usa tkraise() para mostrarse/ocultarse sin ser destruido.
    """

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la interfaz
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye todos los widgets de la pantalla de login."""
        self.configure(bg=THEME["bg_dark"])

        # Spacers para centrado vertical
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Card central ────────────────────────────────────
        outer = tk.Frame(self, bg=THEME["border"], padx=1, pady=1)
        outer.grid(row=1, column=0)

        card = tk.Frame(outer, bg=THEME["bg_surface"])
        card.pack(fill="both", expand=True)

        # Barra de acento superior
        tk.Frame(card, bg=THEME["accent"], height=4).pack(fill="x", side="top")

        inner = tk.Frame(card, bg=THEME["bg_surface"], padx=56, pady=48)
        inner.pack(fill="both", expand=True)

        # ── Logo / Título ────────────────────────────────────
        logo_frame = tk.Frame(inner, bg=THEME["bg_surface"])
        logo_frame.pack(pady=(0, 36))

        tk.Label(
            logo_frame, text="👁",
            font=("Segoe UI Emoji", 52),
            bg=THEME["bg_surface"], fg=THEME["accent"]
        ).pack()

        tk.Label(
            logo_frame, text=APP_NAME,
            font=FONTS["app_title"],
            bg=THEME["bg_surface"], fg=THEME["text_primary"]
        ).pack(pady=(6, 0))

        tk.Label(
            logo_frame, text="Inicie sesión para continuar",
            font=FONTS["small"],
            bg=THEME["bg_surface"], fg=THEME["text_muted"]
        ).pack(pady=(4, 0))

        # ── Campos de entrada ────────────────────────────────
        self.user_entry = self._make_field(inner, "USUARIO")
        self.password_entry = self._make_field(inner, "CONTRASEÑA", show="•")

        # ── Mensaje de error ─────────────────────────────────
        self.error_label = tk.Label(
            inner, text="",
            font=FONTS["small"],
            bg=THEME["bg_surface"], fg=THEME["danger"]
        )
        self.error_label.pack(pady=(0, 8))

        # ── Botón de login ───────────────────────────────────
        self._login_btn = tk.Button(
            inner, text="Iniciar Sesión",
            font=FONTS["button"],
            bg=THEME["accent"], fg=THEME["text_primary"],
            activebackground=THEME["accent_hover"],
            activeforeground=THEME["text_primary"],
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=13,
            command=self._on_login
        )
        self._login_btn.pack(fill="x", pady=(4, 0))
        self._login_btn.bind("<Enter>", lambda e: self._login_btn.configure(bg=THEME["accent_hover"]))
        self._login_btn.bind("<Leave>", lambda e: self._login_btn.configure(bg=THEME["accent"]))

    def _make_field(self, parent: tk.Widget, label: str, show: str = "") -> tk.Entry:
        """
        Crea un campo de entrada estilizado con etiqueta y borde dinámico.

        Args:
            parent: Widget padre.
            label:  Texto de la etiqueta (se muestra en mayúsculas).
            show:   Carácter de sustitución (p.ej. "•" para contraseñas).

        Returns:
            El widget Entry creado.
        """
        frame = tk.Frame(parent, bg=THEME["bg_surface"])
        frame.pack(fill="x", pady=(0, 18))

        tk.Label(
            frame, text=label,
            font=FONTS["small_bold"],
            bg=THEME["bg_surface"], fg=THEME["text_secondary"]
        ).pack(anchor="w")

        # Borde con estado (cambia de color en foco)
        border_frame = tk.Frame(frame, bg=THEME["border"], pady=1, padx=1)
        border_frame.pack(fill="x", pady=(5, 0))

        inner = tk.Frame(border_frame, bg=THEME["bg_input"])
        inner.pack(fill="x")

        entry = tk.Entry(
            inner,
            font=FONTS["body"],
            bg=THEME["bg_input"], fg=THEME["text_primary"],
            insertbackground=THEME["text_primary"],
            relief="flat", bd=8, show=show
        )
        entry.pack(fill="x")

        # Efecto de foco en el borde
        entry.bind("<FocusIn>",  lambda e: border_frame.configure(bg=THEME["accent"]))
        entry.bind("<FocusOut>", lambda e: border_frame.configure(bg=THEME["border"]))

        return entry

    # ──────────────────────────────────────────────────────────
    # Lógica
    # ──────────────────────────────────────────────────────────

    def _on_login(self) -> None:
        """Valida las credenciales y navega al panel principal si son correctas."""
        username = self.user_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self._show_error("Por favor, complete todos los campos.")
            return

        from Configs.database import verificar_credenciales
        user = verificar_credenciales(username, password)

        if user:
            self.error_label.configure(text="")
            self.app.current_user = dict(user)
            # Limpiar campos antes de navegar
            self.user_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            self.app.show_frame("IndexScreen")
        else:
            self._show_error("Usuario o contraseña incorrectos.")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()

    def _show_error(self, message: str) -> None:
        """Muestra un mensaje de error debajo de los campos."""
        self.error_label.configure(text=f"⚠  {message}")

    # ──────────────────────────────────────────────────────────
    # Ciclo de vida del frame
    # ──────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """
        Llamado por App.show_frame() cada vez que esta pantalla se hace visible.
        Vincula la tecla Enter y enfoca el campo de usuario.
        """
        self.app.bind("<Return>", lambda e: self._on_login())
        self.user_entry.focus_set()
