import pymysql
import requests
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env
load_dotenv()

# Obtener variables de entorno
webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
db_config = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}


def notificar_incidencia(incidencia):
    """Envía la incidencia al webhook de Google Chat."""
    mensaje = {
        "text": f"**Nueva incidencia en Rodalies:**\n"
                f"* Línea: {incidencia['linea']}\n"
                f"* Descripción: {incidencia['descripcion']}\n"
                f"* Fecha y hora: {incidencia['fecha']} {incidencia['hora']}"
    }

    response = requests.post(webhook_url, json=mensaje)
    return response.status_code == 200  # True si se notificó con éxito

try:
    # Conexión a la base de datos
    connection = pymysql.connect(**db_config)

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Consulta para obtener una incidencia no notificada
        sql = "SELECT linea, descripcion, fecha, hora FROM incidencia WHERE notificado = 'no' LIMIT 1"
        cursor.execute(sql)
        incidencia = cursor.fetchone()

        if incidencia:
            # Notificar la incidencia
            exito = notificar_incidencia(incidencia)

            if exito:
                # Actualizar el estado de la incidencia a notificada
                update_sql = "UPDATE incidencia SET notificado = 'si' WHERE linea = %s AND fecha = %s AND hora = %s"
                cursor.execute(update_sql, (incidencia['linea'], incidencia['fecha'], incidencia['hora']))
                connection.commit()  # Confirmar los cambios

except pymysql.MySQLError as e:
    print(f"Error en la base de datos: {e}")

finally:
    # Cerrar la conexión
    if connection:
        connection.close()
