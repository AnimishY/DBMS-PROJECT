# config/uploads.py

from werkzeug.utils import secure_filename
import os

IMAGES = {'jpg', 'jpeg', 'png', 'gif'}

class UploadSet:
    def __init__(self, name, extensions):
        self.name = name
        self.extensions = extensions
        self.destination = None

    def save(self, storage, folder=''):
        filename = secure_filename(storage.filename)
        if not self.destination:
            raise ValueError("UploadSet destination not configured. Use 'configure_uploads(app, upload_set)'.")

        path = os.path.join(self.destination, folder, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        storage.save(path)
        return filename

    def _config(self, app, name):
        # Called internally by configure_uploads
        self.destination = app.config.get(f'{name.upper()}_DEST')

def configure_uploads(app, *upload_sets):
    for upload_set in upload_sets:
        upload_set._config(app, upload_set.name)

photos = UploadSet('photos', IMAGES)

