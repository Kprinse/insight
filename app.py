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
import sql_commands
from config import API_KEYS, EXPECTED_POST_KEYS
import gunicorn
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import glob
import subprocess
import ffmpeg
import moviepy.video.io.ImageSequenceClip as isc
import math

app = Flask(__name__)

app.config['UPLOAD_PATH'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
app.secret_key = 'secret'

socketio = SocketIO(app)

# Checks if the database exists
if not os.path.isfile('data.db'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # Sets Up Needed Tables
    c.execute(sql_commands.setup_connections)
    c.execute(sql_commands.setup_wearable_table)
    c.execute(sql_commands.setup_users)

    conn.commit()
    conn.close()


@socketio.on('Fetch Sensor Data')
def fetch_request():
    # Called when Client requests stored sensor data
    print('The sensor data was requested.')
    connection = sqlite3.connect('data.db')
    api_key = ('GROUP3',)
    cur = connection.execute('SELECT heart_rate, temp, co_level, lat, lon, '
                             'proximity_sensor, temp_array, image_path, MAX(datetime) '
                             'FROM wearables WHERE Api_key = ?', api_key)
    result = cur.fetchone()

    print('result:', result)
    if result == (None, None, None, None, None, None, None, None, None):
        return 'Failed'

    print(result)
    l = list(result)
    t_list = l[6].split(',')
    print(t_list)
    l[6] = t_list
    result = l

    # Formats query into a result that can be used by the browser to render
    zipped = zip(('hr', 'temp', 'co_level', 'lat', 'lon', 'proximity_sensor', 'thermal_array', 'streamed_image'),
                 result)
    final = {num: data for num, data in list(zipped)}
    final['streamed_image'] = '../' + final['streamed_image']

    print('Requested Data: ', final)
    socketio.emit('Requested Data', final)


@app.route('/delete/<key>')
def delete(key):
    if key != 'test':
        return redirect(url_for('modern_dashboard'))
    conn = sqlite3.connect('data.db')
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
    shutil.rmtree('uploads')
    os.mkdir('uploads')
    return 'delete'


# Called when attempting to access the Dashboard
@app.route('/')
def home():
    # connection = sqlite3.connect('data.db')
    # # Gets all devices that have initially connected to database
    # cur = connection.execute('SELECT api_key FROM connections')
    # results = cur.fetchall()
    # print('Results:', results)
    # connection.close()
    # Passes device information to render Dashboard with devices
    return redirect(url_for("login"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.pop('user_id', None)

        username = request.form['user']
        password = request.form['password']

        conn = sqlite3.connect('data.db')
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['user']
        password = request.form['password']
        verify = request.form['verify']

        if not password == verify:
            return 'Passwords Must Match'

        conn = sqlite3.connect('data.db')
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


@app.route('/base')
def base():
    return render_template('modern-base.html')


@app.route('/modern_dash')
def modern_dashboard():
    # Renders previously saved sensor data on the dashboard
    labels = ['Heart Rate',
              'Temperature',
              'Carbon Monoxide',
              'Longitude',
              'Latitude',
              'Proximity']

    connection = sqlite3.connect('data.db')
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


@app.route('/tables')
def tables():
    labels = ['Heart Rate', 'Carbon Monoxide Levels',
              'Longitude', 'Latitude', 'Proximity', 'Thermal Array',
              'Image File']
    return render_template('tables.html', labels=labels)


@app.route('/notes')
def notes():
    return render_template('notifications.html')


@app.route('/user')
def user():
    return render_template('user.html')


@app.route('/black-dash')
def dashboard():
    return render_template('new-dashboard.html')


@app.route('/live-table')
def live_table():
    return render_template('tables.html')


@app.route('/map')
def map():
    conn = sqlite3.connect('data.db')
    cur = conn.execute('SELECT lat, lon FROM wearables '
                       'WHERE api_key = ? ORDER BY datetime DESC', ('GROUP3',))
    result = cur.fetchall()
    print(result)
    cur.close()
    conn.close()
    return render_template('map.html', coordinates=result)


@app.route('/init_device_conn/<api_key>')
def init_device_conn(api_key):
    # Sets Up IOT device initial connection with server
    # After successful connection, device info will be rendered on dashboard
    if api_key in API_KEYS:
        connection = sqlite3.connect('data.db')
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


@app.route('/history/<api_key>')
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

    connection = sqlite3.connect('data.db')
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


@app.route('/live/<api_key>')
def live_data(api_key):
    if api_key not in API_KEYS:
        return 'Invalid API Key'

    sensors = ['Temperature',
               'Carbon Dioxide Levels',
               'Latitude',
               'Longitude',
               'Proximity']
    return render_template('live.html', api_key=api_key, labels=sensors)


@app.route('/push/<api_key>/heart_rate=<hr>/temp=<temp>/co_levels=<co_levels>/lon=<lon>/lat=<lat>/proximity_sensor=<prox_sensor>/thermal_array=<thermal_array>',
           methods=['GET', 'POST'])
def push_data(api_key, hr, co_levels, lon, lat, prox_sensor):
    # This is an endpoint to send data from the IOT device to the database
    connection = sqlite3.connect('data.db')
    cur = connection.execute(
        'INSERT INTO wearables VALUES (:Id, :api_key, :hr, :co_levels, :lon, :lat, :prox_sensor, :datetime)', \
        {'Id': None, 'api_key': api_key, 'hr': hr, 'co_levels': co_levels,
         'lon': lon, 'lat': lat, 'prox_sensor': prox_sensor, 'datetime': str(datetime.datetime.now())[:19]})
    # connection.commit()
    cur.close()
    connection.close()
    # Returning the same data for verification purposes
    return {'api_key': api_key, 'hr': hr, 'co_levels': co_levels,
            'lon': lon, 'lat': lat, 'prox_sensor': prox_sensor, 'datetime': str(datetime.datetime.now())[:19]}


@app.route('/post_test', methods=['POST'])
def post_test():
    data = request.form.copy()
    if data['test']:
        return 'Successful Test Post | Value: ' + str(data['test'])
        print('Successful Test Post | Value:', request.form['test'])
    print('Not Successful')

@app.route('/push', methods=['POST'])
def mass_push():
    sensor_readings = request.form.copy()

    if sensor_readings['api_key'] not in API_KEYS:
        return 'Wrong API Key'

    temp = float(sensor_readings['temp'])
    sensor_readings['temp'] = temp * 1.8 + 32

    # try:
    #     temp = float(sensor_readings['temp'])
    #     sensor_readings['temp'] = temp * 1.8 + 32
    # except TypeError:
    #     return 'Can not convert temp to float'

    thermal = sensor_readings['thermal_array'].split(',')
    if len(thermal) != 16:
        return 'Improperly formatted'
    thermal = [math.floor(float(temp) * 1.8 + 32) for temp in thermal]
    thermal_str = ','.join([str(temp) for temp in thermal])
    sensor_readings['thermal_array'] = thermal_str

    # try:
    #     thermal = sensor_readings['thermal_array'].split(',')
    #     if len(thermal) != 16:
    #         return 'Improperly formatted'
    #     thermal = [math.floor(float(temp) * 1.8 + 32) for temp in thermal]
    #     thermal_str = ','.join([str(temp) for temp in thermal])
    #     sensor_readings['thermal_array'] = thermal_str
    # except TypeError:
    #     return 'Thermal data improperly formatted'

    image_file = request.files['image']
    filename = image_file.filename

    if filename == '':
        return 'No file received'

    file_prefix, file_ext = os.path.splitext(filename)
    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
        return 'Failed Upload. Extension: ' + file_ext

    sensor_readings['proximity_sensor'] = float(sensor_readings['proximity_sensor'])

    # try:
    #     sensor_readings['proximity_sensor'] = float(sensor_readings['proximity_sensor'])
    # except:
    #     sensor_readings['proximity_sensor'] = -1.0

    for key_needing_mods in ['temp', 'co_levels', 'lon', 'lat']:
        sensor_readings[key_needing_mods] = float(sensor_readings[key_needing_mods])

    random_name = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(15))
    image_file_path = os.path.join(app.config['UPLOAD_PATH'], secure_filename(random_name + file_ext))
    image_file.save(image_file_path)

    conn = sqlite3.connect('data.db')
    statement = 'INSERT INTO wearables VALUES (:Id, :api_key, :heart_rate, :temp, :co_level, :lat, :lon, :proximity_sensor, :temp_array, :image_path, :datetime)'
    data = {'Id': None,
            'api_key': sensor_readings['api_key'],
            'temp': sensor_readings['temp'],
            'heart_rate': sensor_readings['heart_rate'],
            'co_level': sensor_readings['co_levels'],
            'lat': sensor_readings['lat'],
            'lon': sensor_readings['lon'],
            'proximity_sensor': sensor_readings['proximity_sensor'],
            'temp_array': sensor_readings['thermal_array'],
            'image_path': image_file_path,
            'datetime': str(datetime.datetime.now())[:19]}

    cur = conn.execute(statement, data)
    conn.commit()
    cur.close()
    conn.close()
    return 'Success'


@app.route('/image/<api_key>', methods=['POST'])
def image_upload(api_key):
    if api_key in API_KEYS:
        image_file = request.files['file']
        filename = image_file.filename
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                return 'Failed Upload. Extension: ' + file_ext
            image_file.save(os.path.join(app.config['UPLOAD_PATH'], secure_filename(filename)))
        return 'Upload Success'
    return 'Upload Failed'


@app.route('/generate_video')
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
    print(os.listdir('templates'))
    return render_template('video.html')


@app.route('/uploads/<image>')
def image_retrieval(image):
    return send_from_directory(app.config['UPLOAD_PATH'], image)


@app.route('/view_video')
def sample_video():
    return render_template('video.html')


@app.route('/video/<video>')
def video_file(video):
    return send_from_directory('output', video)


if __name__ == '__main__':
    socketio.run()
