import os, zipfile
from libs.utils import create_table_statement, create_dir, remove_dir, extract_kmz, create_inserts, \
    create_dir_structure, create_table_agregator

from flask import Flask, flash, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from random import getrandbits

# UPLOAD_FOLDER = './input_post'
ALLOWED_EXTENSIONS = {'zip'}

app = Flask(__name__)
app.config[
    'UPLOAD_FOLDER'] = 'in'  # TODO: Olhar como vou implementar as pastas para não gerar race conditions e permitir multiplos acessos
app.config['TEMP_FOLDER'] = 'temp'
app.config['OUT_FOLDER'] = 'out'
# create_dir(app.config['OUT_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS





@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'table' not in request.form and 'buffer' not in request.form:
            flash('POST sem nome e tamanho do buffer!')
            return redirect(request.url)

        folder_name_hash_id = str(getrandbits(32))
        upload_folder = './temp/' + folder_name_hash_id + '/' + app.config['UPLOAD_FOLDER']
        temp_folder = './temp/' + folder_name_hash_id + '/' + app.config['TEMP_FOLDER']
        out_folder = './temp/' + folder_name_hash_id + '/' + app.config['OUT_FOLDER']
        create_dir_structure(app, folder_name_hash_id)
        table_name = request.form['table']
        buffer = int( request.form['buffer'])
        if 'file' not in request.files:
            flash('Sem parte arquivo!')
            return redirect(request.url)
        file = request.files['file']
        filename = secure_filename(file.filename)
        if filename == '':
            flash('Arquivo não escolhido!')
            return redirect(request.url)

        if allowed_file(filename):
            file.save(os.path.join(upload_folder, filename))

            with zipfile.ZipFile(os.path.join(upload_folder, filename), 'r') as zip_ref:
                zip_ref.extractall(upload_folder)
                os.remove(os.path.join(upload_folder, filename))

            extract_kmz(upload_folder, temp_folder)
            sql_inserts = create_inserts(temp_folder, table_name, buffer)
            remove_dir(upload_folder)
            remove_dir(temp_folder)

            with open(out_folder + '/' + 'insert.sql', 'w+') as f:
                f.write('BEGIN;\n')
                f.write(create_table_statement(table_name, True))
                f.write('\n'.join(sql_inserts))
                f.write(create_table_statement(table_name, False))
                f.write(create_table_agregator(table_name))
                f.write('COMMIT;\n')

            return redirect('/uploads/' + folder_name_hash_id + '/out/' + 'insert.sql')

    return '''
    <!doctype html>
    <title>Carregar arquivo KML</title>
    <h1>Carregar arquivos KML</h1>
    <form method=post enctype=multipart/form-data>
      <input required type=file name=file> </br></br>
      <label for='buffer'>Tamanho do buffer:</lable>
      <input type='text' name='buffer' value='0'> </br></br>
      <label for='table'>Nome da tabela:</lable>
      <input required type='text' name='table'> </br></br>
      <input type=submit value=Upload> </br>
    </form>
    '''


@app.route('/uploads/<foldername>/out/<filename>', methods=['GET', 'POST'])
def uploaded_file(foldername, filename):
    return send_from_directory(os.path.join('temp', foldername,'out' ),
                               filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')