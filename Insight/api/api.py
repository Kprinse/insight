from flask import Blueprint, request, render_template
import sqlite3
import datetime

API_KEYS = ['TEST']

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/live/<api_key>')
def live_data(api_key):
    if api_key not in API_KEYS:
        return 'Invalid API Key'

    sensors = ['Temperature',
               'Carbon Dioxide Levels',
               'Latitude',
               'Longitude',
               'Proximity']
    return render_template('live.html', api_key=api_key, labels=sensors)


@api.route('/push/<api_key>/heart_rate=<hr>/temp=<temp>/co_levels=<co_levels>/lon=<lon>/lat=<lat>/proximity_sensor=<prox_sensor>/thermal_array=<thermal_array>',
           methods=['GET', 'POST'])
def push_data(api_key, hr, co_levels, lon, lat, prox_sensor):
    # This is an endpoint to send data from the IOT device to the database
    connection = sqlite3.connect('../../data.db')
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


@api.route('/post_test', methods=['POST'])
def post_test():
    data = request.form.copy()
    if data['test']:
        return 'Successful Test Post | Value: ' + str(data['test'])
        print('Successful Test Post | Value:', request.form['test'])
    print('Not Successful')

# @views.route('/push', methods=['POST'])
# def mass_push():
#     sensor_readings = request.form.copy()
#
#     if sensor_readings['api_key'] not in API_KEYS:
#         return 'Wrong API Key'
#
#     temp = float(sensor_readings['temp'])
#     sensor_readings['temp'] = temp * 1.8 + 32
#
#     # try:
#     #     temp = float(sensor_readings['temp'])
#     #     sensor_readings['temp'] = temp * 1.8 + 32
#     # except TypeError:
#     #     return 'Can not convert temp to float'
#
#     thermal = sensor_readings['thermal_array'].split(',')
#     if len(thermal) != 16:
#         return 'Improperly formatted'
#     thermal = [math.floor(float(temp) * 1.8 + 32) for temp in thermal]
#     thermal_str = ','.join([str(temp) for temp in thermal])
#     sensor_readings['thermal_array'] = thermal_str
#
#     # try:
#     #     thermal = sensor_readings['thermal_array'].split(',')
#     #     if len(thermal) != 16:
#     #         return 'Improperly formatted'
#     #     thermal = [math.floor(float(temp) * 1.8 + 32) for temp in thermal]
#     #     thermal_str = ','.join([str(temp) for temp in thermal])
#     #     sensor_readings['thermal_array'] = thermal_str
#     # except TypeError:
#     #     return 'Thermal data improperly formatted'
#
#     image_file = request.files['image']
#     filename = image_file.filename
#
#     if filename == '':
#         return 'No file received'
#
#     file_prefix, file_ext = os.path.splitext(filename)
#     if file_ext not in app.config['UPLOAD_EXTENSIONS']:
#         return 'Failed Upload. Extension: ' + file_ext
#
#     sensor_readings['proximity_sensor'] = float(sensor_readings['proximity_sensor'])
#
#     # try:
#     #     sensor_readings['proximity_sensor'] = float(sensor_readings['proximity_sensor'])
#     # except:
#     #     sensor_readings['proximity_sensor'] = -1.0
#
#     for key_needing_mods in ['temp', 'co_levels', 'lon', 'lat']:
#         sensor_readings[key_needing_mods] = float(sensor_readings[key_needing_mods])
#
#     random_name = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(15))
#     image_file_path = os.path.join(app.config['UPLOAD_PATH'], secure_filename(random_name + file_ext))
#     image_file.save(image_file_path)
#
#     conn = sqlite3.connect('data.db')
#     statement = 'INSERT INTO wearables VALUES (:Id, :api_key, :heart_rate, :temp, :co_level, :lat, :lon, :proximity_sensor, :temp_array, :image_path, :datetime)'
#     data = {'Id': None,
#             'api_key': sensor_readings['api_key'],
#             'temp': sensor_readings['temp'],
#             'heart_rate': sensor_readings['heart_rate'],
#             'co_level': sensor_readings['co_levels'],
#             'lat': sensor_readings['lat'],
#             'lon': sensor_readings['lon'],
#             'proximity_sensor': sensor_readings['proximity_sensor'],
#             'temp_array': sensor_readings['thermal_array'],
#             'image_path': image_file_path,
#             'datetime': str(datetime.datetime.now())[:19]}
#
#     cur = conn.execute(statement, data)
#     conn.commit()
#     cur.close()
#     conn.close()
#     return 'Success'


# @views.route('/image/<api_key>', methods=['POST'])
# def image_upload(api_key):
#     if api_key in API_KEYS:
#         image_file = request.files['file']
#         filename = image_file.filename
#         if filename != '':
#             file_ext = os.path.splitext(filename)[1]
#             if file_ext not in app.config['UPLOAD_EXTENSIONS']:
#                 return 'Failed Upload. Extension: ' + file_ext
#             image_file.save(os.path.join(app.config['UPLOAD_PATH'], secure_filename(filename)))
#         return 'Upload Success'
#     return 'Upload Failed'
