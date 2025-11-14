from flask import Flask, render_template, request, redirect, url_for, abort
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from flask import current_app

from secret import secret_key
from api import api  # importa il Blueprint delle API
from utils import *

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
app.register_blueprint(api)
from api import load_parcheggi, load_linee

# Flask-Login setup - impostiamo la pagina di login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# ------------------CLASSE USER-----------------------
class User(UserMixin):
    def __init__(self, id, email, ruolo):
        self.id = id
        self.email = email
        self.ruolo = ruolo

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connectionUtenti()
        user = conn.execute("SELECT * FROM utenti WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if user:
            return User(id=user["id"], email=user["email"], ruolo=user["ruolo"])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# -----------------ROTTE PRINCIPALI--------------------
@app.route('/')
def home():
    return redirect(url_for('login'))

# ------------------- LOGIN UTENTE --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connectionUtenti()
        user = conn.execute("SELECT * FROM utenti WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and user["password"] == password:  # 🔓 password in chiaro
            user_obj = User(id=user["id"], email=user["email"], ruolo=user["ruolo"])
            login_user(user_obj)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('mappa_page'))
        else:
            return render_template('login.html', error="Credenziali non valide")

    return render_template('login.html')


# ------------------- LOGOUT --------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ------------------- LOGIN ADMIN ---------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connectionUtenti()
        admin = conn.execute(
            "SELECT * FROM utenti WHERE email = ? AND ruolo = 'admin'", (email,)
        ).fetchone()
        conn.close()

        if admin and admin["password"] == password:
            user_obj = User(id=admin["id"], email=admin["email"], ruolo=admin["ruolo"])
            login_user(user_obj)
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Credenziali amministratore non valide")

    return render_template('admin_login.html')


# ------------------- DASHBOARD ADMIN -----------------
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.ruolo != 'admin':
        abort(403)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        ruolo = request.form.get('ruolo', 'user')

        conn = get_db_connectionUtenti()
        try:
            conn.execute(
                "INSERT INTO utenti (email, password, ruolo) VALUES (?, ?, ?)",
                (email, password, ruolo),
            )
            conn.commit()
            message = "Utente aggiunto con successo!"
        except sqlite3.IntegrityError:
            message = "Errore: utente già esistente!"
        conn.close()

        return render_template('admin_dashboard.html', success=message)

    return render_template('admin_dashboard.html')


# ------------------- GESTIONE UTENTI -----------------
@app.route('/admin/utenti', methods=['GET', 'POST'])
@login_required
def gestione_utenti():
    if current_user.ruolo != 'admin':
        abort(403)

    conn = get_db_connectionUtenti()

    if request.method == 'POST':
        utente_id = request.form.get('utente_id')
        conn.execute("DELETE FROM utenti WHERE id = ?", (utente_id,))
        conn.commit()

    utenti = conn.execute("SELECT * FROM utenti").fetchall()
    conn.close()

    return render_template('gestione_utenti.html', utenti=utenti)

#------------------ MAP ---------------------

# Endpoint to render the map page
@app.route('/mappa')
@login_required
def mappa_page():
    # Il ruolo è già salvato nell'oggetto Flask-Login
    is_admin = (current_user.ruolo == 'admin')
    return render_template('map.html', is_admin=is_admin)


#---------------- PARCHEGGI -----------------

# Interfaccia per gestire i parcheggi
@app.route('/parcheggi_page')
@login_required
def parcheggi_page():
    return render_template('parcheggi.html')

# redirect a pagina parcheggi
@app.route('/parcheggi')
def parcheggi_redirect():
    return redirect(url_for('parcheggi_page'))


# ---------------- LINEE BUS -----------------

# Pagina principale (HTML)
@app.route('/linee_page')
@login_required
def linee_page():
    return render_template('linee.html')


# Redirect per /linee → /linee_page
@app.route('/linee')
def linee_redirect():
    return redirect(url_for('linee_page'))


# ---------------- SIMULAZIONI ---------------

@app.route('/simulazioni')
@login_required
def simulazioni():
    return render_template("simulazioni.html")


@app.route('/simulazioni/<sim_id>')
def simulazione_dettaglio(sim_id):
    with current_app.test_client() as client:
        response = client.get(f"/api/simulazioni/{sim_id}")
        if response.status_code != 200:
            return "Errore nel recupero della simulazione", 404
        data = response.get_json()

    return render_template("simulazioni_dettaglio.html", simulazione=data)


# ---------------- PREVISIONE ---------------

@app.route("/previsioni")
@login_required
def previsioni_page():
    """Pagina HTML per visualizzare le previsioni turistiche."""
    return render_template("previsioni.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

def previsione_mese(anno=2025, mese=7):
    """
    Esegue la chiamata all'endpoint /api/predizioni per Dozza intera.
    (Usata per test o per generare i dati da backend)
    """
    client = app.test_client()
    response = client.post("/api/predizioni", json={"anno": anno, "mese": mese})
    print(response.json)
    return response.json

