
from flask import Flask, render_template_string, request, jsonify, send_file, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import io
import datetime
import csv

app = Flask(__name__)
app.secret_key = 'cambia-esta-clave-por-una-segura'
DB_NAME = 'movimientos.db'

# ------------------ Inicialización DB ------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            dispositivo_id TEXT NOT NULL,
            usuario TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT
        )
    """)
    conn.commit()
    conn.close()

def ensure_admin():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = ?", ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password_hash, nombre) VALUES (?, ?, ?)",
                       ('admin', generate_password_hash('123456'), 'Administrador'))
        conn.commit()
    conn.close()

init_db()
ensure_admin()

# ------------------ Autenticación ------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ------------------ Plantillas ------------------
PAGE_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Iniciar session</title>
  /static/styles.css
</head>
<body>
  <header class="header">
    <div class="brand">Sistema de Movimientos CCTV & Contabilidad</div>
    <nav class="nav">
      {{ url_for(Iniciar session</a>
    </nav>
  </header>
  <main class="container">
    <section class="panel narrow">
      <h1>Iniciar session</h1>
      <form method="POST" class="form-grid">
        <div class="form-group">
          <label>Usuario</label>
          <input type="text" name="username" required />
        </div>
        <div class="form-group">
          <label>Contraseña</label>
          <input type="password" name="password" required />
        </div>
        <div class="form-actions">
          <button type="submit" class="btn-primary">Entrar</button>
        </div>
      </form>
      {% if error %}
        <p class="help" style="color:#fca5a5;">{{ error }}</p>
      {% else %}
        <p class="help">Usuario por defecto: <code>admin</code> / Contraseña: <code>123456</code></p>
      {% endif %}
    </section>
  </main>
  <footer class="footer">
    <small>© {{ current_year }} Sermaworld / A&A Servicios Contables</small>
  </footer>
</body>
</html>
"""

PAGE_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Registro y Reporte</title>
  /static/styles.css
