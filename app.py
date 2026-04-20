from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, session
import fitz  # PyMuPDF
import os, pikepdf, sqlite3
from authlib.integrations.flask_client import OAuth
from pdf2docx import Converter
import tabula
import pandas as pd

app = Flask(__name__)
app.secret_key = "SMART_PDF_DUBAI_SECRET_2026"

# --- Google OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='373127108649-eoqjtpanqoj2bvt6l5jovrglv52hucep.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Database & Folders Setup ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, name TEXT, email TEXT, profile_pic TEXT, plan TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Auth Routes ---
@app.route('/')
def index():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login')
def login():
    # මෙතන Redirect URI එක කෙළින්ම දීමෙන් 'invalid_client' error එක මගහරවා ගත හැක
    redirect_uri = 'http://127.0.0.1:5000/authorize'
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if user_info:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO users (id, name, email, profile_pic, plan) VALUES (?, ?, ?, ?, ?)",
                      (user_info['sub'], user_info['name'], user_info['email'], user_info['picture'], 'Free'))
            conn.commit()
            conn.close()
            session['user'] = user_info
        return redirect('/')
    except Exception as e:
        return f"Login Failed: {str(e)}", 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- PDF Tools Logic ---

@app.route('/merge', methods=['POST'])
def merge():
    try:
        files = request.files.getlist('pdfs')
        result = fitz.open()
        for file in files:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            with fitz.open(path) as m_pdf:
                result.insert_pdf(m_pdf)
        output = "merged_output.pdf"
        result.save(output)
        result.close()
        return send_file(output, as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/word', methods=['POST'])
def word():
    try:
        file = request.files.getlist('pdfs')[0]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        output = "output.docx"
        cv = Converter(path)
        cv.convert(output)
        cv.close()
        return send_file(output, as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/excel', methods=['POST'])
def export_excel():
    try:
        file = request.files.getlist('pdfs')[0]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        output = "output.csv"
        df_list = tabula.read_pdf(path, pages='all')
        if not df_list: return "No tables found!", 400
        tabula.convert_into(path, output, output_format="csv", pages='all')
        return send_file(output, as_attachment=True)
    except Exception as e:
        return "Java Required for Excel!", 500

@app.route('/protect', methods=['POST'])
def protect():
    try:
        file = request.files.getlist('pdfs')[0]
        password = request.form.get('password', '1234')
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        with pikepdf.open(path) as pdf:
            pdf.save("protected.pdf", encryption=pikepdf.Encryption(owner=password, user=password))
        return send_file("protected.pdf", as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/unlock', methods=['POST'])
def unlock():
    try:
        file = request.files.getlist('pdfs')[0]
        password = request.form.get('password')
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        with pikepdf.open(path, password=password) as pdf:
            pdf.save("unlocked.pdf")
        return send_file("unlocked.pdf", as_attachment=True)
    except Exception as e:
        return "Wrong Password!", 500

@app.route('/pagenumbers', methods=['POST'])
def pagenumbers():
    try:
        file = request.files.getlist('pdfs')[0]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            page.insert_text((550, 800), str(i + 1), fontsize=12)
        doc.save("numbered.pdf")
        doc.close()
        return send_file("numbered.pdf", as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/organize', methods=['POST'])
def organize():
    try:
        file = request.files.getlist('pdfs')[0]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        doc = fitz.open(path)
        doc[0].set_rotation(90)
        doc.save("organized.pdf")
        doc.close()
        return send_file("organized.pdf", as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/split', methods=['POST'])
def split():
    try:
        file = request.files.getlist('pdfs')[0]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        doc = fitz.open(path)
        result = fitz.open()
        result.insert_pdf(doc, from_page=0, to_page=0)
        result.save("split.pdf")
        doc.close()
        return send_file("split.pdf", as_attachment=True)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
