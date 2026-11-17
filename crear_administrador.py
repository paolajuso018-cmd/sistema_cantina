from werkzeug.security import generate_password_hash
from models.conexion import obtener_conexion
from getpass import getpass


print("====================================")
print("   CREAR ADMINISTRADOR - LA CANTINA")
print("====================================")

# Datos del administrador
nombre = input("Nombre completo: ").strip()
correo = input("Correo electrónico: ").strip()
username = input("Nombre de usuario: ").strip()
password = getpass("Contraseña: ")
confirmar = getpass("Confirmar contraseña: ")

# Validaciones
if not all([nombre, correo, username, password]):
    print("Error: Todos los campos son obligatorios.")
    raise SystemExit

if password != confirmar:
    print("Error: Las contraseñas no coinciden.")
    raise SystemExit

if len(password) < 8:
    print("Error: La contraseña debe tener al menos 8 caracteres.")
    raise SystemExit

conexion = None
cursor = None

try:

    conexion = obtener_conexion()

    if conexion is None:
        print("No fue posible conectar con MySQL.")
        raise SystemExit

    cursor = conexion.cursor()

    # Verificar si ya existe el administrador
    cursor.execute("""
        SELECT id_usuario
        FROM usuarios
        WHERE id_rol = 1
        LIMIT 1
    """)

    if cursor.fetchone():
        print("Ya existe un usuario administrador.")
        raise SystemExit

    # Verificar que no se repita el usuario o correo
    cursor.execute("""
        SELECT id_usuario
        FROM usuarios
        WHERE username = %s OR correo = %s
        LIMIT 1
    """, (username, correo))

    if cursor.fetchone():
        print("El nombre de usuario o correo ya está registrado.")
        raise SystemExit

    # Cifrar contraseña
    password_cifrado = generate_password_hash(password)

    # Registrar administrador
    cursor.execute("""
        INSERT INTO usuarios (
            id_rol,
            nombre,
            correo,
            username,
            password,
            estado
        )
        VALUES (%s, %s, %s, %s, %s, 'Activo')
    """, (
        1,
        nombre,
        correo,
        username,
        password_cifrado
    ))

    conexion.commit()

    print("\n¡Administrador creado correctamente!")
    print("Nombre:", nombre)
    print("Usuario:", username)
    print("Rol: Administrador")

except Exception as error:

    if conexion:
        conexion.rollback()

    print("Error al crear administrador:", error)

finally:

    if cursor:
        cursor.close()

    if conexion:
        conexion.close()