"""
index.py — Panel principal de módulos.

Descubre dinámicamente los módulos disponibles en la carpeta Modulos/
y los presenta como cards interactivas que permiten iniciar y detener
servicios web (Flask/FastAPI) en segundo plano.

Clases:
    ModuleCard:  Widget card individual para un módulo/servicio.
    IndexScreen: Frame principal con la grilla de cards.
"""
import json
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Optional

from Configs.settings import THEME, FONTS, APP_NAME, MODULES_DIR


# ══════════════════════════════════════════════════════════
# ModuleCard
# ══════════════════════════════════════════════════════════

class ModuleCard(tk.Frame):
    """
    Widget card que representa un módulo/servicio web.

    Muestra:
        - Ícono y nombre del módulo.
        - Indicador LED de estado (Activo/Inactivo).
        - Puerto asignado cuando está activo.
        - Botón "Acceder al módulo" (solo cuando está activo).

    Al hacer clic en la card (fuera del botón de acceso) abre
    un diálogo de confirmación para iniciar o detener el servicio.
    """

    def __init__(self, parent: tk.Widget, app: tk.Tk, module_info: dict) -> None:
        super().__init__(parent, bg=THEME["bg_card"], relief="flat", bd=0, cursor="hand2")
        self.app = app
        self.module_info = module_info
        self.module_id: str = module_info["id"]
        self._is_tkinter: bool = module_info.get("type") == "tkinter"
        self._active: bool = self._is_tkinter
        self._build_ui()
        self._bind_events()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye todos los widgets internos del card."""
        # Barra lateral de estado (cambia de color según estado)
        self.status_bar = tk.Frame(self, bg=THEME["border"], width=5)
        self.status_bar.pack(side="left", fill="y")

        # Contenido principal
        content = tk.Frame(self, bg=THEME["bg_card"], padx=16, pady=14)
        content.pack(fill="both", expand=True)

        # ── Fila superior: ícono + info + LED ───────────────
        top_row = tk.Frame(content, bg=THEME["bg_card"])
        top_row.pack(fill="x")

        # Ícono del módulo
        self.icon_label = tk.Label(
            top_row,
            text=self.module_info.get("icono", "🔷"),
            font=("Segoe UI Emoji", 32),
            bg=THEME["bg_card"]
        )
        self.icon_label.pack(side="left", padx=(0, 14))

        # Nombre y descripción
        info_frame = tk.Frame(top_row, bg=THEME["bg_card"])
        info_frame.pack(side="left", fill="both", expand=True)

        self.name_label = tk.Label(
            info_frame,
            text=self.module_info["nombre"],
            font=FONTS["card_title"],
            bg=THEME["bg_card"], fg=THEME["text_primary"],
            anchor="w"
        )
        self.name_label.pack(fill="x")

        desc = self.module_info.get("descripcion", "")
        if desc:
            self.desc_label = tk.Label(
                info_frame,
                text=desc[:72] + ("…" if len(desc) > 72 else ""),
                font=FONTS["card_body"],
                bg=THEME["bg_card"], fg=THEME["text_secondary"],
                anchor="w", wraplength=200, justify="left"
            )
            self.desc_label.pack(fill="x", pady=(2, 0))

        # Indicador LED (derecha superior)
        led_group = tk.Frame(top_row, bg=THEME["bg_card"])
        led_group.pack(side="right", anchor="n", pady=4)

        self.led_canvas = tk.Canvas(
            led_group, width=14, height=14,
            bg=THEME["bg_card"], highlightthickness=0
        )
        self.led_canvas.pack(side="left")
        self._led = self.led_canvas.create_oval(2, 2, 12, 12,
                                                 fill=THEME["danger"],
                                                 outline="")

        self.status_label = tk.Label(
            led_group, text="Inactivo",
            font=FONTS["led"],
            bg=THEME["bg_card"], fg=THEME["text_muted"]
        )
        self.status_label.pack(side="left", padx=(5, 0))

        # ── Separador ────────────────────────────────────────
        tk.Frame(content, bg=THEME["border"], height=1).pack(fill="x", pady=(12, 8))

        # ── Fila inferior: puerto + botón acceso ─────────────
        bottom_row = tk.Frame(content, bg=THEME["bg_card"])
        bottom_row.pack(fill="x")

        if self._is_tkinter:
            self.port_label = tk.Label(
                bottom_row, text="Módulo nativo",
                font=FONTS["small"],
                bg=THEME["bg_card"], fg=THEME["text_success"]
            )
            self.port_label.pack(side="left")

            screens = self.module_info.get("screens", [])
            first_screen = screens[0] if screens else "VehicleProcessingScreen"
            self.access_btn = tk.Button(
                bottom_row, text="▶  Abrir módulo",
                font=FONTS["small_bold"],
                bg=THEME["success"], fg="#ffffff",
                activebackground="#0d9668", activeforeground="#fff",
                relief="flat", bd=0, cursor="hand2",
                padx=10, pady=5,
                command=lambda s=first_screen: self._open_tkinter_screen(s)
            )
            self.access_btn.pack(side="right")
        else:
            self.port_label = tk.Label(
                bottom_row, text="Puerto: —",
                font=FONTS["small"],
                bg=THEME["bg_card"], fg=THEME["text_muted"]
            )
            self.port_label.pack(side="left")

            self.access_btn = tk.Button(
                bottom_row, text="▶  Acceder al módulo",
                font=FONTS["small_bold"],
                bg=THEME["success"], fg="#ffffff",
                activebackground="#0d9668", activeforeground="#fff",
                relief="flat", bd=0, cursor="hand2",
                padx=10, pady=5,
                state="disabled",
                command=self._open_browser
            )
            self.access_btn.pack(side="right")

    def _bind_events(self) -> None:
        """Vincula eventos de clic y hover a todos los sub-widgets del card."""
        self._bind_to_subtree(self)

    def _bind_to_subtree(self, widget: tk.Widget) -> None:
        """Aplica bindings recursivamente, omitiendo botones para no interferir."""
        if not isinstance(widget, tk.Button):
            widget.bind("<Button-1>", self._on_card_click)
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            self._bind_to_subtree(child)

    # ──────────────────────────────────────────────────────────
    # Eventos
    # ──────────────────────────────────────────────────────────

    def _on_enter(self, event=None) -> None:
        """Efecto hover al pasar el mouse sobre el card."""
        bg = THEME["bg_card_act_hov"] if self._active else THEME["bg_card_hover"]
        self._apply_bg(self, bg)

    def _on_leave(self, event=None) -> None:
        """Restaura el color al salir del hover."""
        bg = THEME["bg_card_active"] if self._active else THEME["bg_card"]
        self._apply_bg(self, bg)

    def _apply_bg(self, widget: tk.Widget, color: str) -> None:
        """Aplica un color de fondo recursivamente (excepto canvas y botones especiales)."""
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._apply_bg(child, color)
        # Restaurar elementos fijos
        self.status_bar.configure(bg=THEME["success"] if self._active else THEME["border"])
        self.led_canvas.configure(bg=color)

    def _on_card_click(self, event=None) -> None:
        """Lógica de clic: alterna entre iniciar y detener el servicio."""
        if self._is_tkinter:
            screens = self.module_info.get("screens", [])
            target = screens[0] if screens else "VehicleProcessingScreen"
            self._open_tkinter_screen(target)
        elif self._active:
            self._confirm_stop()
        else:
            self._confirm_start()

    def _confirm_start(self) -> None:
        answer = messagebox.askyesno(
            "Activar módulo",
            f"¿Desea iniciar el módulo\n«{self.module_info['nombre']}»?",
            icon="question", parent=self.app
        )
        if answer:
            self._start_service()

    def _confirm_stop(self) -> None:
        answer = messagebox.askyesno(
            "Desactivar módulo",
            f"¿Desea detener el módulo\n«{self.module_info['nombre']}»?",
            icon="warning", parent=self.app
        )
        if answer:
            self._stop_service()

    def _start_service(self) -> None:
        ok, port, err = self.app.service_manager.start_service(self.module_info)
        if ok:
            self.set_active(True, port)
        else:
            messagebox.showerror(
                "Error al iniciar",
                f"No se pudo iniciar el módulo:\n\n{err}",
                parent=self.app
            )

    def _stop_service(self) -> None:
        self.app.service_manager.stop_service(self.module_id)
        self.set_active(False)

    def _open_browser(self) -> None:
        """Abre el módulo en el navegador predeterminado del sistema."""
        port = self.app.service_manager.get_port(self.module_id)
        if port:
            webbrowser.open(f"http://localhost:{port}")

    def _open_tkinter_screen(self, screen_name: str) -> None:
        """Navega a una pantalla Tkinter del módulo nativo."""
        self.app.show_frame(screen_name)

    # ──────────────────────────────────────────────────────────
    # Estado visual
    # ──────────────────────────────────────────────────────────

    def set_active(self, active: bool, port: Optional[int] = None) -> None:
        """
        Actualiza la apariencia completa del card según el estado del servicio.

        Args:
            active: True si el servicio está corriendo.
            port:   Puerto asignado (solo relevante cuando active=True).
        """
        self._active = active

        if self._is_tkinter:
            bg = THEME["bg_card_active"]
            self.status_bar.configure(bg=THEME["success"])
            self.led_canvas.itemconfig(self._led, fill=THEME["success"])
            self.status_label.configure(text="Nativo", fg=THEME["text_success"])
            self.access_btn.configure(state="normal")
            self.port_label.configure(text="Módulo nativo", fg=THEME["text_success"])
            self._apply_bg(self, bg)
        elif active:
            bg = THEME["bg_card_active"]
            self.status_bar.configure(bg=THEME["success"])
            self.led_canvas.itemconfig(self._led, fill=THEME["success"])
            self.status_label.configure(text="Activo", fg=THEME["text_success"])
            self.access_btn.configure(state="normal")
            port_text = f"Puerto: {port}" if port else "Puerto: activo"
            self.port_label.configure(text=port_text, fg=THEME["text_success"])
            self._apply_bg(self, bg)
        else:
            bg = THEME["bg_card"]
            self.status_bar.configure(bg=THEME["border"])
            self.led_canvas.itemconfig(self._led, fill=THEME["danger"])
            self.status_label.configure(text="Inactivo", fg=THEME["text_muted"])
            self.access_btn.configure(state="disabled")
            self.port_label.configure(text="Puerto: —", fg=THEME["text_muted"])
            self._apply_bg(self, bg)

    def refresh_status(self) -> None:
        """Sincroniza el estado visual con el estado real del ServiceManager."""
        if self._is_tkinter:
            return
        running = self.app.service_manager.is_running(self.module_id)
        port = self.app.service_manager.get_port(self.module_id)
        if running != self._active:
            self.set_active(running, port)


# ══════════════════════════════════════════════════════════
# IndexScreen
# ══════════════════════════════════════════════════════════

class IndexScreen(tk.Frame):
    """
    Panel principal de la aplicación.

    Descubre módulos en Modulos/ y los renderiza como ModuleCard.
    Refresca el estado de los servicios cada 5 segundos via after().
    """

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app
        self.cards: dict[str, ModuleCard] = {}
        self._refresh_job = None
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye el header de navegación y el área de cards."""
        self._build_header()
        self._build_content()

    def _build_header(self) -> None:
        """Construye la barra de navegación superior."""
        header = tk.Frame(self, bg=THEME["bg_header"])
        header.pack(fill="x", side="top")

        # Línea de acento
        tk.Frame(header, bg=THEME["accent"], height=3).pack(fill="x")

        nav = tk.Frame(header, bg=THEME["bg_header"])
        nav.pack(fill="x", padx=20, pady=14)

        # Logo + Título
        brand = tk.Frame(nav, bg=THEME["bg_header"])
        brand.pack(side="left")

        tk.Label(brand, text="👁 ", font=("Segoe UI Emoji", 18),
                 bg=THEME["bg_header"], fg=THEME["accent"]).pack(side="left")
        tk.Label(brand, text=APP_NAME,
                 font=FONTS["heading"],
                 bg=THEME["bg_header"], fg=THEME["text_primary"]).pack(side="left")

        # Controles de la derecha
        right = tk.Frame(nav, bg=THEME["bg_header"])
        right.pack(side="right")

        self.user_label = tk.Label(
            right, text="",
            font=FONTS["nav"],
            bg=THEME["bg_header"], fg=THEME["text_secondary"]
        )
        self.user_label.pack(side="left", padx=(0, 20))

        self._nav_btn(right, "👤  Perfil", "ProfileScreen")
        self._nav_btn(right, "➕  Registrar usuario", "RegisterScreen")

        # Botón cerrar sesión (estilo diferente)
        logout_btn = tk.Button(
            right, text="⏻  Cerrar sesión",
            font=FONTS["button"],
            bg=THEME["danger_dark"], fg=THEME["text_danger"],
            activebackground=THEME["danger"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=self.app.logout
        )
        logout_btn.pack(side="left", padx=(12, 0))
        logout_btn.bind("<Enter>", lambda e: logout_btn.configure(bg=THEME["danger"], fg="#fff"))
        logout_btn.bind("<Leave>", lambda e: logout_btn.configure(bg=THEME["danger_dark"], fg=THEME["text_danger"]))

    def _nav_btn(self, parent: tk.Widget, text: str, target: str) -> tk.Button:
        """Crea un botón de navegación estilizado para el header."""
        btn = tk.Button(
            parent, text=text,
            font=FONTS["nav"],
            bg=THEME["bg_surface"], fg=THEME["text_primary"],
            activebackground=THEME["accent"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=lambda t=target: self.app.show_frame(t)
        )
        btn.pack(side="left", padx=4)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=THEME["accent"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=THEME["bg_surface"]))
        return btn

    def _build_content(self) -> None:
        """Construye el área de contenido con el título y la grilla scrollable."""
        content = tk.Frame(self, bg=THEME["bg_dark"])
        content.pack(fill="both", expand=True, padx=28, pady=24)

        # Encabezado de sección
        title_row = tk.Frame(content, bg=THEME["bg_dark"])
        title_row.pack(fill="x", pady=(0, 20))

        tk.Label(title_row, text="Módulos disponibles",
                 font=FONTS["title"],
                 bg=THEME["bg_dark"], fg=THEME["text_primary"]).pack(side="left")

        self.count_label = tk.Label(title_row, text="",
                                    font=FONTS["small"],
                                    bg=THEME["bg_dark"], fg=THEME["text_muted"])
        self.count_label.pack(side="left", padx=(14, 0), pady=(8, 0))

        # ── Canvas + Scrollbar para la grilla ────────────────
        canvas_frame = tk.Frame(content, bg=THEME["bg_dark"])
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=THEME["bg_dark"],
                                highlightthickness=0)

        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self.canvas.yview)

        self.grid_frame = tk.Frame(self.canvas, bg=THEME["bg_dark"])
        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all"))
        )

        self._canvas_win = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Hacer que el grid_frame ocupe el ancho del canvas
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._canvas_win, width=e.width)
        )

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Scroll con rueda del mouse
        self.bind_all("<MouseWheel>",
                      lambda e: self.canvas.yview_scroll(
                          -1 * (e.delta // 120), "units"))

    # ──────────────────────────────────────────────────────────
    # Lógica de descubrimiento de módulos
    # ──────────────────────────────────────────────────────────

    def _discover_modules(self) -> list:
        """
        Escanea la carpeta Modulos/ y retorna la lista de módulos encontrados.

        Para cada subdirectorio dentro de Modulos/:
            1. Si existe module_info.json, usa sus datos.
            2. Si no, usa valores por defecto basados en el nombre del directorio.
            3. Solo considera el directorio si contiene app.py (o el script especificado).

        Returns:
            Lista de diccionarios con la información de cada módulo.
        """
        modules = []
        if not MODULES_DIR.exists():
            return modules

        for idx, module_dir in enumerate(sorted(MODULES_DIR.iterdir())):
            if not module_dir.is_dir() or module_dir.name.startswith("."):
                continue

            info_file = module_dir / "module_info.json"

            if info_file.exists():
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                except (json.JSONDecodeError, OSError):
                    info = {}

                # Resolver ruta del directorio del módulo
                ruta = info.get("ruta_directorio", "")
                if ruta:
                    resolved = (module_dir / ruta).resolve() if not Path(ruta).is_absolute() else Path(ruta)
                    info["ruta_directorio"] = str(resolved)
                else:
                    info["ruta_directorio"] = str(module_dir)
            else:
                # Sin module_info.json: usar defaults
                info = {
                    "ruta_directorio": str(module_dir),
                    "script_entry": "app.py",
                    "puerto_default": 5000 + idx,
                }

            # Verificar que el script de entrada exista (excepto módulos nativos Tkinter)
            if info.get("type") != "tkinter":
                ruta_dir = Path(info["ruta_directorio"])
                script = ruta_dir / info.get("script_entry", "app.py")
                if not script.exists():
                    continue

            # Completar con defaults
            info.setdefault("nombre",        module_dir.name.replace("_", " ").title())
            info.setdefault("descripcion",   "")
            info.setdefault("icono",         "🔷")
            info.setdefault("puerto_default", 5000 + idx)
            info["id"] = module_dir.name   # ID único basado en nombre de carpeta

            modules.append(info)

        return modules

    def _render_cards(self, modules: list) -> None:
        """
        Limpia y re-renderiza la grilla de cards.

        Args:
            modules: Lista de diccionarios de módulos descubiertos.
        """
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.cards.clear()

        if not modules:
            self._render_empty_state()
            return

        COLS = 3
        for col in range(COLS):
            self.grid_frame.columnconfigure(col, weight=1)

        for i, mod in enumerate(modules):
            row, col = divmod(i, COLS)
            card = ModuleCard(self.grid_frame, self.app, mod)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.cards[mod["id"]] = card

            # Restaurar estado si el servicio ya estaba activo
            if self.app.service_manager.is_running(mod["id"]):
                port = self.app.service_manager.get_port(mod["id"])
                card.set_active(True, port)

    def _render_empty_state(self) -> None:
        """Muestra un estado vacío cuando no hay módulos."""
        empty = tk.Frame(self.grid_frame, bg=THEME["bg_dark"])
        empty.pack(pady=80)

        tk.Label(empty, text="📭",
                 font=("Segoe UI Emoji", 52),
                 bg=THEME["bg_dark"]).pack()

        tk.Label(empty, text="No se encontraron módulos",
                 font=FONTS["heading"],
                 bg=THEME["bg_dark"], fg=THEME["text_secondary"]).pack(pady=(12, 0))

        tk.Label(empty,
                 text=f"Coloque sus módulos en la carpeta  '{MODULES_DIR.name}/'",
                 font=FONTS["body"],
                 bg=THEME["bg_dark"], fg=THEME["text_muted"]).pack(pady=(6, 0))

    # ──────────────────────────────────────────────────────────
    # Polling de estado
    # ──────────────────────────────────────────────────────────

    def _start_status_polling(self) -> None:
        """Inicia el ciclo de refresco automático del estado cada 5 segundos."""
        self._poll_status()

    def _poll_status(self) -> None:
        """Refresca el estado visual de cada card y reprograma la próxima consulta."""
        for card in self.cards.values():
            try:
                card.refresh_status()
            except tk.TclError:
                pass  # El widget puede haber sido destruido

        self._refresh_job = self.after(5000, self._poll_status)

    def _stop_status_polling(self) -> None:
        """Cancela el ciclo de refresco si está activo."""
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

    # ──────────────────────────────────────────────────────────
    # Ciclo de vida
    # ──────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """
        Llamado por App.show_frame() cada vez que esta pantalla se hace visible.
        Actualiza el saludo del usuario y recarga los módulos.
        """
        # Actualizar saludo
        if self.app.current_user:
            name = (self.app.current_user.get("nombre_completo")
                    or self.app.current_user.get("username", ""))
            self.user_label.configure(text=f"👤  {name}")

        # Desvincula Enter del login
        try:
            self.app.unbind("<Return>")
        except Exception:
            pass

        # Descubrir y renderizar módulos
        modules = self._discover_modules()
        n = len(modules)
        self.count_label.configure(
            text=f"({n} módulo{'s' if n != 1 else ''})"
        )
        self._render_cards(modules)

        # Iniciar polling de estado
        self._stop_status_polling()
        self._start_status_polling()
