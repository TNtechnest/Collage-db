import os
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


def store_uploaded_file(file_storage, college_code, category):
    original_filename = secure_filename(file_storage.filename or "upload.bin")
    college_folder = secure_filename((college_code or "default").lower())
    category_folder = secure_filename(category.lower())
    relative_dir = Path(college_folder) / category_folder
    absolute_dir = Path(current_app.config["UPLOAD_FOLDER"]) / relative_dir
    os.makedirs(absolute_dir, exist_ok=True)

    stored_name = f"{uuid4().hex}_{original_filename}"
    relative_path = (relative_dir / stored_name).as_posix()
    file_storage.save(absolute_dir / stored_name)
    return original_filename, relative_path
