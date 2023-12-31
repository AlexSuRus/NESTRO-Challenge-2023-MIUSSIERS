from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
import os
import uuid
from werkzeug.utils import secure_filename
import pandas as pd

from marketplace.auth import login_required, admin_only
from marketplace.db import get_db
from flask import render_template, flash, redirect, url_for
from .db import get_item_by_id


bp = Blueprint('store', __name__)
dir_path = os.path.dirname(os.path.realpath(__file__))
IMG_FOLDER = dir_path + '/static/img'
FILE_FOLDER = dir_path + '/static/files'


@bp.route('/')
def index():
    if not g.user:
        return redirect(url_for('auth.login'))
    db = get_db()

    db.execute('CREATE TABLE IF NOT EXISTS item (id INTEGER PRIMARY KEY AUTOINCREMENT,'
               'item_name TEXT NOT NULL,'
               'item_description TEXT,'
               'item_image BLOB,'
               'dataset_author TEXT NOT NULL,'
               'file_name TEXT NOT NULL,'
               'secured_name TEXT NOT NULL,'
               'original_file_name TEXT NOT NULL)')

    db.execute('CREATE TABLE IF NOT EXISTS cart (cart_id INTEGER PRIMARY KEY AUTOINCREMENT,'
               'user_id INTEGER NOT NULL,'
               'item_id INTEGER NOT NULL,'
               'FOREIGN KEY (user_id) REFERENCES user (id),'
               'FOREIGN KEY (item_id) REFERENCES item (id))')

    items = db.execute(
        'SELECT *'
        ' FROM item i'
    ).fetchall()

    return render_template('store/index.html', items=items, title=None)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
# @admin_only
def create():
    if request.method == 'POST':
        data = request.values.to_dict()
        item_name = data["item_name"]
        item_description = data["item_description"]
        item_image = request.files["item_image"]
        item_file = request.files["item_file"]
        errors = []
        dataset_author = data["dataset_author"]

        if len(item_file.filename) != 0:
            secure_filename(item_file.filename)
            secured_name = uuid.uuid4().hex
            file_name = secured_name + '.'+(item_file.filename.split('.')[-1])
            original_file_name = file_name

            item_file.save(os.path.join(FILE_FOLDER, file_name))
            if (item_file.filename.split('.')[-1]) == "xlsx":
                data = pd.read_excel(os.path.join(FILE_FOLDER, file_name))
                PATH = os.path.join(FILE_FOLDER, secured_name)
                data.to_csv(PATH+'.csv', index=False)
                file_name = secured_name + '.csv'

        else:
            error = 'Нужно выбрать файл с данными'
            errors.append(error)
            flash(error)

        if not item_description:
            error = 'Описание обязательно'
            errors.append(error)
            flash(error)
        if not item_image:
            error = 'Изображение обязательно'
            errors.append(error)
            flash(error)
        if not item_file:
            error = 'Набор данных обязателен'
            errors.append(error)
            flash(error)

        if item_image:
            secure_filename(item_image.filename)
            item_image.save(os.path.join(IMG_FOLDER, item_image.filename))

        if not item_name:
            error = 'Заголовок обязателен'
            errors.append(error)
            flash(error)
        else:
            try:
                db = get_db()
                db.execute(
                    'INSERT INTO item (item_name, item_description, item_image, dataset_author, secured_name, file_name, original_file_name)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (item_name, item_description, item_image.filename,
                     dataset_author, secured_name, file_name, original_file_name)
                )
                db.commit()

                flash(item_name + ' was added to the store', 'success')
            except:
                return render_template('store/create.html', errors=errors)

    return render_template('store/create.html')


@bp.route('/delete_cart_item/<int:item_id>', methods=['POST'])
@login_required
@admin_only
def delete(item_id):
    db = get_db()
    db.execute('DELETE FROM item WHERE id = ?', [item_id])
    db.commit()
    return redirect(url_for('store.index'))


@bp.route('/store/item/<int:item_id>')
def view_item(item_id):
    item = get_item_by_id(item_id)
    if item:
        return render_template('store/item.html', item=item)
    flash('Item not found')
    return redirect(url_for('store.index'))
