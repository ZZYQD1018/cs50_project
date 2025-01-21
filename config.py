import os

class Config:
    SECRET_KEY = os.urandom(24).hex()
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'project/static/uploads')
