
from flask import Flask, render_template
from config import Config

app = Flask(__name__)
app.config.from_object(Config)


# ==========================================
# BLUEPRINTS
# ==========================================

from routes.login import login_bp
from routes.registro import registro_bp
from routes.reservaciones import reservaciones_bp
from routes.administrativo import administrativo_bp
from routes.usuarios import usuarios_bp
from routes.almacen import almacen_bp
from routes.recetas import recetas_bp
from routes.ventas import ventas_bp


# ==========================================
# REGISTRO DE BLUEPRINTS
# ==========================================

app.register_blueprint(login_bp)
app.register_blueprint(registro_bp)
app.register_blueprint(reservaciones_bp)
app.register_blueprint(administrativo_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(almacen_bp)
app.register_blueprint(recetas_bp)
app.register_blueprint(ventas_bp)


# ==========================================
# PÁGINA PÚBLICA
# ==========================================

@app.route("/")
def inicio():
    return render_template("inicio.html")


# ==========================================
# PRUEBA DE CONEXIÓN MYSQL
# ==========================================

@app.route("/prueba-conexion")
def prueba_conexion():

    from models.conexion import obtener_conexion

    conexion = obtener_conexion()

    if conexion:

        cursor = conexion.cursor()
        cursor.execute("SELECT DATABASE()")
        resultado = cursor.fetchone()

        cursor.close()
        conexion.close()

        return f"""
            <h1>¡Conexión exitosa!</h1>
            <p>Base de datos conectada: {resultado[0]}</p>
        """

    return "Error: No se pudo conectar con MySQL."

print("\n========== RUTAS REGISTRADAS ==========")

for regla in app.url_map.iter_rules():
    print(regla.endpoint, "->", regla.rule)

print("=======================================\n")

# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)
