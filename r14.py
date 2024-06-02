# -*- coding: utf-8 -*-

import os
import feedparser
import requests
from dotenv import load_dotenv

# crear una variable con la fecha y otra variable con la hora actual
# importar la libreria datetime
from datetime import datetime
# crear una variable con la fecha y hora actual
fecha_actual = datetime.now().strftime('%Y-%m-%d')
hora_actual = datetime.now().strftime('%H:%M:%S')
print(fecha_actual)
print(hora_actual)


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
    # Crear una funcion de Registro de la incidencia en un archivo csv con fecha y hora actual, descripcion de la incidencia (si no hay poner que no hay incidencias) y otra columna con la linia consultada, rl archivo se llamara {nombre_de_linea}_incidencias.csv, cada incidencia se añadira en una nueva fila
# esta funcion registra tambien la fecha actual en otra columna y la hora actual en otra columna del archivo csv
#crear una funcion que crea un archivo csv si no existe (si existe que no crear el archivo) que sea {nombre_de_linea}_incidencias.csv y que contenga una linea: linia,incidencia,descripcion,fecha,hora
def crear_archivo(nombre_de_linea):
    if not os.path.exists(f'{nombre_de_linea}_incidencias.csv'):
       with open(f'{nombre_de_linea}_incidencias.csv', 'a') as file:
            file.write('linia,incidencia,descripcion,fecha,hora\n')
        
def registrar_incidencia(nombre_de_linea, incidencia,fecha_actual,hora_actual):
    with open(f'{nombre_de_linea}_incidencias.csv', 'a') as file:
        file.write(f'{nombre_de_linea},{incidencia["title"]},{incidencia["description"]},{fecha_actual},{hora_actual}\n')
# crear la misma funcion pero que registre como "description" que no hay incidiencias en la linia consultada
def registrar_sin_incidencias(nombre_de_linea, fecha_actual, hora_actual):
    with open(f'{nombre_de_linea}_incidencias.csv', 'a') as file:
        file.write(f'{nombre_de_linea},No hay incidencias en la linia consultada,{fecha_actual},{hora_actual}\n')

            


def main():
    incidencias = obtener_incidencias(rss_url)
    if not incidencias:
        notificar_sin_incidencias(ifttt_webhook_url, nombre_de_linea)
        crear_archivo(nombre_de_linea)
        registrar_sin_incidencias(nombre_de_linea,fecha_actual, hora_actual)
    else:
        for incidencia in incidencias:
            notificar_incidencia(ifttt_webhook_url, incidencia, nombre_de_linea)
            crear_archivo(nombre_de_linea)
            registrar_incidencia(nombre_de_linea, incidencia,fecha_actual,hora_actual)
            

if __name__ == "__main__":
    main()

