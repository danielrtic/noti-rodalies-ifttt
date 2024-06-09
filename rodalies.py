import os
import feedparser
import requests
import csv
import json
from datetime import datetime, timedelta

# Cargar las variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()

# URL del webhook de Google Chat
google_chat_webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')

# Lista de URLs de feeds RSS de Rodalies
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

def obtener_incidencias(rss_url):
    feed = feedparser.parse(rss_url)
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

    # Leer las incidencias existentes en el CSV (sin encabezados)
    incidencias_existentes = []
    if os.path.isfile(filename):
        with open(filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                incidencias_existentes.append(row)

    # Verificar si la incidencia ya está registrada hoy
    incidencia_registrada = False
    for existente in incidencias_existentes:
        if existente[1] == incidencia['description'] and existente[2] == fecha_actual:
            incidencia_registrada = True
            break

    # Registrar la incidencia solo si no está registrada hoy
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
            # Verificar si la incidencia ya fue notificada hoy
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

            registrar_incidencia(nombre_de_linea, incidencia)  # Registrar siempre en el CSV

    # Enviar notificación final si hay incidencias
    if lineas_con_incidencias:
        mensaje_final = f"Resumen de incidencias en las líneas: {', '.join(lineas_con_incidencias)}"
        payload = {'text': mensaje_final}
        requests.post(google_chat_webhook_url, json=payload)

    guardar_ultimas_incidencias(ultimas_incidencias)  # Guardar las últimas incidencias

if __name__ == "__main__":
    main()
