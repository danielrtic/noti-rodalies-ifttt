# -*- coding: utf-8 -*-

import os
import feedparser
import requests
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# URL del feed RSS de Rodalies Gencat Open Data
rss_url = 'https://www.gencat.cat/rodalies/incidencies_rodalies_rss_r14_es_ES.xml'

# URL del webhook de IFTTT (cargada desde la variable de entorno)
ifttt_webhook_url = os.getenv('IFTTT_WEBHOOK_URL')

# Nombre de la línea que se notifica
nombre_de_linea = 'R14'

def obtener_incidencias(rss_url):
    feed = feedparser.parse(rss_url)
    incidencias = []
    for entry in feed.entries:
        if 'description' in entry:
            incidencia = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.get('link', '')
            }
            incidencias.append(incidencia)
    return incidencias

def notificar_incidencia(ifttt_webhook_url, incidencia, nombre_de_linea):
    data = {
        'value1': f'Incidencia en la línea {nombre_de_linea}: {incidencia["title"]}',
        'value2': incidencia['description'],
        'value3': incidencia['link']
    }
    response = requests.post(ifttt_webhook_url, json=data)
    if response.status_code == 200:
        print('Notificación enviada con éxito.')
    else:
        print(f'Error al enviar notificación: {response.status_code}')

def notificar_sin_incidencias(ifttt_webhook_url, nombre_de_linea):
    data = {
        'value1': f'No hay incidencias en la línea {nombre_de_linea}',
        'value2': '',
        'value3': ''
    }
    response = requests.post(ifttt_webhook_url, json=data)
    if response.status_code == 200:
        print('Notificación de no incidencias enviada con éxito.')
    else:
        print(f'Error al enviar notificación: {response.status_code}')

def main():
    incidencias = obtener_incidencias(rss_url)
    if not incidencias:
        notificar_sin_incidencias(ifttt_webhook_url, nombre_de_linea)
    else:
        for incidencia in incidencias:
            notificar_incidencia(ifttt_webhook_url, incidencia, nombre_de_linea)

if __name__ == "__main__":
    main()
