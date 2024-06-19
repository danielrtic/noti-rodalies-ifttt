import os
import feedparser
import requests
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pymysql

# Cargar variables desde .env
load_dotenv()
google_chat_webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
API_URL = os.getenv("API_URL")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Lista de URLs de feeds RSS (vacía para que las agregues)
rss_urls = {
    'R1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r1_es_ES.xml',
    'R2-NORTE': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r2_nord_es_ES.xml',
    'R2-SUD': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r2_sud_es_ES.xml',
    'R3': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r3_es_ES.xml',
    'R4': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r4_es_ES.xml',
    'R7': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r7_es_ES.xml',
    'R8': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r8_es_ES.xml',
    'R11': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r11_es_ES.xml',
    'R12': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r12_es_ES.xml',
    'R13': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r13_es_ES.xml',
    'R14': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r14_es_ES.xml',
    'R15': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r15_es_ES.xml',
    'R16': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r16_es_ES.xml',
    'R17': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r17_es_ES.xml',
    'RL3': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rl3_es_ES.xml',
    'RG1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rg1_es_ES.xml',
    'RT1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rt1_es_ES.xml',
    'RT2': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rt2_es_ES.xml'
}

# Conexión a MySQL usando PyMySQL (GLOBAL)
cnx = None # Inicializar como None para evitar errores antes de la conexión

def obtener_proxys():
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()  # Obtener datos como JSON
        proxys_formateados = []
        for proxy in data:  # Iterar sobre los datos JSON
            ip = proxy.get("ip")
            puerto = proxy.get("puerto")
            usuario = proxy.get("usuario")
            contraseña = proxy.get("contraseña")
            if all([ip, puerto, usuario, contraseña]):
                proxy_formateado = f"{ip}:{puerto}:{usuario}:{contraseña}"
                proxys_formateados.append(proxy_formateado)
        return proxys_formateados
    else:
        print("Error al obtener proxies de la API.")
        return []

def usar_proxy_rotatorio(url_objetivo):
    proxys = obtener_proxys()
    if not proxys:
        return

    proxy_elegido = random.choice(proxys)
    ip, puerto, usuario, contraseña = proxy_elegido.split(":")
    proxies = {
        "http": f"http://{usuario}:{contraseña}@{ip}:{puerto}",
        "https": f"http://{usuario}:{contraseña}@{ip}:{puerto}",
    }

    try:
        response = requests.get(url_objetivo, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error al usar el proxy: {e}")
        return None

def obtener_incidencias(rss_url):
    use_proxy = os.getenv("USE_PROXY") == "on"
    if use_proxy:
        response = usar_proxy_rotatorio(rss_url)
    else:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()

    if response is None:
        return []
    feed = feedparser.parse(response.content)
    incidencias = [{'title': entry.title, 'description': entry.description} for entry in feed.entries if 'description' in entry]
    if not incidencias:
        print(f"No se encontraron incidencias en el feed: {rss_url}")  # Verificar si se obtienen incidencias
    return incidencias

def notificar_incidencia(webhook_url, incidencia, nombre_de_linea):
    payload = {
        'text': f'Incidencia en la línea {nombre_de_linea}: {incidencia["description"]}'
    }
    requests.post(webhook_url, json=payload)

def registrar_incidencia(cursor, nombre_de_linea, incidencia):
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    hora_actual = datetime.now().strftime('%H:%M:%S')

    # Consulta para verificar si la incidencia ya existe HOY
    cursor.execute(
        "SELECT * FROM incidencias WHERE linea = %s AND descripcion = %s AND fecha = %s",
        (nombre_de_linea, incidencia['description'], fecha_actual)
    )
    if not cursor.fetchone():  # La incidencia no existe HOY
        try:
            print(f"Intentando insertar: {nombre_de_linea}, {incidencia['description']}, {fecha_actual}, {hora_actual}")
            cursor.execute(
                "INSERT INTO incidencias (linea, descripcion, fecha, hora) VALUES (%s, %s, %s, %s)",
                (nombre_de_linea, incidencia['description'], fecha_actual, hora_actual)
            )
        except pymysql.Error as e:
            print(f"Error al insertar incidencia en MySQL: {e}")
        else:
            cnx.commit()  # Confirmar cambios solo si no hay error

def cargar_ultimas_incidencias(cursor):
    try:
        cursor.execute("SELECT descripcion, fecha FROM incidencias ORDER BY fecha DESC, hora DESC")
        return [{'description': row[0], 'fecha': row[1].strftime('%Y-%m-%d')} for row in cursor.fetchall()]
    except pymysql.Error as e:
        print(f"Error al cargar últimas incidencias desde MySQL: {e}")
        return []  # Devolver lista vacía en caso de error


def main():
    global cnx  # Indicar que estamos usando la variable global cnx
    try:
        # Conexión a MySQL usando PyMySQL
        cnx = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("Conexión a MySQL exitosa")  # Confirmar conexión
        cursor = cnx.cursor()
    
        ultimas_incidencias = cargar_ultimas_incidencias(cursor)
        lineas_con_incidencias = set()
        for nombre_de_linea, rss_url in rss_urls.items():
            incidencias = obtener_incidencias(rss_url)
            for incidencia in incidencias:
                incidencia_notificada = False
                for ultima_incidencia in ultimas_incidencias:
                    if ultima_incidencia['description'] == incidencia['description'] and ultima_incidencia['fecha'] == datetime.now().strftime('%Y-%m-%d'):
                        incidencia_notificada = True
                        break
    
                if not incidencia_notificada:
                    notificar_incidencia(google_chat_webhook_url, incidencia, nombre_de_linea)
                    lineas_con_incidencias.add(nombre_de_linea)
                    ultimas_incidencias.append({
                        'description': incidencia['description'],
                        'fecha': datetime.now().strftime('%Y-%m-%d')
                    })
    
                registrar_incidencia(cursor, nombre_de_linea, incidencia)  # Intenta registrar (puede ser duplicado)
    
        if lineas_con_incidencias:
            mensaje_final = f"Resumen de incidencias en las líneas: {', '.join(lineas_con_incidencias)}"
            payload = {'text': mensaje_final}
            requests.post(google_chat_webhook_url, json=payload)

    except pymysql.MySQLError as e:  # Capturar errores específicos de MySQL
        if e.args[0] == 2003:
            print(f"Error de conexión: No se puede conectar al servidor MySQL. Verifica el host y el puerto.")
        elif e.args[0] == 1045:
            print(f"Error de acceso: Usuario o contraseña incorrectos.")
        else:
            print(f"Error general de MySQL: {e}")
    finally:
        if cnx:  # Verificar si la conexión se estableció antes de cerrarla
            cursor.close()
            cnx.close()

if __name__ == "__main__":
    main()
