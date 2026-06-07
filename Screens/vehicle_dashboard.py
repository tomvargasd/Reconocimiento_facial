import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from Configs.settings import THEME, FONTS
import Modulos.conteo_vehiculos.database as db

VEHICLE_ICONS = {
    'car':        '🚗',
    'motorcycle': '🏍️',
    'bus':        '🚌',
    'truck':      '🚚',
    'bicycle':    '🚲',
}

VEHICLE_LABELS = {
    'car':        'Autos',
    'motorcycle': 'Motos',
    'bus':        'Buses',
    'truck':      'Camiones',
    'bicycle':    'Bicicletas',
}

VEHICLE_ORDER = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']


class VehicleDashboardScreen(tk.Frame):

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app
        self._selected_video_id: Optional[int] = None
        self._build_ui()

    def _build_ui(self):
        self._build_header()

        main = tk.Frame(self, bg=THEME["bg_dark"])
        main.pack(fill="both", expand=True, padx=20, pady=12)

        main.grid_columnconfigure(0, weight=1, minsize=400)
        main.grid_columnconfigure(1, weight=1, minsize=400)
        main.grid_rowconfigure(0, weight=1)

        self._build_list_panel(main)
        self._build_detail_panel(main)

    def _build_header(self):
        header = tk.Frame(self, bg=THEME["bg_header"])
        header.pack(fill="x", side="top")

        tk.Frame(header, bg=THEME["accent"], height=3).pack(fill="x")

        nav = tk.Frame(header, bg=THEME["bg_header"])
        nav.pack(fill="x", padx=20, pady=12)

        back_btn = tk.Button(
            nav, text="←  Volver",
            font=FONTS["button"],
            bg=THEME["bg_surface"], fg=THEME["text_primary"],
            activebackground=THEME["accent"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=self._go_back
        )
        back_btn.pack(side="left")
        back_btn.bind("<Enter>", lambda e: back_btn.configure(bg=THEME["accent"]))
        back_btn.bind("<Leave>", lambda e: back_btn.configure(bg=THEME["bg_surface"]))

        tk.Label(nav, text="📊",
                 font=("Segoe UI Emoji", 20),
                 bg=THEME["bg_header"], fg=THEME["accent"]).pack(side="left", padx=(20, 8))

        tk.Label(nav, text="Dashboard — Conteo de Vehículos",
                 font=FONTS["heading"],
                 bg=THEME["bg_header"], fg=THEME["text_primary"]).pack(side="left")

        self._refresh_btn = tk.Button(
            nav, text="↻  Actualizar",
            font=FONTS["button"],
            bg=THEME["info_dark"], fg=THEME["text_info"],
            activebackground=THEME["info"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=self._refresh
        )
        self._refresh_btn.pack(side="right")
        self._refresh_btn.bind("<Enter>", lambda e: self._refresh_btn.configure(bg=THEME["info"], fg="#fff"))
        self._refresh_btn.bind("<Leave>", lambda e: self._refresh_btn.configure(bg=THEME["info_dark"], fg=THEME["text_info"]))

        go_proc_btn = tk.Button(
            nav, text="🚗  Ir a procesamiento",
            font=FONTS["button"],
            bg=THEME["success_dark"], fg=THEME["text_success"],
            activebackground=THEME["success"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=lambda: self.app.show_frame("VehicleProcessingScreen")
        )
        go_proc_btn.pack(side="right", padx=(0, 8))
        go_proc_btn.bind("<Enter>", lambda e: go_proc_btn.configure(bg=THEME["success"], fg="#fff"))
        go_proc_btn.bind("<Leave>", lambda e: go_proc_btn.configure(bg=THEME["success_dark"], fg=THEME["text_success"]))

    def _build_list_panel(self, parent):
        container = tk.Frame(parent, bg=THEME["bg_surface"],
                             highlightbackground=THEME["border"],
                             highlightthickness=1, relief="flat")
        container.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        inner = tk.Frame(container, bg=THEME["bg_surface"], padx=12, pady=12)
        inner.pack(fill="both", expand=True)

        header_row = tk.Frame(inner, bg=THEME["bg_surface"])
        header_row.pack(fill="x", pady=(0, 8))

        tk.Label(header_row, text="Videos procesados",
                 font=FONTS["subheading"],
                 bg=THEME["bg_surface"], fg=THEME["text_primary"]).pack(side="left")

        self._list_count_label = tk.Label(header_row, text="",
                                          font=FONTS["small"],
                                          bg=THEME["bg_surface"], fg=THEME["text_muted"])
        self._list_count_label.pack(side="left", padx=(10, 0))

        tree_frame = tk.Frame(inner, bg=THEME["bg_dark"])
        tree_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Vehicle.Treeview",
                        background=THEME["bg_card"],
                        foreground=THEME["text_primary"],
                        fieldbackground=THEME["bg_card"],
                        bordercolor=THEME["border"],
                        lightcolor=THEME["border"],
                        darkcolor=THEME["border"],
                        font=FONTS["small"],
                        rowheight=32)
        style.configure("Vehicle.Treeview.Heading",
                        background=THEME["bg_surface"],
                        foreground=THEME["accent"],
                        relief="flat",
                        font=FONTS["small_bold"])
        style.map("Vehicle.Treeview",
                  background=[("selected", THEME["accent_dim"])],
                  foreground=[("selected", "#fff")])

        columns = ("name", "date", "total", "status")
        self._tree = ttk.Treeview(tree_frame, columns=columns,
                                   show="headings",
                                   style="Vehicle.Treeview",
                                   selectmode="browse")

        self._tree.heading("name", text="Nombre")
        self._tree.heading("date", text="Fecha")
        self._tree.heading("total", text="Total")
        self._tree.heading("status", text="Estado")

        self._tree.column("name", width=200, minwidth=120)
        self._tree.column("date", width=130, minwidth=100)
        self._tree.column("total", width=60, minwidth=50, anchor="center")
        self._tree.column("status", width=70, minwidth=60, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                   command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_video_select)
        self._tree.bind("<Double-1>", lambda e: self._on_video_select())

    def _build_detail_panel(self, parent):
        container = tk.Frame(parent, bg=THEME["bg_surface"],
                             highlightbackground=THEME["border"],
                             highlightthickness=1, relief="flat")
        container.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._detail_inner = tk.Frame(container, bg=THEME["bg_surface"], padx=16, pady=16)
        self._detail_inner.pack(fill="both", expand=True)

        self._show_empty_detail()

    def _show_empty_detail(self):
        self._clear_detail()

        tk.Label(self._detail_inner, text="Selecciona un video",
                 font=FONTS["heading"],
                 bg=THEME["bg_surface"], fg=THEME["text_muted"]).pack(pady=(60, 0))

        tk.Label(self._detail_inner, text="de la lista para ver su detalle",
                 font=FONTS["body"],
                 bg=THEME["bg_surface"], fg=THEME["text_muted"]).pack()

    def _clear_detail(self):
        for w in self._detail_inner.winfo_children():
            w.destroy()

    def _show_detail(self, video):
        self._clear_detail()

        tk.Label(self._detail_inner, text="Detalle del Video",
                 font=FONTS["subheading"],
                 bg=THEME["bg_surface"], fg=THEME["text_primary"]).pack(anchor="w", pady=(0, 12))

        fields_frame = tk.Frame(self._detail_inner, bg=THEME["bg_surface"])
        fields_frame.pack(fill="x", pady=(0, 12))

        details = [
            ("Nombre:", video.get('original_filename', '-')),
            ("Procesado:", video.get('processed_at', '-')),
            ("Línea:", f"{video.get('line_orientation', '-').capitalize()} @ {int(video.get('line_position', 0) * 100)}%"),
        ]

        duration = video.get('duration_seconds', 0)
        if duration:
            mins, secs = divmod(int(duration), 60)
            hours, mins = divmod(mins, 60)
            if hours:
                dur_str = f"{hours}h {mins}m {secs}s"
            else:
                dur_str = f"{mins}m {secs}s"
            details.append(("Duración:", dur_str))

        for i, (label, value) in enumerate(details):
            row = tk.Frame(fields_frame, bg=THEME["bg_surface"])
            row.pack(fill="x", pady=2)

            tk.Label(row, text=label,
                     font=FONTS["label"],
                     bg=THEME["bg_surface"], fg=THEME["text_secondary"],
                     width=14, anchor="w").pack(side="left")

            tk.Label(row, text=value,
                     font=FONTS["body_bold"],
                     bg=THEME["bg_surface"], fg=THEME["text_primary"],
                     anchor="w").pack(side="left", fill="x", expand=True)

        sep = tk.Frame(self._detail_inner, bg=THEME["border"], height=1)
        sep.pack(fill="x", pady=(0, 12))

        counts = video.get('counts', [])
        counts_map = {c['vehicle_type']: c['count'] for c in counts}

        tk.Label(self._detail_inner, text="Desglose de vehículos",
                 font=FONTS["subheading"],
                 bg=THEME["bg_surface"], fg=THEME["text_primary"]).pack(anchor="w", pady=(0, 10))

        grid = tk.Frame(self._detail_inner, bg=THEME["bg_surface"])
        grid.pack(fill="x")

        for col, vtype in enumerate(VEHICLE_ORDER):
            icon = VEHICLE_ICONS.get(vtype, '🚗')
            label = VEHICLE_LABELS.get(vtype, vtype)
            count_val = counts_map.get(vtype, 0)

            cell = tk.Frame(grid, bg=THEME["bg_card"],
                            highlightbackground=THEME["border"],
                            highlightthickness=1, relief="flat",
                            padx=8, pady=8)
            cell.grid(row=0, column=col, padx=3, pady=3, sticky="nsew")
            grid.grid_columnconfigure(col, weight=1)

            tk.Label(cell, text=icon,
                     font=("Segoe UI Emoji", 20),
                     bg=THEME["bg_card"], fg=THEME["text_primary"]).pack()

            tk.Label(cell, text=label,
                     font=FONTS["small"],
                     bg=THEME["bg_card"], fg=THEME["text_secondary"]).pack(pady=(2, 0))

            tk.Label(cell, text=str(count_val),
                     font=("Segoe UI", 22, "bold"),
                     bg=THEME["bg_card"], fg=THEME["accent"]).pack(pady=(4, 0))

        sep2 = tk.Frame(self._detail_inner, bg=THEME["border"], height=1)
        sep2.pack(fill="x", pady=(12, 8))

        total_val = video.get('total_vehicles', 0)
        total_row = tk.Frame(self._detail_inner, bg=THEME["bg_surface"])
        total_row.pack(fill="x")

        tk.Label(total_row, text="Total general:",
                 font=FONTS["body_bold"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).pack(side="left")

        tk.Label(total_row, text=str(total_val),
                 font=("Segoe UI", 18, "bold"),
                 bg=THEME["bg_surface"], fg=THEME["success"]).pack(side="left", padx=(10, 0))

        if total_val > 0:
            btn_frame = tk.Frame(self._detail_inner, bg=THEME["bg_surface"])
            btn_frame.pack(fill="x", pady=(16, 0))

            delete_btn = tk.Button(
                btn_frame, text="🗑️  Eliminar video",
                font=FONTS["button"],
                bg=THEME["danger_dark"], fg=THEME["text_danger"],
                activebackground=THEME["danger"], activeforeground="#fff",
                relief="flat", bd=0, cursor="hand2",
                padx=14, pady=8,
                command=self._delete_selected
            )
            delete_btn.pack(side="left")
            delete_btn.bind("<Enter>", lambda e: delete_btn.configure(bg=THEME["danger"], fg="#fff"))
            delete_btn.bind("<Leave>", lambda e: delete_btn.configure(bg=THEME["danger_dark"], fg=THEME["text_danger"]))

    def _on_video_select(self, event=None):
        selection = self._tree.selection()
        if not selection:
            return
        item = self._tree.item(selection[0])
        video_id = item.get("tags", [None])[0]
        if video_id:
            self._selected_video_id = video_id
            video = db.get_video_detail(video_id)
            if video:
                self._show_detail(video)
            else:
                self._show_empty_detail()

    def _delete_selected(self):
        if not self._selected_video_id:
            return

        video = db.get_video_detail(self._selected_video_id)
        name = video.get('original_filename', 'este video') if video else 'este video'

        if messagebox.askyesno(
            "Eliminar video",
            f"¿Está seguro de que desea eliminar\n«{name}» y todos sus datos?\n\nEsta acción no se puede deshacer.",
            icon="warning", parent=self
        ):
            db.delete_video(self._selected_video_id)
            self._selected_video_id = None
            self._show_empty_detail()
            self._load_videos()

    def _load_videos(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

        videos = db.get_all_videos()
        if not videos:
            self._show_empty_detail()
            self._list_count_label.configure(text="(0 videos)")
            return

        self._list_count_label.configure(text=f"({len(videos)} video{'s' if len(videos) != 1 else ''})")

        icons = {'done': '✅', 'processing': '🔄', 'pending': '⏳', 'error': '❌', 'cancelled': '⏹️'}

        for v in videos:
            status_icon = icons.get(v['status'], '❓')
            display_name = v.get('original_filename', v.get('filename', '-'))
            if len(display_name) > 35:
                display_name = display_name[:32] + '...'

            self._tree.insert("", "end",
                              values=(
                                  display_name,
                                  v.get('processed_at', '-')[:19],
                                  v.get('total_vehicles', 0),
                                  status_icon,
                              ),
                              tags=(v['id'],))

        if not self._selected_video_id and videos:
            first = self._tree.get_children()[0]
            self._tree.selection_set(first)
            self._tree.focus(first)
            self._on_video_select()

    def _refresh(self):
        self._load_videos()

    def _go_back(self):
        self.app.show_frame("IndexScreen")

    def on_show(self):
        self._selected_video_id = None
        self._load_videos()
