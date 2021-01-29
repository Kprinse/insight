from flask import Flask
from .views.views import views
from .api.api import api

def create_app(config=None):
    app = Flask(__name__)

    app.register_blueprint(views)
    app.register_blueprint(api)

    # app.config['UPLOAD_PATH'] = 'uploads'
    # app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
    # app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
    # app.secret_key = 'secret'

    # socketio = SocketIO(app)

    return app
