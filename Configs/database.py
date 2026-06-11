"""
database.py — Gestión de la base de datos SQLite de la aplicación Tkinter.

Modelos:
    - usuarios:      Cuentas de acceso al sistema.
    - modulos:       Registro de módulos descubiertos (cache).
    - estado_modulos: Estado de ejecución persistente de los módulos.

Funciones exportadas:
    get_conn, init_db, verificar_credenciales, registrar_usuario,
    listar_usuarios, actualizar_usuario, eliminar_usuario, contar_usuarios.
"""
import sqlite3
import hashlib
from typing import Optional
from Configs.settings import DB_PATH


# ══════════════════════════════════════════════════════════
# Utilidades internas
# ══════════════════════════════════════════════════════════

def _hash_password(password: str) -> str:
    """Genera el hash SHA-256 de una contraseña en texto plano."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════
# Conexión y inicialización
# ══════════════════════════════════════════════════════════

def get_conn() -> sqlite3.Connection:
    """
    Abre y retorna una conexión a la base de datos de la aplicación.

    Activa el Row Factory para acceder a columnas por nombre y
    habilita el soporte de claves foráneas.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """
    Inicializa la base de datos creando las tablas si no existen.

    Es seguro llamar esta función en cada arranque de la aplicación;
    usa CREATE TABLE IF NOT EXISTS para no destruir datos existentes.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    # ── Tabla de usuarios del sistema Tkinter ────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id               INTEGER  PRIMARY KEY AUTOINCREMENT,
            username         TEXT     NOT NULL UNIQUE,
            password_hash    TEXT     NOT NULL,
            nombre_completo  TEXT     NOT NULL DEFAULT '',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Registro de módulos descubiertos (cache) ─────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS modulos (
            id               INTEGER  PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT     NOT NULL,
            descripcion      TEXT     DEFAULT '',
            ruta_directorio  TEXT     NOT NULL UNIQUE,
            script_entry     TEXT     NOT NULL DEFAULT 'app.py',
            puerto_default   INTEGER  NOT NULL DEFAULT 5000,
            icono            TEXT     DEFAULT '🔷'
        )
    """)

    # ── Estado de ejecución de los módulos ───────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS estado_modulos (
            modulo_id        TEXT     PRIMARY KEY,
            puerto_asignado  INTEGER,
            pid              INTEGER,
            activo           INTEGER  NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════
# Funciones de usuario
# ══════════════════════════════════════════════════════════

def verificar_credenciales(username: str, password: str) -> Optional[sqlite3.Row]:
    """
    Verifica las credenciales del usuario contra la base de datos.

    Args:
        username: Nombre de usuario.
        password: Contraseña en texto plano (se hashea internamente).

    Returns:
        La fila del usuario (sqlite3.Row) si las credenciales son válidas,
        None en caso contrario.
    """
    conn = get_conn()
    ph = _hash_password(password)
    user = conn.execute(
        "SELECT * FROM usuarios WHERE username = ? AND password_hash = ?",
        (username, ph)
    ).fetchone()
    conn.close()
    return user


def registrar_usuario(
    username: str,
    password: str,
    nombre_completo: str = ""
) -> tuple:
    """
    Registra un nuevo usuario en la base de datos.

    Args:
        username:        Nombre de usuario único.
        password:        Contraseña en texto plano (mínimo 4 caracteres).
        nombre_completo: Nombre descriptivo opcional.

    Returns:
        Tupla (True, '') si el registro fue exitoso.
        Tupla (False, mensaje_error) si ocurrió algún problema.
    """
    if not username or not password:
        return False, "El usuario y la contraseña son obligatorios."
    if len(password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."

    ph = _hash_password(password)
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre_completo) VALUES (?, ?, ?)",
            (username.strip(), ph, nombre_completo.strip())
        )
        conn.commit()
        conn.close()
        return True, ""
    except sqlite3.IntegrityError:
        return False, f"El usuario '{username}' ya existe en el sistema."
    except Exception as e:
        return False, f"Error inesperado: {e}"


def listar_usuarios() -> list:
    """
    Obtiene todos los usuarios registrados sin exponer password_hash.

    Returns:
        Lista de diccionarios con campos: id, username, nombre_completo, created_at.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, nombre_completo, created_at "
        "FROM usuarios ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actualizar_usuario(
    user_id: int,
    nuevo_username: str,
    nuevo_nombre: str,
    nueva_password: str = ""
) -> tuple:
    """
    Actualiza los datos de un usuario existente.

    Args:
        user_id:          ID del usuario a modificar.
        nuevo_username:   Nuevo nombre de usuario.
        nuevo_nombre:     Nuevo nombre completo.
        nueva_password:   Nueva contraseña (si está vacía, no se modifica).

    Returns:
        Tupla (True, '') si éxito, (False, mensaje_error) si falla.
    """
    if not nuevo_username:
        return False, "El nombre de usuario no puede estar vacío."
    try:
        conn = get_conn()
        if nueva_password:
            ph = _hash_password(nueva_password)
            conn.execute(
                "UPDATE usuarios SET username=?, nombre_completo=?, password_hash=? WHERE id=?",
                (nuevo_username.strip(), nuevo_nombre.strip(), ph, user_id)
            )
        else:
            conn.execute(
                "UPDATE usuarios SET username=?, nombre_completo=? WHERE id=?",
                (nuevo_username.strip(), nuevo_nombre.strip(), user_id)
            )
        conn.commit()
        conn.close()
        return True, ""
    except sqlite3.IntegrityError:
        return False, f"El nombre de usuario '{nuevo_username}' ya está en uso."
    except Exception as e:
        return False, f"Error inesperado: {e}"


def eliminar_usuario(user_id: int) -> tuple:
    """
    Elimina un usuario de la base de datos por su ID.

    Args:
        user_id: ID del usuario a eliminar.

    Returns:
        Tupla (True, '') si éxito, (False, mensaje_error) si falla.
    """
    try:
        conn = get_conn()
        conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True, ""
    except Exception as e:
        return False, f"Error al eliminar: {e}"


def contar_usuarios() -> int:
    """Retorna el número total de usuarios registrados en el sistema."""
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    conn.close()
    return count


def get_usuario_por_id(user_id: int) -> Optional[dict]:
    """
    Busca un usuario por su ID.

    Returns:
        Diccionario con los datos del usuario, o None si no existe.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username, nombre_completo, created_at FROM usuarios WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
