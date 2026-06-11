"""
create_user.py — Script de consola para registrar un usuario manualmente.

Uso:
    python scripts/create_user.py --username <usuario> --password <contraseña> [--nombre <nombre>]

Si no se proveen argumentos, los solicitará interactivamente.
"""
import sys
from pathlib import Path
import argparse

# Agregar la raíz del proyecto al sys.path para poder importar Configs
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from Configs import database


def main():
    parser = argparse.ArgumentParser(description="Registrar un usuario en el sistema SQLite de la aplicación.")
    parser.add_argument("--username", type=str, help="Nombre de usuario único.")
    parser.add_argument("--password", type=str, help="Contraseña (mínimo 4 caracteres).")
    parser.add_argument("--nombre", type=str, default="", help="Nombre completo opcional.")

    args = parser.parse_args()

    username = args.username
    password = args.password
    nombre = args.nombre

    # Modo interactivo si faltan argumentos
    if not username:
        username = input("Ingrese el nombre de usuario: ").strip()
    if not password:
        password = input("Ingrese la contraseña: ")
    if not nombre and not args.username:  # Preguntar si estamos en modo interactivo
        nombre = input("Ingrese el nombre completo (opcional): ").strip()

    # Inicializar la base de datos por si acaso
    database.init_db()

    success, msg = database.registrar_usuario(username, password, nombre)

    if success:
        print(f"\n[ÉXITO] Usuario '{username}' registrado correctamente en la base de datos.")
    else:
        print(f"\n[ERROR] No se pudo registrar el usuario: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
