from flask import Blueprint
import datetime
import os
import random
import string
import sqlite3
import pytz
import shutil
from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    session,
    redirect,
    url_for
)
from flask_socketio import *
from Insight import sql_commands
from config import API_KEYS, EXPECTED_POST_KEYS
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import glob
import subprocess
import ffmpeg
import moviepy.video.io.ImageSequenceClip as isc
import math

views = Blueprint('views', __name__)

@views.route('/test')
def test():
    return 'Blueprint'

# @socketio.on('Fetch Sensor Data')
# def fetch_request():
#     # Called when Client requests stored sensor data
#     print('The sensor data was requested.')
#     connection = sqlite3.connect('data.db')
#     api_key = ('GROUP3',)
#     cur = connection.execute('SELECT heart_rate, temp, co_level, lat, lon, '
#                              'proximity_sensor, temp_array, image_path, MAX(datetime) '
#                              'FROM wearables WHERE Api_key = ?', api_key)
#     result = cur.fetchone()
#
#     print('result:', result)
#     if result == (None, None, None, None, None, None, None, None, None):
#         return 'Failed'
#
#     print(result)
#     l = list(result)
#     t_list = l[6].split(',')
#     print(t_list)
#     l[6] = t_list
#     result = l
#
#     # Formats query into a result that can be used by the browser to render
#     zipped = zip(('hr', 'temp', 'co_level', 'lat', 'lon', 'proximity_sensor', 'thermal_array', 'streamed_image'),
#                  result)
#     final = {num: data for num, data in list(zipped)}
#     final['streamed_image'] = '../' + final['streamed_image']
#
#     print('Requested Data: ', final)
#     socketio.emit('Requested Data', final)


@views.route('/delete/<key>')
def delete(key):
    if key != 'test':
        return redirect(url_for('modern_dashboard'))
    conn = sqlite3.connect('../../data.db')
    cur = conn.execute('DROP TABLE wearables')
    cur.execute(sql_commands.setup_wearable_table)
    cur.execute('DROP TABLE users')
    cur.execute(sql_commands.setup_users)
    cur.execute('INSERT INTO users VALUES (:Id, :username, :password);',
                {'Id': None,
                 'username': 'test',
                 'password': 'test'
                 })
    cur.execute('INSERT INTO users VALUES (:Id, :username, :password);',
                {'Id': None,
                 'username': 'kyle',
                 'password': 'test'
                 })
    shutil.rmtree('../../uploads')
    os.mkdir('../../uploads')
    return 'delete'


# Called when attempting to access the Dashboard
@views.route('/')
def home():
    # connection = sqlite3.connect('data.db')
    # # Gets all devices that have initially connected to database
    # cur = connection.execute('SELECT api_key FROM connections')
    # results = cur.fetchall()
    # print('Results:', results)
    # connection.close()
    # Passes device information to render Dashboard with devices
    return redirect(url_for('views.login'))


@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.pop('user_id', None)

        username = request.form['user']
        password = request.form['password']

        conn = sqlite3.connect('../../data.db')
        cur = conn.execute('SELECT * FROM users '
                           'WHERE username = ? '
                           'AND password = ?', (username, password))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            session['user'] = username
            return redirect(url_for('modern_dashboard'))

    return render_template('login.html')


@views.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['user']
        password = request.form['password']
        verify = request.form['verify']

        if not password == verify:
            return 'Passwords Must Match'

        conn = sqlite3.connect('../../data.db')
        cur = conn.execute('SELECT * FROM users '
                           'WHERE username = ? '
                           'AND password = ?', (username, password))
        result = cur.fetchone()
        cur.close()

        if not result is None:
            return 'Username And Password Already Exist'

        cur = conn.execute('INSERT INTO users VALUES (:Id, :username, :password)',
                           {'Id': None,
                            'username': username,
                            'password': password
                            })
        conn.commit()
        cur.close()

    return render_template('register.html')


@views.route('/base')
def base():
    return render_template('modern-base.html')


@views.route('/modern_dash')
def modern_dashboard():
    # Renders previously saved sensor data on the dashboard
    labels = ['Heart Rate',
              'Temperature',
              'Carbon Monoxide',
              'Longitude',
              'Latitude',
              'Proximity']

    connection = sqlite3.connect('../../data.db')
    cur = connection.execute('SELECT * FROM wearables WHERE Api_key = ? ORDER BY datetime DESC', ('GROUP3',))
    rows = cur.fetchall()

    if len(rows) < 1:
        return 'No History To Display'

    print(rows)
    print(rows[-1])

    # Restructures list to group data by type instead of by entries
    clustered_data = zip(*rows)
    grouped_data = [list(group) for group in list(clustered_data)]
    print(grouped_data)

    cur.execute('SELECT image_path FROM wearables WHERE Api_key = ? ORDER BY datetime DESC', ("GROUP3",))
    image_paths = cur.fetchall()

    print(glob.glob('uploads/*'))
    print(image_paths)

    paths = [path[0] for path in image_paths]
    print(paths)
    clip = isc.ImageSequenceClip(paths, fps=1)
    clip.write_videofile('output/test.mp4')

    cur.close()
    connection.close()

    # Renders the HTML passing sensor information and labels
    return render_template('modern-dash.html', data=grouped_data[2:], labels=labels)


