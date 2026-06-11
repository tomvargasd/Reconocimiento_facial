"""
register.py — Pantalla de registro de nuevos usuarios.

Permite a un administrador registrar una nueva cuenta de usuario en el sistema SQLite.
Incluye validación en tiempo real y visuales acordes al tema premium.
"""
import tkinter as tk
from Configs.settings import THEME, FONTS
from Configs import database


class RegisterScreen(tk.Frame):
    """
    Frame para registrar nuevos usuarios del sistema.
    Accesible una vez autenticado, como función administrativa.
    """

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la interfaz
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye el header de navegación y el formulario de registro."""
        self._build_header()

        # Contenedor principal para centrar el formulario
        outer = tk.Frame(self, bg=THEME["bg_dark"])
        outer.pack(fill="both", expand=True)

        # Spacers para centrado
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Card del Formulario
        card_outer = tk.Frame(outer, bg=THEME["border"], padx=1, pady=1)
        card_outer.grid(row=1, column=0)

        card = tk.Frame(card_outer, bg=THEME["bg_surface"])
        card.pack(fill="both", expand=True)

        # Barra decorativa de acento
        tk.Frame(card, bg=THEME["accent"], height=3).pack(fill="x")

        inner = tk.Frame(card, bg=THEME["bg_surface"], padx=45, pady=35)
        inner.pack(fill="both", expand=True)

        tk.Label(
            inner, text="Crear Cuenta Nueva",
            font=FONTS["title"],
            bg=THEME["bg_surface"], fg=THEME["text_primary"]
        ).pack(anchor="w", pady=(0, 20))

        # ── Campos del formulario ─────────────────────────────
        self.nombre_entry = self._make_field(inner, "NOMBRE COMPLETO")
        self.user_entry = self._make_field(inner, "USUARIO")
        self.password_entry = self._make_field(inner, "CONTRASEÑA", show="•")
        self.confirm_entry = self._make_field(inner, "CONFIRMAR CONTRASEÑA", show="•")

        # ── Mensaje de error / éxito ──────────────────────────
        self.feedback_label = tk.Label(
            inner, text="",
            font=FONTS["small"],
            bg=THEME["bg_surface"]
        )
        self.feedback_label.pack(pady=(0, 10))

        # ── Botones de acción ─────────────────────────────────
        btn_row = tk.Frame(inner, bg=THEME["bg_surface"])
        btn_row.pack(fill="x", pady=(10, 0))

        # Cancelar
        cancel_btn = tk.Button(
            btn_row, text="Cancelar",
            font=FONTS["button"],
            bg=THEME["bg_card"], fg=THEME["text_primary"],
            activebackground=THEME["bg_card_hover"], activeforeground=THEME["text_primary"],
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=10,
            command=self._on_cancel
        )
        cancel_btn.pack(side="left")
        cancel_btn.bind("<Enter>", lambda e: cancel_btn.configure(bg=THEME["bg_card_hover"]))
        cancel_btn.bind("<Leave>", lambda e: cancel_btn.configure(bg=THEME["bg_card"]))

        # Registrar
        self.register_btn = tk.Button(
            btn_row, text="👤  Registrar Usuario",
            font=FONTS["button"],
            bg=THEME["accent"], fg="#ffffff",
            activebackground=THEME["accent_hover"], activeforeground="#ffffff",
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=10,
            command=self._on_register
        )
        self.register_btn.pack(side="right")
        self.register_btn.bind("<Enter>", lambda e: self.register_btn.configure(bg=THEME["accent_hover"]))
        self.register_btn.bind("<Leave>", lambda e: self.register_btn.configure(bg=THEME["accent"]))

    def _build_header(self) -> None:
        """Construye la barra de navegación superior."""
        header = tk.Frame(self, bg=THEME["bg_header"])
        header.pack(fill="x", side="top")
        tk.Frame(header, bg=THEME["accent"], height=3).pack(fill="x")

        nav = tk.Frame(header, bg=THEME["bg_header"])
        nav.pack(fill="x", padx=20, pady=14)

        tk.Label(nav, text="➕  Registro de usuarios",
                 font=FONTS["heading"],
                 bg=THEME["bg_header"], fg=THEME["text_primary"]).pack(side="left")

        right = tk.Frame(nav, bg=THEME["bg_header"])
        right.pack(side="right")

        self._nav_btn(right, "⬅  Módulos", "IndexScreen")
        self._nav_btn(right, "👤  Perfil", "ProfileScreen")

    def _nav_btn(self, parent: tk.Widget, text: str, target: str) -> None:
        btn = tk.Button(
            parent, text=text,
            font=FONTS["nav"],
            bg=THEME["bg_surface"], fg=THEME["text_primary"],
            activebackground=THEME["accent"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2", padx=12, pady=7,
            command=lambda t=target: self.app.show_frame(t)
        )
        btn.pack(side="left", padx=4)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=THEME["accent"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=THEME["bg_surface"]))

    def _make_field(self, parent: tk.Widget, label: str, show: str = "") -> tk.Entry:
        """Crea un campo de entrada estilizado."""
        frame = tk.Frame(parent, bg=THEME["bg_surface"])
        frame.pack(fill="x", pady=(0, 14))

        tk.Label(
            frame, text=label,
            font=FONTS["small_bold"],
            bg=THEME["bg_surface"], fg=THEME["text_secondary"]
        ).pack(anchor="w")

        border_frame = tk.Frame(frame, bg=THEME["border"], pady=1, padx=1)
        border_frame.pack(fill="x", pady=(4, 0))

        inner = tk.Frame(border_frame, bg=THEME["bg_input"])
        inner.pack(fill="x")

        entry = tk.Entry(
            inner,
            font=FONTS["body"],
            bg=THEME["bg_input"], fg=THEME["text_primary"],
            insertbackground=THEME["text_primary"],
            relief="flat", bd=6, show=show
        )
        entry.pack(fill="x")

        # Focus effects
        entry.bind("<FocusIn>", lambda e: border_frame.configure(bg=THEME["accent"]))
        entry.bind("<FocusOut>", lambda e: border_frame.configure(bg=THEME["border"]))

        return entry

    # ──────────────────────────────────────────────────────────
    # Lógica de Registro
    # ──────────────────────────────────────────────────────────

    def _on_register(self) -> None:
        """Valida y procesa el registro en la base de datos."""
        nombre = self.nombre_entry.get().strip()
        username = self.user_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not username or not password:
            self._show_feedback("Usuario y contraseña son obligatorios.", error=True)
            return

        if len(password) < 4:
            self._show_feedback("La contraseña debe tener al menos 4 caracteres.", error=True)
            return

        if password != confirm:
            self._show_feedback("Las contraseñas no coinciden.", error=True)
            return

        # Intentar insertar en base de datos
        success, msg = database.registrar_usuario(username, password, nombre)

        if success:
            self._show_feedback("✓ Usuario registrado correctamente.", error=False)
            self._clear_fields()
            # Navegar de vuelta al listado o panel después de un breve delay
            self.after(1200, lambda: self.app.show_frame("IndexScreen"))
        else:
            self._show_feedback(msg, error=True)

    def _on_cancel(self) -> None:
        """Limpia los campos y regresa a la pantalla anterior."""
        self._clear_fields()
        self.app.show_frame("IndexScreen")

    def _show_feedback(self, message: str, error: bool = False) -> None:
        color = THEME["danger"] if error else THEME["success"]
        prefix = "⚠  " if error else ""
        self.feedback_label.configure(text=f"{prefix}{message}", fg=color)

    def _clear_fields(self) -> None:
        self.nombre_entry.delete(0, tk.END)
        self.user_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.confirm_entry.delete(0, tk.END)
        self.feedback_label.configure(text="")

    # ──────────────────────────────────────────────────────────
    # Ciclo de vida
    # ──────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Llamado cuando la pantalla se hace visible."""
        self._clear_fields()
        self.nombre_entry.focus_set()
