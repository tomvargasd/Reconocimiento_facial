import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from typing import Optional

import cv2
from PIL import Image, ImageTk

from Configs.settings import THEME, FONTS
import Modulos.conteo_vehiculos.database as db
from Modulos.conteo_vehiculos.vehicle_counter import process_video, build_region_points

MODULE_DIR = Path(__file__).parent.parent / "Modulos" / "conteo_vehiculos"
UPLOAD_DIR = MODULE_DIR / "uploaded_videos"

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


class VehicleProcessingScreen(tk.Frame):

    def __init__(self, parent: tk.Widget, app: tk.Tk) -> None:
        super().__init__(parent, bg=THEME["bg_dark"])
        self.app = app

        self._processing = False
        self._cancel_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._current_video_path: Optional[str] = None
        self._current_video_id: Optional[int] = None
        self._photo_ref: Optional[ImageTk.PhotoImage] = None
        self._yolo_available = True
        self._frames_processed = 0
        self._frames_displayed = 0

        self._check_dependencies()
        self._build_ui()

    def _check_dependencies(self):
        try:
            from ultralytics import solutions
        except ImportError:
            self._yolo_available = False

    def _build_ui(self):
        self._build_header()

        main = tk.Frame(self, bg=THEME["bg_dark"])
        main.pack(fill="both", expand=True, padx=20, pady=12)

        main.grid_columnconfigure(0, weight=0, minsize=660)
        main.grid_columnconfigure(1, weight=1, minsize=340)
        main.grid_rowconfigure(0, weight=1)

        self._build_video_area(main)
        self._build_control_panel(main)

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

        title_frame = tk.Frame(nav, bg=THEME["bg_header"])
        title_frame.pack(side="left", padx=(20, 0))

        tk.Label(title_frame, text="🚗",
                 font=("Segoe UI Emoji", 20),
                 bg=THEME["bg_header"], fg=THEME["accent"]).pack(side="left", padx=(0, 8))

        tk.Label(title_frame, text="Conteo de Vehículos",
                 font=FONTS["heading"],
                 bg=THEME["bg_header"], fg=THEME["text_primary"]).pack(side="left")

        if not self._yolo_available:
            warn = tk.Label(nav,
                            text="⚠️ YOLO no disponible. Revisa requirements.txt",
                            font=FONTS["small_bold"],
                            bg=THEME["bg_header"], fg=THEME["text_danger"])
            warn.pack(side="right")

    def _build_video_area(self, parent):
        container = tk.Frame(parent, bg=THEME["bg_dark"])
        container.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        label = tk.Label(container, text="Vista previa del video",
                         font=FONTS["subheading"],
                         bg=THEME["bg_dark"], fg=THEME["text_secondary"])
        label.pack(anchor="w", pady=(0, 8))

        canvas_frame = tk.Frame(container, bg=THEME["bg_surface"],
                                relief="flat", bd=1,
                                highlightbackground=THEME["border"],
                                highlightthickness=1)
        canvas_frame.pack(fill="both", expand=True)

        self.video_canvas = tk.Canvas(
            canvas_frame,
            bg=THEME["bg_card"],
            highlightthickness=0,
            width=640,
            height=480,
        )
        self.video_canvas.pack(fill="both", expand=True, padx=1, pady=1)

        self.video_placeholder = self.video_canvas.create_text(
            320, 240, text="Selecciona un video y presiona Iniciar",
            fill=THEME["text_muted"],
            font=FONTS["body"],
            anchor="center",
        )
        self.video_canvas.bind("<Configure>", self._on_canvas_resize)

    def _build_control_panel(self, parent):
        container = tk.Frame(parent, bg=THEME["bg_dark"])
        container.grid(row=0, column=1, sticky="nsew")

        outer = tk.Frame(container, bg=THEME["bg_surface"],
                         highlightbackground=THEME["border"],
                         highlightthickness=1, relief="flat")
        outer.pack(fill="both", expand=True)

        panel = tk.Frame(outer, bg=THEME["bg_surface"], padx=16, pady=16)
        panel.pack(fill="both", expand=True)

        self._build_config_section(panel)
        self._build_file_section(panel)
        self._build_action_buttons(panel)
        self._build_counter_section(panel)
        self._build_progress_section(panel)

    def _build_config_section(self, parent):
        sec = tk.LabelFrame(parent, text="📐  Configuración de línea",
                            font=FONTS["subheading"],
                            bg=THEME["bg_surface"], fg=THEME["text_primary"],
                            padx=12, pady=10,
                            highlightbackground=THEME["border"],
                            relief="groove", bd=1)
        sec.pack(fill="x", pady=(0, 10))

        orient_frame = tk.Frame(sec, bg=THEME["bg_surface"])
        orient_frame.pack(fill="x", pady=(0, 8))

        tk.Label(orient_frame, text="Orientación:",
                 font=FONTS["label"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).pack(side="left", padx=(0, 10))

        self._orientation_var = tk.StringVar(value="horizontal")

        horiz_rb = tk.Radiobutton(orient_frame, text="Horizontal",
                                   variable=self._orientation_var, value="horizontal",
                                   font=FONTS["label"],
                                   bg=THEME["bg_surface"], fg=THEME["text_primary"],
                                   selectcolor=THEME["bg_card"],
                                   activebackground=THEME["bg_surface"],
                                   activeforeground=THEME["accent"],
                                   relief="flat")
        horiz_rb.pack(side="left", padx=(0, 12))

        vert_rb = tk.Radiobutton(orient_frame, text="Vertical",
                                  variable=self._orientation_var, value="vertical",
                                  font=FONTS["label"],
                                  bg=THEME["bg_surface"], fg=THEME["text_primary"],
                                  selectcolor=THEME["bg_card"],
                                  activebackground=THEME["bg_surface"],
                                  activeforeground=THEME["accent"],
                                  relief="flat")
        vert_rb.pack(side="left")

        pos_frame = tk.Frame(sec, bg=THEME["bg_surface"])
        pos_frame.pack(fill="x")

        tk.Label(pos_frame, text="Posición:",
                 font=FONTS["label"],
                 bg=THEME["bg_surface"], fg=THEME["text_secondary"]).pack(side="left", padx=(0, 10))

        self._position_var = tk.DoubleVar(value=0.5)
        self._pos_slider = tk.Scale(pos_frame, from_=0.0, to=1.0,
                                     resolution=0.01,
                                     orient="horizontal",
                                     variable=self._position_var,
                                     length=140,
                                     bg=THEME["bg_surface"],
                                     fg=THEME["text_primary"],
                                     troughcolor=THEME["bg_card"],
                                     activebackground=THEME["accent"],
                                     highlightthickness=0,
                                     font=FONTS["small"])
        self._pos_slider.pack(side="left", padx=(0, 6))

        self._pos_label = tk.Label(pos_frame, text="50%",
                                    font=FONTS["small_bold"],
                                    bg=THEME["bg_surface"],
                                    fg=THEME["accent"])
        self._pos_label.pack(side="left")

        self._position_var.trace_add("write", self._on_position_change)

    def _build_file_section(self, parent):
        sec = tk.LabelFrame(parent, text="📁  Archivo de video",
                            font=FONTS["subheading"],
                            bg=THEME["bg_surface"], fg=THEME["text_primary"],
                            padx=12, pady=10,
                            highlightbackground=THEME["border"],
                            relief="groove", bd=1)
        sec.pack(fill="x", pady=(0, 10))

        self._file_label = tk.Label(sec,
                                     text="Ningún archivo seleccionado",
                                     font=FONTS["body"],
                                     bg=THEME["bg_surface"],
                                     fg=THEME["text_muted"],
                                     anchor="w",
                                     wraplength=280)
        self._file_label.pack(fill="x", pady=(0, 8))

        select_btn = tk.Button(sec, text="📂  Seleccionar video",
                                font=FONTS["button"],
                                bg=THEME["accent"], fg="#fff",
                                activebackground=THEME["accent_hover"],
                                activeforeground="#fff",
                                relief="flat", bd=0, cursor="hand2",
                                padx=14, pady=8,
                                command=self._select_video)
        select_btn.pack(anchor="w")

    def _build_action_buttons(self, parent):
        btn_frame = tk.Frame(parent, bg=THEME["bg_surface"])
        btn_frame.pack(fill="x", pady=(0, 10))

        self._start_btn = tk.Button(btn_frame, text="▶  Iniciar Conteo",
                                     font=FONTS["button"],
                                     bg=THEME["success"], fg="#fff",
                                     activebackground="#0d9668",
                                     activeforeground="#fff",
                                     relief="flat", bd=0, cursor="hand2",
                                     padx=20, pady=10,
                                     state="disabled",
                                     command=self._start_processing)
        self._start_btn.pack(side="left", padx=(0, 8))

        self._cancel_btn = tk.Button(btn_frame, text="■  Cancelar",
                                      font=FONTS["button"],
                                      bg=THEME["danger_dark"], fg=THEME["text_danger"],
                                      activebackground=THEME["danger"],
                                      activeforeground="#fff",
                                      relief="flat", bd=0, cursor="hand2",
                                      padx=16, pady=10,
                                      state="disabled",
                                      command=self._cancel_processing)
        self._cancel_btn.pack(side="left")

        self._dashboard_btn = tk.Button(btn_frame, text="📊  Ver Dashboard",
                                         font=FONTS["small_bold"],
                                         bg=THEME["info_dark"], fg=THEME["text_info"],
                                         activebackground=THEME["info"],
                                         activeforeground="#fff",
                                         relief="flat", bd=0, cursor="hand2",
                                         padx=14, pady=10,
                                         state="disabled",
                                         command=self._go_to_dashboard)
        self._dashboard_btn.pack(side="right")

    def _build_counter_section(self, parent):
        sec = tk.LabelFrame(parent, text="📊  Contadores en vivo",
                            font=FONTS["subheading"],
                            bg=THEME["bg_surface"], fg=THEME["text_primary"],
                            padx=12, pady=10,
                            highlightbackground=THEME["border"],
                            relief="groove", bd=1)
        sec.pack(fill="x", pady=(0, 10))

        self._counter_labels = {}
        vehicle_order = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']
        for vtype in vehicle_order:
            row = tk.Frame(sec, bg=THEME["bg_surface"])
            row.pack(fill="x", pady=2)

            icon = VEHICLE_ICONS.get(vtype, '🚗')
            label = VEHICLE_LABELS.get(vtype, vtype)

            tk.Label(row, text=f"{icon}  {label}:",
                     font=FONTS["body_bold"],
                     bg=THEME["bg_surface"],
                     fg=THEME["text_primary"],
                     width=16, anchor="w").pack(side="left")

            val_label = tk.Label(row, text="0",
                                  font=("Segoe UI", 14, "bold"),
                                  bg=THEME["bg_surface"],
                                  fg=THEME["accent"],
                                  anchor="e", width=6)
            val_label.pack(side="right")

            self._counter_labels[vtype] = val_label

        sep = tk.Frame(sec, bg=THEME["border"], height=1)
        sep.pack(fill="x", pady=6)

        total_row = tk.Frame(sec, bg=THEME["bg_surface"])
        total_row.pack(fill="x", pady=2)

        tk.Label(total_row, text="Total:",
                 font=FONTS["body_bold"],
                 bg=THEME["bg_surface"],
                 fg=THEME["text_secondary"],
                 width=16, anchor="w").pack(side="left")

        self._total_label = tk.Label(total_row, text="0",
                                      font=("Segoe UI", 16, "bold"),
                                      bg=THEME["bg_surface"],
                                      fg=THEME["success"],
                                      anchor="e", width=6)
        self._total_label.pack(side="right")

    def _build_progress_section(self, parent):
        sec = tk.Frame(parent, bg=THEME["bg_surface"])
        sec.pack(fill="x", side="bottom")

        progress_row = tk.Frame(sec, bg=THEME["bg_surface"])
        progress_row.pack(fill="x")

        self._progress_var = tk.IntVar(value=0)
        self._progress_bar = ttk.Progressbar(progress_row,
                                              variable=self._progress_var,
                                              maximum=100,
                                              length=280)
        self._progress_bar.pack(side="left", padx=(0, 8))

        self._progress_label = tk.Label(progress_row, text="0%",
                                         font=FONTS["small_bold"],
                                         bg=THEME["bg_surface"],
                                         fg=THEME["text_secondary"])
        self._progress_label.pack(side="left")

        self._status_label = tk.Label(sec, text="",
                                       font=FONTS["small"],
                                       bg=THEME["bg_surface"],
                                       fg=THEME["text_muted"],
                                       anchor="w")
        self._status_label.pack(fill="x", pady=(4, 0))

    def _on_position_change(self, *args):
        val = int(self._position_var.get() * 100)
        self._pos_label.configure(text=f"{val}%")

    def _select_video(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar video",
            parent=self,
            filetypes=[
                ("Archivos de video", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                ("Todos los archivos", "*.*"),
            ]
        )
        if not file_path:
            return

        self._current_video_path = file_path
        filename = Path(file_path).name
        self._file_label.configure(text=f"📎  {filename}", fg=THEME["accent"])
        self._start_btn.configure(state="normal")

        self._show_thumbnail(file_path)

    def _show_thumbnail(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                self._display_frame(frame)
        except Exception:
            pass

    def _on_canvas_resize(self, event):
        if self._photo_ref and not self._processing:
            self.video_canvas.coords("video_frame",
                                      event.width // 2, event.height // 2)

    def _display_frame(self, frame_bgr):
        if frame_bgr is None or frame_bgr.size == 0:
            return
        from PIL import Image, ImageTk
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        canvas_w = self.video_canvas.winfo_width() or 640
        canvas_h = self.video_canvas.winfo_height() or 480
        img = self._resize_keep_aspect(img, canvas_w, canvas_h)

        self._photo_ref = ImageTk.PhotoImage(img)

        self.video_canvas.delete("all")
        self.video_canvas.create_image(
            canvas_w // 2, canvas_h // 2,
            image=self._photo_ref,
            anchor="center",
            tags="video_frame",
        )

    def _resize_keep_aspect(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        return img.resize((new_w, new_h), Image.LANCZOS)

    def _start_processing(self):
        if not self._current_video_path or not os.path.exists(self._current_video_path):
            self._status_label.configure(text="❌  Archivo no encontrado", fg=THEME["text_danger"])
            return

        if not self._yolo_available:
            self._status_label.configure(
                text="❌  YOLO no instalado. Ejecuta: pip install -r Modulos/conteo_vehiculos/requirements.txt",
                fg=THEME["text_danger"])
            return

        db.init_db()
        orientation = self._orientation_var.get()
        position = self._position_var.get()

        original_name = Path(self._current_video_path).name
        import uuid
        filename = f"{uuid.uuid4().hex[:8]}_{original_name}"

        upload_path = UPLOAD_DIR / filename
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy2(self._current_video_path, upload_path)

        self._current_video_id = db.insert_video(
            filename=filename,
            original_filename=original_name,
            orientation=orientation,
            position=position,
        )

        db.update_video_status(self._current_video_id, 'processing')

        self._processing = True
        self._cancel_event = threading.Event()

        self._start_btn.configure(state="disabled", text="⏳  Procesando...")
        self._cancel_btn.configure(state="normal")
        self._dashboard_btn.configure(state="disabled")

        for label in self._counter_labels.values():
            label.configure(text="0")
        self._total_label.configure(text="0")
        self._progress_var.set(0)
        self._progress_label.configure(text="0%")
        self._status_label.configure(text="🔄  Procesando video...", fg=THEME["text_info"])

        self._thread = threading.Thread(
            target=self._run_processing,
            args=(str(upload_path), orientation, position),
            daemon=True,
        )
        self._thread.start()

    def _run_processing(self, video_path, orientation, position):
        try:
            process_video(
                video_path=video_path,
                orientation=orientation,
                position=position,
                progress_callback=lambda p: self.app.after(0, self._on_progress, p),
                frame_callback=lambda f: self.app.after(0, self._on_frame, f.copy()),
                counts_callback=lambda c: self.app.after(0, self._on_counts, c),
                cancel_event=self._cancel_event,
                video_id=self._current_video_id,
            )
            if self._cancel_event and self._cancel_event.is_set():
                self.app.after(0, self._on_cancelled)
            else:
                self.app.after(0, self._on_complete)
        except Exception as e:
            self.app.after(0, self._on_error, str(e))

    def _on_frame(self, frame):
        self._frames_processed += 1
        if self._frames_processed % 3 == 0:
            self._frames_displayed += 1
            self._display_frame(frame)

    def _on_progress(self, percent):
        self._progress_var.set(percent)
        self._progress_label.configure(text=f"{percent}%")
        self._status_label.configure(
            text=f"🔄  Procesando... {percent}%  |  {self._frames_processed} frames analizados",
            fg=THEME["text_info"])

    def _on_counts(self, counts):
        for vtype in self._counter_labels:
            val = counts.get(vtype, 0)
            self._counter_labels[vtype].configure(text=str(val))
        total = counts.get('total', 0)
        self._total_label.configure(text=str(total))

    def _on_complete(self):
        self._processing = False
        self._start_btn.configure(state="normal", text="▶  Iniciar Conteo")
        self._cancel_btn.configure(state="disabled")
        self._dashboard_btn.configure(state="normal")
        self._progress_var.set(100)
        self._progress_label.configure(text="100%")
        self._status_label.configure(
            text=f"✅  Procesamiento completado — {self._frames_processed} frames procesados",
            fg=THEME["text_success"])
        self._draw_completion_overlay()

    def _draw_completion_overlay(self):
        canvas_w = self.video_canvas.winfo_width() or 640
        canvas_h = self.video_canvas.winfo_height() or 480
        self.video_canvas.create_rectangle(
            0, canvas_h - 50, canvas_w, canvas_h,
            fill=THEME["success_dark"], outline="",
            tags="overlay")
        self.video_canvas.create_text(
            canvas_w // 2, canvas_h - 25,
            text="✅  ANÁLISIS COMPLETADO  —  Ve al Dashboard para ver los resultados",
            fill=THEME["text_success"],
            font=FONTS["subheading"],
            tags="overlay")

    def _on_cancelled(self):
        self._processing = False
        self._start_btn.configure(state="normal", text="▶  Iniciar Conteo")
        self._cancel_btn.configure(state="disabled")
        self._dashboard_btn.configure(state="normal")
        self._status_label.configure(
            text="⏹️  Procesamiento cancelado",
            fg=THEME["text_warning"])
        canvas_w = self.video_canvas.winfo_width() or 640
        canvas_h = self.video_canvas.winfo_height() or 480
        self.video_canvas.create_text(
            canvas_w // 2, canvas_h // 2,
            text="⏹️  PROCESAMIENTO CANCELADO",
            fill=THEME["text_warning"],
            font=("Segoe UI", 18, "bold"),
            tags="overlay")

    def _on_error(self, error_msg):
        self._processing = False
        self._start_btn.configure(state="normal", text="▶  Iniciar Conteo")
        self._cancel_btn.configure(state="disabled")
        self._status_label.configure(
            text=f"❌  Error: {error_msg}",
            fg=THEME["text_danger"])
        if self._current_video_id:
            db.update_video_status(self._current_video_id, 'error')
        canvas_w = self.video_canvas.winfo_width() or 640
        canvas_h = self.video_canvas.winfo_height() or 480
        self.video_canvas.create_text(
            canvas_w // 2, canvas_h // 2,
            text=f"❌  ERROR: {error_msg}",
            fill=THEME["text_danger"],
            font=("Segoe UI", 14, "bold"),
            tags="overlay")

    def _cancel_processing(self):
        if self._cancel_event:
            self._cancel_event.set()
        self._cancel_btn.configure(state="disabled")
        self._status_label.configure(text="⏹️  Cancelando...", fg=THEME["text_warning"])

    def _go_back(self):
        self._cancel_processing()
        self.app.show_frame("IndexScreen")

    def _go_to_dashboard(self):
        self.app.show_frame("VehicleDashboardScreen")

    def on_show(self):
        pass