</head>
<body>
  <header class="header">
    <div class="brand">Sistema de Movimientos CCTV & Contabilidad</div>
    <nav class="nav">
      {% if session.get('user') %}
        <span>Hola, {{ session.get('user_nombre') or session.get('user') }}</span>
        {{ url_for(Cerrar session</a>
      {% else %}
        {{ url_for(Iniciar session</a>
      {% endif %}
    </nav>
  </header>
  <main class="container">
    <section class="panel">
      <h1>Registrar Nuevo Movimiento</h1>
      <form id="movimientoForm" class="form-grid">
        <div class="form-group"><label>Fecha</label><input type="date" name="fecha" required /></div>
        <div class="form-group"><label>Tipo</label>
          <select name="tipo" required>
            <option value="">Seleccione...</option>
            <option value="Instalación">Instalación</option>
            <option value="Mantenimiento">Mantenimiento</option>
            <option value="Ajuste">Ajuste</option>
          </select>
        </div>
        <div class="form-group"><label>Descripción</label><textarea name="descripcion" required minlength="5"></textarea></div>
        <div class="form-group"><label>ID del dispositivo</label><input type="text" name="dispositivo_id" required /></div>
        <div class="form-group"><label>Usuario responsable</label><input type="text" name="usuario" required /></div>
        <div class="form-actions"><button type="submit" class="btn-primary">Guardar</button></div>
      </form>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h2>Reporte de Movimientos</h2>
        <div class="actions">
          /export/csvExportar CSV</a>
          /export/pdfExportar PDF</a>
        </div>
      </div>
      <form id="filtrosForm" class="filters-grid">
        <input type="date" name="desde" /><input type="date" name="hasta" />
        <select name="tipo"><option value="">Tipo</option><option value="Instalación">Instalación</option><option value="Mantenimiento">Mantenimiento</option><option value="Ajuste">Ajuste</option></select>
        <input type="text" name="dispositivo_id" placeholder="Dispositivo" />
        <input type="text" name="usuario" placeholder="Usuario" />
        <input type="text" name="q" placeholder="Buscar" />
        <button type="submit" class="btn">Filtrar</button>
        <button type="button" id="limpiarFiltros" class="btn">Limpiar</button>
      </form>
      <table id="reporte" class="table"><thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Descripción</th><th>Dispositivo</th><th>Usuario</th></tr></thead><tbody></tbody></table>
    </section>
  </main>
  <footer class="footer"><small>© {{ current_year }} Sermaworld / A&A Servicios Contables</small></footer>
  <script>
    function queryStringFromForm(form){const data=new FormData(form);const params=new URLSearchParams();for(const[k,v]of data.entries()){if(v&&v.trim()!=='')params.append(k,v.trim());}return params.toString();}
    function cargarReporte(params=''){const url=params?'/reporte?'+params:'/reporte';fetch(url).then(res=>res.json()).then(data=>{const tbody=document.querySelector('#reporte tbody');tbody.innerHTML='';data.forEach(row=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${row.id}</td><td>${row.fecha}</td><td>${row.tipo}</td><td>${row.descripcion}</td><td>${row.dispositivo_id}</td><td>${row.usuario}</td>`;tbody.appendChild(tr);});});}
    cargarReporte();
    document.getElementById('movimientoForm').addEventListener('submit',function(e){e.preventDefault();const formData=new FormData(this);fetch('/agregar',{method:'POST',body:formData}).then(res=>res.json()).then(data=>{alert(data.message);const params=queryStringFromForm(document.getElementById('filtrosForm'));cargarReporte(params);this.reset();});});
    document.getElementById('filtrosForm').addEventListener('submit',function(e){e.preventDefault();const params=queryStringFromForm(this);cargarReporte(params);});
    document.getElementById('limpiarFiltros').addEventListener('click',function(){document.getElementById('filtrosForm').reset();cargarReporte();});
  </script>
</body>
</html>
"""

# ------------------ Rutas ------------------
@app.route('/')
@login_required
def index():
    return render_template_string(PAGE_INDEX, current_year=datetime.datetime.now().year)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, nombre FROM usuarios WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row and check_password_hash(row[2], password):
            session['user'] = row[1]
            session['user_nombre'] = row[3]
            return redirect(url_for('index'))
        return render_template_string(PAGE_LOGIN, error='Usuario o contraseña inválidos', current_year=datetime.datetime.now().year)
    return render_template_string(PAGE_LOGIN, current_year=datetime.datetime.now().year)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    fecha = request.form.get('fecha')
    tipo = request.form.get('tipo')
    descripcion = request.form.get('descripcion')
    dispositivo_id = request.form.get('dispositivo_id')
    usuario = request.form.get('usuario')
    if not fecha or not tipo or not descripcion or not dispositivo_id or not usuario:
        return jsonify({'message': 'Todos los campos son obligatorios'}), 400
    if len(descripcion) < 5:
        return jsonify({'message': 'La descripción debe tener al menos 5 caracteres'}), 400
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO movimientos (fecha, tipo, descripcion, dispositivo_id, usuario) VALUES (?, ?, ?, ?, ?)',
                   (fecha, tipo, descripcion, dispositivo_id, usuario))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Movimiento agregado correctamente'})

def build_filters_query(params):
    where, values = [], []
    if params.get('desde'): where.append("date(fecha)>=date(?)"); values.append(params['desde'])
    if params.get('hasta'): where.append("date(fecha)<=date(?)"); values.append(params['hasta'])
    if params.get('tipo'): where.append("tipo=?"); values.append(params['tipo'])
    if params.get('dispositivo_id'): where.append("dispositivo_id LIKE ?"); values.append('%'+params['dispositivo_id']+'%')
    if params.get('usuario'): where.append("usuario LIKE ?"); values.append('%'+params['usuario']+'%')
    if params.get('q'): where.append("descripcion LIKE ?"); values.append('%'+params['q']+'%')
    sql = "SELECT * FROM movimientos" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC"
    return sql, values

@app.route('/reporte')
@login_required
def reporte():
    params = {k: request.args.get(k) for k in ['desde','hasta','tipo','dispositivo_id','usuario','q']}
    sql, values = build_filters_query(params)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql, values)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'id':r[0],'fecha':r[1],'tipo':r[2],'descripcion':r[3],'dispositivo_id':r[4],'usuario':r[5]} for r in rows])

@app.route('/export/csv')
@login_required
def export_csv():
    params = {k: request.args.get(k) for k in ['desde','hasta','tipo','dispositivo_id','usuario','q']}
    sql, values = build_filters_query(params)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql, values)
    rows = cursor.fetchall()
    conn.close()
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['ID','Fecha','Tipo','Descripción','Dispositivo','Usuario'])
    for r in rows: writer.writerow(r)
    return send_file(io.BytesIO(csv_buffer.getvalue().encode('utf-8')), as_attachment=True, download_name='reporte_movimientos.csv', mimetype='text/csv')

@app.route('/export/pdf')
@login_required
def export_pdf():
    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.pdfgen import canvas
    except ImportError:
        return jsonify({'message':'Instala reportlab: python -m pip install reportlab'}),501
    params = {k: request.args.get(k) for k in ['desde','hasta','tipo','dispositivo_id','usuario','q']}
    sql, values = build_filters_query(params)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql, values)
    rows = cursor.fetchall()
    conn.close()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    c.setFont("Helvetica-Bold",14); c.drawString(30,560,"Reporte de Movimientos"); c.setFont("Helvetica",10)
    headers=['ID','Fecha','Tipo','Descripción','Dispositivo','Usuario']; x=[30,90,180,270,520,620]
    for i,h in enumerate(headers): c.drawString(x[i],540,h)
    y=520
    for r in rows:
        vals=[str(r[0]),r[1],r[2],r[3],r[4],r[5]]
        for i,v in enumerate(vals): c.drawString(x[i],y,v[:60])
        y-=16
        if y<40:
            c.showPage(); c.setFont("Helvetica",10)
            for i,h in enumerate(headers): c.drawString(x[i],560,h)
            y=540
    c.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="reporte_movimientos.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    print("Servidor listo. Ejecuta: python -m flask --app app run")
