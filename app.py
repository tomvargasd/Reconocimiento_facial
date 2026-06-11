"""
main.py — Punto de entrada principal de la aplicación.

Inicializa la base de datos, carga la ventana principal en Tkinter y gestiona
la navegación entre pantallas (login, index, profile, register).
Implementa ServiceManager para controlar el ciclo de vida de los servicios (Flask)
en segundo plano de manera segura e interactiva.
"""
import sys
import os
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Optional, Dict, Tuple

# Asegurar importación de directorios locales
sys.path.append(str(Path(__file__).parent.resolve()))

from Configs.settings import THEME, FONTS, APP_NAME, WINDOW_SIZE, WINDOW_MIN_SIZE, DEFAULT_PORT_START, PORT_SCAN_RANGE
from Configs import database
from Screens.login import LoginScreen
from Screens.index import IndexScreen
from Screens.profile import ProfileScreen
from Screens.register import RegisterScreen
from Screens.vehicle_processing import VehicleProcessingScreen
from Screens.vehicle_dashboard import VehicleDashboardScreen


# ══════════════════════════════════════════════════════════
# ServiceManager
# ══════════════════════════════════════════════════════════

class ServiceManager:
    """
    Gestiona el ciclo de vida de los subprocesos (servicios web de los módulos).
    Permite iniciar, detener, consultar el estado de cada servicio y
    encontrar puertos libres dinámicamente.
    """

    def __init__(self) -> None:
        # Almacena los procesos Popen por modulo_id
        self._processes: Dict[str, subprocess.Popen] = {}
        # Almacena el puerto asignado por modulo_id
        self._ports: Dict[str, int] = {}
        # Hilos de lectura de logs
        self._log_threads: Dict[str, Tuple[threading.Thread, threading.Thread]] = {}

    def find_free_port(self, start_port: int) -> int:
        """
        Encuentra el primer puerto TCP libre a partir de start_port.
        """
        port = start_port
        for _ in range(PORT_SCAN_RANGE):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    port += 1
        raise IOError(f"No se encontró ningún puerto libre en el rango {start_port} - {start_port + PORT_SCAN_RANGE}")

    def start_service(self, module_info: dict) -> Tuple[bool, Optional[int], str]:
        """
        Inicia el servicio web asociado a un módulo en segundo plano.

        Args:
            module_info: Diccionario con los datos del módulo (id, ruta_directorio, script_entry, etc.)

        Returns:
            Tupla: (éxito: bool, puerto: Optional[int], mensaje_error: str)
        """
        module_id = module_info["id"]
        if self.is_running(module_id):
            return True, self._ports[module_id], ""

        ruta_dir = Path(module_info["ruta_directorio"])
        script = module_info.get("script_entry", "app.py")
        puerto_base = module_info.get("puerto_default", DEFAULT_PORT_START)

        try:
            puerto = self.find_free_port(puerto_base)
        except Exception as e:
            return False, None, f"Error al buscar puerto libre: {e}"

        # Comando para iniciar: python <script> --port <puerto>
        # Pasamos --port para indicarle al app de Flask en qué puerto correr.
        cmd = [sys.executable, script, "--port", str(puerto)]

        try:
            # Iniciamos en segundo plano
            process = subprocess.Popen(
                cmd,
                cwd=str(ruta_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            self._processes[module_id] = process
            self._ports[module_id] = puerto

            # Iniciar lectura de logs en hilos separados para evitar bloquear los buffers
            t_out = threading.Thread(target=self._read_stream, args=(process.stdout, f"{module_id}_stdout"), daemon=True)
            t_err = threading.Thread(target=self._read_stream, args=(process.stderr, f"{module_id}_stderr"), daemon=True)
            t_out.start()
            t_err.start()
            self._log_threads[module_id] = (t_out, t_err)

            # Esperar un momento y validar si no falló inmediatamente
            time_waited = 0.0
            while time_waited < 1.0:
                code = process.poll()
                if code is not None:
                    # El proceso falló al iniciar
                    err_msg = f"El proceso terminó inmediatamente con código {code}."
                    self._cleanup_refs(module_id)
                    return False, None, err_msg
                threading.Event().wait(0.1)
                time_waited += 0.1

            return True, puerto, ""

        except Exception as e:
            self._cleanup_refs(module_id)
            return False, None, f"Excepción al iniciar subproceso: {e}"

    def _read_stream(self, stream, name: str) -> None:
        """Lee continuamente la salida de un stream para evitar bloqueos del proceso."""
        try:
            for line in iter(stream.readline, ""):
                # Opcional: imprimir logs a consola principal para depuración
                print(f"[{name}] {line.strip()}", flush=True)
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def stop_service(self, module_id: str) -> bool:
        """
        Detiene el servicio web de un módulo de forma segura.
        """
        process = self._processes.get(module_id)
        if not process:
            return True

        try:
            # Intentar terminar de forma amistosa
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Forzar apagado si no responde
                process.kill()
                process.wait()
        except Exception as e:
            print(f"Error al detener proceso {module_id}: {e}", flush=True)

        self._cleanup_refs(module_id)
        return True

    def stop_all_services(self) -> None:
        """Detiene todos los servicios actualmente en ejecución."""
        active_ids = list(self._processes.keys())
        for module_id in active_ids:
            self.stop_service(module_id)

    def is_running(self, module_id: str) -> bool:
        """Verifica si el servicio de un módulo está activo."""
        process = self._processes.get(module_id)
        if not process:
            return False
        return process.poll() is None

    def get_port(self, module_id: str) -> Optional[int]:
        """Obtiene el puerto asignado a un módulo activo."""
        if self.is_running(module_id):
            return self._ports.get(module_id)
        return None

    def _cleanup_refs(self, module_id: str) -> None:
        """Limpia las referencias en memoria de un módulo."""
        self._processes.pop(module_id, None)
        self._ports.pop(module_id, None)
        self._log_threads.pop(module_id, None)


# ══════════════════════════════════════════════════════════
# App principal
# ══════════════════════════════════════════════════════════

class App(tk.Tk):
    """
    Ventana principal de la aplicación de escritorio Tkinter.
    Organiza y orquesta el flujo de pantallas y controla los subprocesos.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry(WINDOW_SIZE)
        self.minimum_size = WINDOW_MIN_SIZE
        self.minsize(*WINDOW_MIN_SIZE)

        # Centrar ventana en pantalla al iniciar
        self.eval('tk::PlaceWindow . center')

        # Configuración del Tema
        self.configure(bg=THEME["bg_dark"])

        # Estado global
        self.current_user: Optional[dict] = None
        self.service_manager = ServiceManager()

        # Contenedor principal para apilar pantallas
        self.container = tk.Frame(self, bg=THEME["bg_dark"])
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Diccionario de pantallas
        self.frames: Dict[str, tk.Frame] = {}

        # Cargar pantallas
        all_screens = (
            LoginScreen, IndexScreen, ProfileScreen, RegisterScreen,
            VehicleProcessingScreen, VehicleDashboardScreen,
        )
        for ScreenClass in all_screens:
            name = ScreenClass.__name__
            frame = ScreenClass(parent=self.container, app=self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Configurar cierre seguro de ventana
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Mostrar pantalla inicial
        self.show_frame("LoginScreen")

    def show_frame(self, name: str) -> None:
        """
        Muestra la pantalla especificada trayéndola al frente y
        ejecutando su método de ciclo de vida on_show si existe.
        """
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
            if hasattr(frame, "on_show"):
                frame.on_show()

    def logout(self) -> None:
        """Cierra la sesión del usuario actual y detiene todos los servicios."""
        if messagebox.askyesno(
            "Cerrar sesión",
            "¿Está seguro de que desea cerrar la sesión?\n\nEsto detendrá todos los servicios activos.",
            icon="question", parent=self
        ):
            self.service_manager.stop_all_services()
            self.current_user = None
            self.show_frame("LoginScreen")

    def _on_closing(self) -> None:
        """Manejador del evento de cierre (X). Detiene servicios y sale."""
        # Si hay servicios activos, avisar
        active_count = sum(1 for p in self.service_manager._processes.values() if p.poll() is None)
        if active_count > 0:
            msg = (f"Hay {active_count} servicio(s) activo(s) en ejecución.\n"
                   "Al salir, todos se apagarán automáticamente.\n\n"
                   "¿Desea cerrar la aplicación?")
        else:
            msg = "¿Está seguro de que desea salir del sistema?"

        if messagebox.askyesno("Salir de la aplicación", msg, icon="warning", parent=self):
            # Detener todos los servicios
            self.service_manager.stop_all_services()
            self.destroy()


# ══════════════════════════════════════════════════════════
# Entrada
# ══════════════════════════════════════════════════════════

def main() -> None:
    # Inicializar base de datos de usuarios
    try:
        database.init_db()
        # Si no hay usuarios en la base de datos, crear el administrador inicial automáticamente
        if database.contar_usuarios() == 0:
            success, msg = database.registrar_usuario("admin", "admin123", "Administrador")
            if success:
                print("[AUTO-SEED] Base de datos vacía. Se creó el usuario administrador inicial (admin/admin123).", flush=True)
            else:
                print(f"[WARNING] No se pudo crear el usuario administrador inicial: {msg}", file=sys.stderr)
    except Exception as e:
        print(f"Error fatal al inicializar la base de datos: {e}", file=sys.stderr)
        sys.exit(1)

    app = App()
    app.mainloop()



if __name__ == "__main__":
    main()
