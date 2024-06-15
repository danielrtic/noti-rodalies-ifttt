import os
import feedparser
import requests
import csv
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables desde .env (incluyendo API_URL para proxies)
load_dotenv()
google_chat_webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
API_URL = os.getenv("API_URL")

# Lista de URLs de feeds RSS (vacía para que las agregues)
rss_urls = {
    'R1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r1_es_ES.xml',
    'R2-norte': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r2_nord_es_ES.xml',
    'R2-sud': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r2_sud_es_ES.xml',
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
    'RG1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rg1_es_ES.xml',
    'RT1': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rt1_es_ES.xml',
    'RT2': 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_rt2_es_ES.xml'
}

# Archivo para almacenar las últimas incidencias notificadas
ULTIMAS_INCIDENCIAS_FILE = 'ultimas_incidencias.json'

def cargar_ultimas_incidencias():
    try:
        with open(ULTIMAS_INCIDENCIAS_FILE, 'r') as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise json.JSONDecodeError("Formato JSON incorrecto", "", 0)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_ultimas_incidencias(ultimas_incidencias):
    with open(ULTIMAS_INCIDENCIAS_FILE, 'w') as f:
        json.dump(ultimas_incidencias, f)

def limpiar_ultimas_incidencias():
    ultimas_incidencias = cargar_ultimas_incidencias()
    ayer = datetime.now() - timedelta(days=1)
    ultimas_incidencias_limpias = []
    for incidencia in ultimas_incidencias:
        if datetime.strptime(incidencia['fecha'], '%Y-%m-%d') >= ayer:
            ultimas_incidencias_limpias.append(incidencia)
    guardar_ultimas_incidencias(ultimas_incidencias_limpias)

def obtener_proxys():
    response = requests.get(API_URL)
    if response.status_code == 200:
        proxys = response.text.splitlines()
        proxys_formateados = []
        for proxy in proxys:
            partes = proxy.split(":")
            if len(partes) == 4:
                ip, puerto, usuario, contraseña = partes
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
    use_proxy = os.getenv("USE_PROXY") == "on"  # Verificar si USE_PROXY está activado
    
    if use_proxy:
        response = usar_proxy_rotatorio(rss_url)
    else:
        response = requests.get(rss_url, timeout=10)  # Petición directa sin proxy
        response.raise_for_status()

    if response is None:  # Manejar error si usar_proxy_rotatorio falla
        return []
    feed = feedparser.parse(response.content)
    return [{'title': entry.title, 'description': entry.description} for entry in feed.entries if 'description' in entry]

def notificar_incidencia(webhook_url, incidencia, nombre_de_linea):
    payload = {
        'text': f'Incidencia en la línea {nombre_de_linea}: {incidencia["description"]}'
    }
    requests.post(webhook_url, json=payload)

def registrar_incidencia(nombre_de_linea, incidencia):
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    hora_actual = datetime.now().strftime('%H:%M:%S')
    filename = f'{nombre_de_linea}_incidencias.csv'

    incidencias_existentes = []
    if os.path.isfile(filename):
        with open(filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                incidencias_existentes.append(row)

    incidencia_registrada = False
    for existente in incidencias_existentes:
        if existente[1] == incidencia['description'] and existente[2] == fecha_actual:
            incidencia_registrada = True
            break

    if not incidencia_registrada:
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([nombre_de_linea, incidencia['description'], fecha_actual, hora_actual])

def main():
    limpiar_ultimas_incidencias()
    ultimas_incidencias = cargar_ultimas_incidencias()
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

            registrar_incidencia(nombre_de_linea, incidencia) 

    if lineas_con_incidencias:
        mensaje_final = f"Resumen de incidencias en las líneas: {', '.join(lineas_con_incidencias)}"
        payload = {'text': mensaje_final}
        requests.post(google_chat_webhook_url, json=payload)

    guardar_ultimas_incidencias(ultimas_incidencias)

if __name__ == "__main__":
    main()