@views.route('/tables')
def tables():
    labels = ['Heart Rate', 'Carbon Monoxide Levels',
              'Longitude', 'Latitude', 'Proximity', 'Thermal Array',
              'Image File']
    return render_template('tables.html', labels=labels)


@views.route('/notes')
def notes():
    return render_template('notifications.html')


@views.route('/user')
def user():
    return render_template('user.html')


@views.route('/black-dash')
def dashboard():
    return render_template('new-dashboard.html')


@views.route('/live-table')
def live_table():
    return render_template('tables.html')


@views.route('/map')
def map():
    conn = sqlite3.connect('../../data.db')
    cur = conn.execute('SELECT lat, lon FROM wearables '
                       'WHERE api_key = ? ORDER BY datetime DESC', ('GROUP3',))
    result = cur.fetchall()
    print(result)
    cur.close()
    conn.close()
    return render_template('map.html', coordinates=result)


@views.route('/init_device_conn/<api_key>')
def init_device_conn(api_key):
    # Sets Up IOT device initial connection with server
    # After successful connection, device info will be rendered on dashboard
    if api_key in API_KEYS:
        connection = sqlite3.connect('../../data.db')
        cur = connection.execute('INSERT INTO connections VALUES (:Id, :api_key, :datetime);',
                                 {'Id': None,
                                  'api_key': api_key,
                                  'datetime': str(datetime.datetime.now())[:19]
                                  })
        connection.commit()
        cur.close()
        connection.close()

        return 'Successfully connected.'
    else:
        return 'Failed to connect.'


@views.route('/history/<api_key>')
def history(api_key):
    if api_key not in API_KEYS:
        return 'Invalid API Key'

    # Renders previously saved sensor data on the dashboard
    labels = ['Heart Rate',
              'Temperature',
              'Carbon Monoxide Levels',
              'Latitude',
              'Longitude',
              'Proximity']

    connection = sqlite3.connect('../../data.db')
    cur = connection.execute('SELECT * FROM wearables WHERE Api_key = ? ORDER BY datetime DESC', (api_key,))
    rows = cur.fetchall()

    if len(rows) < 1:
        return 'No History To Display'

    print(rows)
    print(rows[-1])

    # Restructures list to group data by type instead of by entries
    unzipped_object = zip(*rows)
    grouped_data = [list(group) for group in list(unzipped_object)]

    cur.execute('SELECT image_path FROM wearables WHERE Api_key = ? ORDER BY datetime DESC', (api_key,))
    image_paths = cur.fetchall()

    print(glob.glob('uploads/*'))
    print(image_paths)

    img_array = []
    for path in image_paths:
        actual_path = path[0]
        print(actual_path)
        img = cv2.imread(actual_path)
        height, width, layers = img.shape
        size = (width, height)
        img_array.append(img)

    out = cv2.VideoWriter('video/project.mp4', cv2.VideoWriter.fourcc(*'MP4v'), 1, size)

    for image in img_array:
        out.write(image)

    out.release()

    # subprocess.call(['ffmpeg', '-i', 'video/project.mp4', '-c:v', 'h264', 'output/images.mp4'])

    cur.close()
    connection.close()

    # Renders the HTML passing sensor information and labels
    return render_template('history.html', data=grouped_data[2:], labels=labels)

@views.route('/generate_video')
def gen_vid():
    img_array = []
    for path in glob.glob('uploads/*'):
        print(path)
        img = cv2.imread(path)
        height, width, layers = img.shape
        size = (width, height)
        img_array.append(img)

    out = cv2.VideoWriter('video/project.mp4', cv2.VideoWriter.fourcc(*'H264'), 1, size)

    for image in img_array:
        out.write(image)
        print('Image', image)

    out.release()
    print(os.listdir('../templates'))
    return render_template('video.html')


# @views.route('/uploads/<image>')
# def image_retrieval(image):
#     return send_from_directory(app.config['UPLOAD_PATH'], image)


@views.route('/view_video')
def sample_video():
    return render_template('video.html')


@views.route('/video/<video>')
def video_file(video):
    return send_from_directory('output', video)