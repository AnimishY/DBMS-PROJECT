# flask_uploads_patch.py
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

def configure_uploads(app, upload_sets):
    for name, upload_set in upload_sets.items():
        upload_set._config(app, name)
