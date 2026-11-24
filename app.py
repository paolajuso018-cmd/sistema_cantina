
from flask import Flask, render_template
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

if not app.config.get("SECRET_KEY"):
    raise RuntimeError("Falta configurar SECRET_KEY")

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
from routes.compras import compras_bp
from routes.proveedores import proveedores_bp
from routes.compras_gerente import compras_gerente_bp


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
app.register_blueprint(compras_bp)
app.register_blueprint(proveedores_bp)
app.register_blueprint(compras_gerente_bp)



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

    if not app.debug:
        return "No disponible", 404

    from models.conexion import obtener_conexion

    conexion = obtener_conexion()

    if conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT DATABASE()")
        resultado = cursor.fetchone()

        cursor.close()
        conexion.close()

        return "Conexión exitosa"

    return "Error de conexión", 500

# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)
