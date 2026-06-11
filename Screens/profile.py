"""
profile.py — Pantalla de perfil de usuario.

Permite al usuario actual ver y editar sus propios datos.
También muestra la lista completa de usuarios registrados
con opciones de editar y eliminar.

Clases:
    ProfileScreen: Frame principal de perfil y gestión de usuarios.
"""
import tkinter as tk
from tkinter import messagebox, ttk
from Configs.settings import THEME, FONTS
from Configs import database


class ProfileScreen(tk.Frame):
    """
    Frame de gestión de perfil y listado de usuarios del sistema.

    Secciones:
        1. Datos del usuario actual (editable).
        2. Lista de todos los usuarios con acciones de editar/eliminar.
    """

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye el header, la sección de perfil y la lista de usuarios."""
        self._build_header()

        # Área de contenido scrollable
        outer = tk.Frame(self, bg=THEME["bg_dark"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=THEME["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)

        self._scroll_frame = tk.Frame(canvas, bg=THEME["bg_dark"])
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        win = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Construir secciones dentro del frame scrollable
        self._build_own_profile_section(self._scroll_frame)
        tk.Frame(self._scroll_frame, bg=THEME["border"], height=1).pack(
            fill="x", padx=30, pady=24)
        self._build_user_list_section(self._scroll_frame)

    def _build_header(self) -> None:
        """Construye la barra de navegación superior."""
        header = tk.Frame(self, bg=THEME["bg_header"])
        header.pack(fill="x", side="top")
        tk.Frame(header, bg=THEME["accent"], height=3).pack(fill="x")

        nav = tk.Frame(header, bg=THEME["bg_header"])
        nav.pack(fill="x", padx=20, pady=14)

        tk.Label(nav, text="👤  Perfil de usuario",
                 font=FONTS["heading"],
                 bg=THEME["bg_header"], fg=THEME["text_primary"]).pack(side="left")

        right = tk.Frame(nav, bg=THEME["bg_header"])
        right.pack(side="right")

        self._nav_btn(right, "⬅  Módulos", "IndexScreen")
        self._nav_btn(right, "➕  Registrar usuario", "RegisterScreen")

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

    def _build_own_profile_section(self, parent: tk.Widget) -> None:
        """Sección para editar los datos del usuario actualmente autenticado."""
        wrapper = tk.Frame(parent, bg=THEME["bg_dark"], padx=30, pady=24)
        wrapper.pack(fill="x")

        # Card
        card = tk.Frame(wrapper, bg=THEME["bg_surface"])
        card.pack(fill="x")
        tk.Frame(card, bg=THEME["accent_dim"], height=3).pack(fill="x")

        body = tk.Frame(card, bg=THEME["bg_surface"], padx=24, pady=20)
        body.pack(fill="x")

        tk.Label(body, text="Mis datos",
                 font=FONTS["subheading"],
                 bg=THEME["bg_surface"], fg=THEME["text_primary"]).pack(anchor="w", pady=(0, 16))

        # Grid de campos
        fields_frame = tk.Frame(body, bg=THEME["bg_surface"])
        fields_frame.pack(fill="x")
        fields_frame.columnconfigure(0, weight=1)
        fields_frame.columnconfigure(1, weight=1)

        # Nombre completo
        tk.Label(fields_frame, text="NOMBRE COMPLETO",
                 font=FONTS["small_bold"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).grid(
            row=0, column=0, sticky="w", pady=(0, 5))

        self._nombre_entry = self._make_entry(fields_frame)
        self._nombre_entry.grid(row=1, column=0, sticky="ew", padx=(0, 16))

        # Usuario
        tk.Label(fields_frame, text="USUARIO",
                 font=FONTS["small_bold"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).grid(
            row=0, column=1, sticky="w", pady=(0, 5))

        self._username_entry = self._make_entry(fields_frame)
        self._username_entry.grid(row=1, column=1, sticky="ew")

        # Nueva contraseña (fila siguiente)
        tk.Label(fields_frame,
                 text="NUEVA CONTRASEÑA  (dejar vacío para no cambiar)",
                 font=FONTS["small_bold"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(16, 5))

        self._password_entry = self._make_entry(fields_frame, show="•")
        self._password_entry.grid(row=3, column=0, sticky="ew", padx=(0, 16))

        # Botón guardar + feedback
        save_frame = tk.Frame(fields_frame, bg=THEME["bg_surface"])
        save_frame.grid(row=3, column=1, sticky="ew")

        save_btn = tk.Button(
            save_frame, text="💾  Guardar cambios",
            font=FONTS["button"],
            bg=THEME["accent"], fg="#fff",
            activebackground=THEME["accent_hover"],
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=9,
            command=self._save_profile
        )
        save_btn.pack(side="left")
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=THEME["accent_hover"]))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=THEME["accent"]))

        self._profile_feedback = tk.Label(
            save_frame, text="",
            font=FONTS["small"],
            bg=THEME["bg_surface"]
        )
        self._profile_feedback.pack(side="left", padx=(14, 0))

    def _build_user_list_section(self, parent: tk.Widget) -> None:
        """Sección con la lista de todos los usuarios registrados."""
        wrapper = tk.Frame(parent, bg=THEME["bg_dark"])
        wrapper.pack(fill="x", padx=30, pady=(0, 30))

        header_row = tk.Frame(wrapper, bg=THEME["bg_dark"])
        header_row.pack(fill="x", pady=(0, 14))

        tk.Label(header_row, text="Usuarios registrados",
                 font=FONTS["subheading"],
                 bg=THEME["bg_dark"], fg=THEME["text_primary"]).pack(side="left")

        # El contenedor de filas se re-crea en cada refresco
        self._user_rows_frame = tk.Frame(wrapper, bg=THEME["bg_dark"])
        self._user_rows_frame.pack(fill="x")

    # ──────────────────────────────────────────────────────────
    # Widgets de apoyo
    # ──────────────────────────────────────────────────────────

    def _make_entry(self, parent: tk.Widget, show: str = "") -> tk.Entry:
        """Crea un Entry con el estilo de la aplicación."""
        e = tk.Entry(
            parent, font=FONTS["body"],
            bg=THEME["bg_input"], fg=THEME["text_primary"],
            insertbackground=THEME["text_primary"],
            relief="flat", bd=8, show=show,
            highlightbackground=THEME["border"],
            highlightthickness=1,
            highlightcolor=THEME["accent"]
        )
        return e

    # ──────────────────────────────────────────────────────────
    # Lógica de perfil propio
    # ──────────────────────────────────────────────────────────

    def _save_profile(self) -> None:
        """Guarda los cambios del perfil del usuario autenticado."""
        if not self.app.current_user:
            return

        nombre   = self._nombre_entry.get().strip()
        username = self._username_entry.get().strip()
        password = self._password_entry.get()

        if not username:
            self._set_profile_feedback("El nombre de usuario no puede estar vacío.", error=True)
            return

        ok, msg = database.actualizar_usuario(
            self.app.current_user["id"], username, nombre, password
        )

        if ok:
            # Actualizar sesión en memoria
            self.app.current_user["username"] = username
            self.app.current_user["nombre_completo"] = nombre
            self._password_entry.delete(0, tk.END)
            self._set_profile_feedback("✓ Cambios guardados correctamente.")
            # Refrescar la lista para reflejar el cambio de nombre
            self._refresh_user_list()
        else:
            self._set_profile_feedback(msg, error=True)

    def _set_profile_feedback(self, msg: str, error: bool = False) -> None:
        color = THEME["danger"] if error else THEME["success"]
        self._profile_feedback.configure(text=msg, fg=color)

    # ──────────────────────────────────────────────────────────
    # Lista de usuarios
    # ──────────────────────────────────────────────────────────

    def _refresh_user_list(self) -> None:
        """Limpia y recarga la lista de usuarios desde la base de datos."""
        for widget in self._user_rows_frame.winfo_children():
            widget.destroy()

        users = database.listar_usuarios()
        current_id = self.app.current_user["id"] if self.app.current_user else -1

        # Cabecera de tabla
        header = tk.Frame(self._user_rows_frame, bg=THEME["bg_surface"],
                          padx=16, pady=10)
        header.pack(fill="x")

        for text, w in [("#", 3), ("Usuario", 16), ("Nombre completo", 26), ("Creado", 14)]:
            tk.Label(header, text=text,
                     font=FONTS["small_bold"],
                     bg=THEME["bg_surface"], fg=THEME["text_muted"],
                     width=w, anchor="w").pack(side="left")

        tk.Frame(self._user_rows_frame, bg=THEME["border"], height=1).pack(fill="x")

        for user in users:
            self._render_user_row(user, current_id)

        if not users:
            tk.Label(self._user_rows_frame, text="No hay usuarios registrados.",
                     font=FONTS["body"],
                     bg=THEME["bg_dark"], fg=THEME["text_muted"]).pack(pady=20)

    def _render_user_row(self, user: dict, current_id: int) -> None:
        """Renderiza una fila de la tabla de usuarios."""
        is_me = (user["id"] == current_id)
        bg = "#1a1a3e" if is_me else THEME["bg_surface"]

        row = tk.Frame(self._user_rows_frame, bg=bg, padx=16, pady=11)
        row.pack(fill="x", pady=1)

        # Borde izquierdo de acento para el usuario actual
        if is_me:
            tk.Frame(row, bg=THEME["accent"], width=4).pack(side="left", fill="y")

        data = tk.Frame(row, bg=bg)
        data.pack(side="left", fill="both", expand=True,
                  padx=(6 if is_me else 0, 0))

        tag = "  ★ tú" if is_me else ""
        fields = [
            (str(user["id"]),                                3),
            (f"{user['username']}{tag}",                    16),
            (user["nombre_completo"] or "—",                26),
            (str(user["created_at"])[:16],                  14),
        ]
        for text, w in fields:
            tk.Label(data, text=text,
                     font=FONTS["body_bold"] if is_me else FONTS["body"],
                     bg=bg,
                     fg=THEME["accent_light"] if is_me else THEME["text_primary"],
                     width=w, anchor="w").pack(side="left")

        # Botones de acción
        actions = tk.Frame(row, bg=bg)
        actions.pack(side="right")

        edit_btn = tk.Button(
            actions, text="✏  Editar",
            font=FONTS["small"],
            bg=THEME["info_dark"], fg=THEME["text_info"],
            activebackground=THEME["info"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=8, pady=5,
            command=lambda uid=user["id"]: self._open_edit_dialog(uid)
        )
        edit_btn.pack(side="left", padx=(0, 6))
        edit_btn.bind("<Enter>", lambda e, b=edit_btn: b.configure(bg=THEME["info"]))
        edit_btn.bind("<Leave>", lambda e, b=edit_btn: b.configure(bg=THEME["info_dark"]))

        if not is_me:
            del_btn = tk.Button(
                actions, text="🗑  Eliminar",
                font=FONTS["small"],
                bg=THEME["danger_dark"], fg=THEME["text_danger"],
                activebackground=THEME["danger"], activeforeground="#fff",
                relief="flat", bd=0, cursor="hand2",
                padx=8, pady=5,
                command=lambda uid=user["id"], un=user["username"]: self._delete_user(uid, un)
            )
            del_btn.pack(side="left")
            del_btn.bind("<Enter>", lambda e, b=del_btn: b.configure(bg=THEME["danger"], fg="#fff"))
            del_btn.bind("<Leave>", lambda e, b=del_btn: b.configure(bg=THEME["danger_dark"], fg=THEME["text_danger"]))

    # ──────────────────────────────────────────────────────────
    # Acciones de usuarios
    # ──────────────────────────────────────────────────────────

    def _open_edit_dialog(self, user_id: int) -> None:
        """Abre un diálogo modal para editar los datos de un usuario."""
        user = database.get_usuario_por_id(user_id)
        if not user:
            return

        dlg = tk.Toplevel(self.app)
        dlg.title(f"Editar — {user['username']}")
        dlg.configure(bg=THEME["bg_surface"])
        dlg.geometry("440x360")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.lift()

        # Barra de acento
        tk.Frame(dlg, bg=THEME["accent"], height=3).pack(fill="x")

        body = tk.Frame(dlg, bg=THEME["bg_surface"], padx=30, pady=24)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"Editar usuario  «{user['username']}»",
                 font=FONTS["heading"],
                 bg=THEME["bg_surface"], fg=THEME["text_primary"]).pack(anchor="w", pady=(0, 20))

        def make_field(lbl: str, default: str = "", show: str = "") -> tk.Entry:
            tk.Label(body, text=lbl.upper(),
                     font=FONTS["small_bold"],
                     bg=THEME["bg_surface"], fg=THEME["text_secondary"]).pack(anchor="w", pady=(10, 4))
            border = tk.Frame(body, bg=THEME["border"], pady=1, padx=1)
            border.pack(fill="x")
            inner = tk.Frame(border, bg=THEME["bg_input"])
            inner.pack(fill="x")
            e = tk.Entry(inner, font=FONTS["body"],
                         bg=THEME["bg_input"], fg=THEME["text_primary"],
                         insertbackground=THEME["text_primary"],
                         relief="flat", bd=6, show=show)
            e.pack(fill="x")
            e.insert(0, default)
            e.bind("<FocusIn>",  lambda ev: border.configure(bg=THEME["accent"]))
            e.bind("<FocusOut>", lambda ev: border.configure(bg=THEME["border"]))
            return e

        e_nombre   = make_field("Nombre completo", user.get("nombre_completo", ""))
        e_username = make_field("Usuario",          user["username"])
        e_pass     = make_field("Nueva contraseña (vacío = sin cambio)", show="•")

        feedback = tk.Label(body, text="", font=FONTS["small"],
                            bg=THEME["bg_surface"])
        feedback.pack(pady=(10, 0))

        def save_changes():
            ok, msg = database.actualizar_usuario(
                user_id,
                e_username.get().strip(),
                e_nombre.get().strip(),
                e_pass.get()
            )
            if ok:
                # Sincronizar sesión si el usuario editado es el actual
                if self.app.current_user and user_id == self.app.current_user["id"]:
                    self.app.current_user["username"]       = e_username.get().strip()
                    self.app.current_user["nombre_completo"] = e_nombre.get().strip()
                self._refresh_user_list()
                dlg.destroy()
            else:
                feedback.configure(text=f"✗  {msg}", fg=THEME["danger"])

        btn_row = tk.Frame(body, bg=THEME["bg_surface"])
        btn_row.pack(fill="x", pady=(20, 0))

        tk.Button(
            btn_row, text="Cancelar",
            font=FONTS["button"],
            bg=THEME["bg_card"], fg=THEME["text_primary"],
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=9,
            command=dlg.destroy
        ).pack(side="left")

        tk.Button(
            btn_row, text="💾  Guardar cambios",
            font=FONTS["button"],
            bg=THEME["accent"], fg="#fff",
            activebackground=THEME["accent_hover"],
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=9,
            command=save_changes
        ).pack(side="right")

    def _delete_user(self, user_id: int, username: str) -> None:
        """Solicita confirmación y elimina al usuario seleccionado."""
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Está seguro de que desea eliminar al usuario «{username}»?\n\n"
            "Esta acción no se puede deshacer.",
            icon="warning", parent=self.app
        ):
            return

        ok, msg = database.eliminar_usuario(user_id)
        if ok:
            self._refresh_user_list()
        else:
            messagebox.showerror("Error", f"No se pudo eliminar el usuario:\n{msg}",
                                 parent=self.app)

    # ──────────────────────────────────────────────────────────
    # Ciclo de vida
    # ──────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Refresca todos los datos al hacerse visible la pantalla."""
        if self.app.current_user:
            self._nombre_entry.delete(0, tk.END)
            self._nombre_entry.insert(0, self.app.current_user.get("nombre_completo", ""))
            self._username_entry.delete(0, tk.END)
            self._username_entry.insert(0, self.app.current_user.get("username", ""))

        self._password_entry.delete(0, tk.END)
        self._set_profile_feedback("")
        self._refresh_user_list()
