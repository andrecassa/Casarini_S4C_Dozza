from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from google.cloud import firestore
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.distance import geodesic
from datetime import datetime
import uuid
from secret import secret_key

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key

# Flask-Login setup - impostiamo la pagina di login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

    @staticmethod
    def get(user_id):
        doc = db.collection('utenti').document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return User(id=doc.id, email=data['email'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Firestore client
db = firestore.Client.from_service_account_json('credentials.json', database='mobility-dozza')

# Appena apro l'applicazione reindirizza alla pagina di login
@app.route('/')
def home():
    return redirect(url_for('mappa_page'))

#-------------- AUTHENTICATION ---------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # Recupera l'utente da Firestore
        utenti = db.collection('utenti').where('email', '==', email).stream()
        user = None
        for doc in utenti:
            data = doc.to_dict()
            if check_password_hash(data.get('password'), password):  # password è quella inserita dall'utente
                user = User(id=doc.id, email=email)
                break
        if user:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('mappa_page'))
        else:
            return render_template('login.html', error="Credenziali non valide")
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        utenti = db.collection('utenti').where('email', '==', email).where('ruolo', '==', 'admin').stream()
        user = None
        for doc in utenti:
            data = doc.to_dict()
            print("DEBUG admin_login:", data)  # STAMPA DI DEBUG
            if check_password_hash(data.get('password'), password):  # <-- usa check_password_hash!
                user = User(id=doc.id, email=email)
                break
        if user:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Credenziali amministratore non valide")
    return render_template('admin_login.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    # Consenti solo all'admin
    utenti = db.collection('utenti').document(current_user.id).get()
    #print("DEBUG admin_dashboard:", utenti.to_dict())
    if not utenti.exists or utenti.to_dict().get('ruolo') != 'admin':
        abort(403)
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        ruolo = request.form.get('ruolo', 'user')
        hashed_password = generate_password_hash(password)  # password è quella in chiaro
        db.collection('utenti').add({
            'email': email,
            'password': hashed_password,
            'ruolo': ruolo
        })
        return render_template('admin_dashboard.html', success="Utente aggiunto!")
    return render_template('admin_dashboard.html')

@app.route('/admin/utenti', methods=['GET', 'POST'])
@login_required
def gestione_utenti():
    # Consenti solo all'admin
    utenti_doc = db.collection('utenti').document(current_user.id).get()
    if not utenti_doc.exists or utenti_doc.to_dict().get('ruolo') != 'admin':
        abort(403)

    # Elimina utente se richiesto
    if request.method == 'POST':
        utente_id = request.form.get('utente_id')
        if utente_id:
            db.collection('utenti').document(utente_id).delete()

    # Recupera tutti gli utenti
    utenti = []
    for doc in db.collection('utenti').stream():
        data = doc.to_dict()
        data['id'] = doc.id
        utenti.append(data)
    return render_template('gestione_utenti.html', utenti=utenti)

#------------------ MAP ---------------------

# Endpoint to render the map page
@app.route('/mappa')
@login_required
def mappa_page():
    ruolo = None
    user_doc = db.collection('utenti').document(current_user.id).get()
    if user_doc.exists:
        ruolo = user_doc.to_dict().get('ruolo')
    is_admin = (ruolo == 'admin')
    return render_template('map.html', is_admin=is_admin)

# Endpoint for map data: returns active parking lots and transport lines
@app.route('/mappa/dati', methods=['GET'])
@login_required
def mappa_dati():
    # Fetch active parking lots from Firestore
    parks_ref = db.collection('parcheggi')
    parks_query = parks_ref.where('attivo', '==', True).stream()
    parcheggi = []
    for doc in parks_query:
        data = doc.to_dict()
        data['id'] = doc.id
        # Conversione lat/lon se sono stringhe con la virgola
        if isinstance(data['latitudine'], str):
            data['latitudine'] = float(data['latitudine'].replace(',', '.'))
        if isinstance(data['longitudine'], str):
            data['longitudine'] = float(data['longitudine'].replace(',', '.'))
        parcheggi.append(data)

    # Fetch active transport lines from Firestore
    lines_ref = db.collection('linee_bus')
    parks_query = lines_ref.where('attivo', '==', True).stream()
    linee_bus = []
    for doc in parks_query:
        data = doc.to_dict()
        data['id'] = doc.id


        # Conversione lat/lon se sono stringhe con la virgola
        if isinstance(data['partenza_lat'], str):
            data['partenza_lat'] = float(data['partenza_lat'].replace(',', '.'))
        if isinstance(data['partenza_lng'], str):
            data['partenza_lng'] = float(data['partenza_lng'].replace(',', '.'))
        if isinstance(data['arrivo_lat'], str):
            data['arrivo_lat'] = float(data['arrivo_lat'].replace(',', '.'))
        if isinstance(data['arrivo_lng'], str):
            data['arrivo_lng'] = float(data['arrivo_lng'].replace(',', '.'))
    
        linee_bus.append(data)
    

    
    #print('parcheggi:', parcheggi)
    #print()
    #print('linee_bus:', linee_bus)

    # Return combined data as JSON

    return jsonify({
        'parcheggi': parcheggi,
        'linee_trasporto': linee_bus
    })


#---------------- PARCHEGGI -----------------

PARCHEGGI_COLLECTION = 'parcheggi'

# Interfaccia per gestire i parcheggi
@app.route('/parcheggi_page')
@login_required
def parcheggi_page():
    return render_template('parcheggi.html')

# GET tutti i parcheggi
@app.route('/parcheggi', methods=['GET'])
def parcheggi_redirect():
    return redirect(url_for('parcheggi_page'))

# Restituisce i dati in JSON, usata solo in JS; recupera i dati da Firestore
@app.route('/api/parcheggi', methods=['GET'])
def get_parcheggi():
    docs = db.collection(PARCHEGGI_COLLECTION).stream()
    parcheggi = []
    for doc in docs:
        p = doc.to_dict()
        p['id'] = doc.id
        parcheggi.append(p)
    return jsonify(parcheggi)

#GET un parcheggio specifico
@app.route('/api/parcheggi/<id>', methods=['GET'])
def get_parcheggio(id):
    doc = db.collection(PARCHEGGI_COLLECTION).document(id).get()
    if doc.exists:
        parcheggio = doc.to_dict()
        parcheggio['id'] = doc.id
        return jsonify(parcheggio)
    else:
        return jsonify({'error': 'Parcheggio non trovato'}), 404

# POST nuovo parcheggio
@app.route('/api/parcheggi', methods=['POST'])
def add_parcheggio():
    data = request.json
    parcheggio_id = str(uuid.uuid4())
    db.collection(PARCHEGGI_COLLECTION).document(parcheggio_id).set(data)
    return jsonify({"id": parcheggio_id}), 201

# PUT modifica parcheggio
@app.route('/api/parcheggi/<id>', methods=['PUT'])
def update_parcheggio(id):
    data = request.json
    db.collection(PARCHEGGI_COLLECTION).document(id).update(data)
    return jsonify({"success": True})

# DELETE parcheggio
@app.route('/api/parcheggi/<id>', methods=['DELETE'])
def delete_parcheggio(id):
    db.collection(PARCHEGGI_COLLECTION).document(id).delete()
    return jsonify({"success": True})


#---------------- LINEE BUS -----------------

LINEE_COLLECTION = 'linee_bus'

@app.route('/linee_page')
@login_required
def linee_page():
    return render_template('linee.html')

# GET tutte le linee (redirect alla pagina)
@app.route('/linee', methods=['GET'])
def linee_redirect():
    return redirect(url_for('linee_page'))

# Restituisce i dati in JSON, usata solo in JS
@app.route('/api/linee', methods=['GET'])
def get_linee():
    docs = db.collection(LINEE_COLLECTION).stream()
    linee = []
    for doc in docs:
        l = doc.to_dict()
        l['id'] = doc.id
        linee.append(l)
    return jsonify(linee)

# GET una singola linea
@app.route('/api/linee/<id>', methods=['GET'])
def get_linea(id):
    doc = db.collection(LINEE_COLLECTION).document(id).get()
    if doc.exists:
        linea = doc.to_dict()
        linea['id'] = doc.id
        return jsonify(linea)
    else:
        return jsonify({'error': 'Linea non trovata'}), 404

# POST nuova linea
@app.route('/api/linee', methods=['POST'])
def add_linea():
    data = request.json
    linea_id = str(uuid.uuid4())
    db.collection(LINEE_COLLECTION).document(linea_id).set(data)
    return jsonify({"id": linea_id}), 201

# PUT modifica linea
@app.route('/api/linee/<id>', methods=['PUT'])
def update_linea(id):
    data = request.json
    db.collection(LINEE_COLLECTION).document(id).update(data)
    return jsonify({"success": True})

# DELETE linea
@app.route('/api/linee/<id>', methods=['DELETE'])
def delete_linea(id):
    db.collection(LINEE_COLLECTION).document(id).delete()
    return jsonify({"success": True})

#---------------- SIMULAZIONI ---------------


def run_simulazione(data, n_turisti, parcheggi_esclusi_ids, linee_escluse_ids):
    # Recupera tutti i parcheggi e linee dal DB
    all_parcheggi_docs = list(db.collection('parcheggi').stream())
    all_linee_docs = list(db.collection('linee_bus').stream())

    # Crea le liste dei parcheggi e delle linee escluse
    parcheggi_esclusi = []
    for doc in all_parcheggi_docs:
        if doc.id in parcheggi_esclusi_ids:
            p = doc.to_dict()
            p['id'] = doc.id
            parcheggi_esclusi.append(p)

    linee_escluse = []
    for doc in all_linee_docs:
        if doc.id in linee_escluse_ids:
            l = doc.to_dict()
            l['id'] = doc.id
            linee_escluse.append(l)

    # Filtra solo quelli NON esclusi
    parcheggi = []
    for doc in all_parcheggi_docs:
        if doc.id not in parcheggi_esclusi_ids:
            p = doc.to_dict()
            p['id'] = doc.id
            parcheggi.append(p)

    linee = []
    for doc in all_linee_docs:
        if doc.id not in linee_escluse_ids:
            l = doc.to_dict()
            l['id'] = doc.id
            linee.append(l)

    # Esegui la simulazione
    output = ottimizza_risorse(parcheggi, linee, n_turisti)
    risultato = output['risultato']
    parcheggi_usati = output['parcheggi_usati']
    linee_usate = output['linee_usate']

    #salva la simulazione nel database
    sim_id = str(uuid.uuid4())
    sim_doc = {
        'id': sim_id,
        'data': data,
        'n_turisti': n_turisti,
        'parcheggi': parcheggi_usati,  # solo quelli usati
        'linee': linee_usate,          # solo quelle usate
        'risultato': risultato,
        'timestamp': datetime.now(),
        'parcheggi_esclusi': parcheggi_esclusi,  # lista di dict dei parcheggi esclusi
        'linee_escluse': linee_escluse,          # lista di dict delle linee escluse
    }
    db.collection('simulazioni').document(sim_id).set(sim_doc)
    return sim_id, sim_doc


@app.route('/api/sim', methods=['POST'])
def api_simulazione():
    data = request.json.get('data')
    n_turisti = request.json.get('n_turisti', 0)
    parcheggi_esclusi_ids = request.json.get('parcheggi_esclusi', [])
    linee_escluse_ids = request.json.get('linee_escluse', [])

    if not data or n_turisti <= 0:
        return jsonify({'error': 'Dati non validi'}), 400

    sim_id, sim_doc = run_simulazione(data, n_turisti, parcheggi_esclusi_ids, linee_escluse_ids)
    return jsonify({'id': sim_id, 'simulazione': sim_doc}), 201


@app.route('/simulazioni', methods=['GET', 'POST'])
@login_required
def simulazioni():
    if request.method == 'POST':
        data = request.form.get('data')
        n_turisti = int(request.form.get('n_turisti'))

        # Ottieni gli ID selezionati dal form (da escludere)
        parcheggi_esclusi_ids = request.form.getlist('parcheggi_esclusi[]')
        # Ottieni gli ID delle linee escluse
        linee_escluse_ids = request.form.getlist('linee_escluse[]')

        sim_id, sim_doc = run_simulazione(data, n_turisti, parcheggi_esclusi_ids, linee_escluse_ids)
        return redirect(url_for('simulazione_dettaglio', sim_id=sim_id))

    # GET: mostra elenco simulazioni e tutti i parcheggi/linee per il form
    simulazioni = [doc.to_dict() for doc in db.collection('simulazioni').stream()]
    parcheggi = [doc.to_dict() | {'id': doc.id} for doc in db.collection('parcheggi').stream()]
    linee = [doc.to_dict() | {'id': doc.id} for doc in db.collection('linee_bus').stream()]
    return render_template('simulazioni.html', simulazioni=simulazioni, parcheggi=parcheggi, linee=linee)


@app.route('/simulazioni/<sim_id>')
def simulazione_dettaglio(sim_id):
    #Dettaglio di una singola simulazione
    doc = db.collection('simulazioni').document(sim_id).get()
    if not doc.exists:
        return "Simulazione non trovata", 404
    simulazione = doc.to_dict()

    # Assicura che i campi siano almeno inizializzati come vuoti
    simulazione['parcheggi'] = simulazione.get('parcheggi', [])
    simulazione['linee'] = simulazione.get('linee', [])
    simulazione['risultato'] = simulazione.get('risultato', {})

    return render_template('simulazioni_dettaglio.html', simulazione=simulazione)

@app.route('/simulazioni/elimina/<sim_id>', methods=['POST'])
@login_required
def elimina_simulazione(sim_id):
    db.collection('simulazioni').document(sim_id).delete()
    return redirect(url_for('simulazioni'))
    
@app.route('/simulazioni/esporta', methods=['POST'])
def simulazioni_esporta():
    # Ricevi i dati della simulazione da esportare
    sim_data = request.json # Dati in formato JSON
    sim_id = sim_data.get('id', str(uuid.uuid4())) # Genera un nuovo ID se non presente
    db.collection('simulazioni').document(sim_id).set(sim_data) # Salva la simulazione nel database
    return jsonify({'status': 'ok', 'id': sim_id})

# Funzione di ottimizzazione (stub da implementare)
def ottimizza_risorse(parcheggi, linee, n_turisti):
    # TODO: implementa la logica di ottimizzazione
    # Esempio: assegna turisti ai parcheggi in modo uniforme
    risultato = {}
    if parcheggi:
        per_parcheggio = n_turisti // len(parcheggi) #  turisti per parcheggio
        for p in parcheggi:
            risultato[p['nome']] = min(per_parcheggio, p.get('capienza', 0)) # assicurati di non superare la capienza
    return risultato


def sono_vicini(lat1, lng1, lat2, lng2, soglia_m=1000):
    """Restituisce True se la distanza tra i due punti è minore della soglia (in metri)."""
    return geodesic((lat1, lng1), (lat2, lng2)).meters <= soglia_m

DOZZA_COORDS = (44.3511, 11.6519)

def ottimizza_risorse(parcheggi, linee, n_turisti):
    risultato = {}
    assegnati = 0 # Numero di turisti già assegnati, inizialmente 0
    parcheggi_usati = []
    linee_usate = set()

    # Mappa parcheggio_id → linee collegate
    linee_per_parcheggio = {}
    for p in parcheggi:
        lat_p = float(str(p['latitudine']).replace(',', '.'))
        lng_p = float(str(p['longitudine']).replace(',', '.'))
        for linea in linee:
            lat_l = float(str(linea['partenza_lat']).replace(',', '.'))
            lng_l = float(str(linea['partenza_lng']).replace(',', '.'))
            if sono_vicini(lat_p, lng_p, lat_l, lng_l, soglia_m=1000):
                linee_per_parcheggio.setdefault(p['id'], []).append(linea)

    # Calcola distanza da Dozza per ogni parcheggio
    parcheggi_distanze = []
    for p in parcheggi:
        coords = (
            float(str(p['latitudine']).replace(',', '.')),
            float(str(p['longitudine']).replace(',', '.'))
        )
        distanza = geodesic(coords, DOZZA_COORDS).meters
        parcheggi_distanze.append((p, distanza))

    # Ordina parcheggi dal più vicino
    parcheggi_distanze.sort(key=lambda x: x[1])

    for parcheggio, distanza in parcheggi_distanze:
        if assegnati >= n_turisti:
            break

        capienza_p = parcheggio.get('capienza', 0)
        if capienza_p <= 0:
            continue

        turisti_restanti = n_turisti - assegnati
        turisti_assegnati_parcheggio = 0
        linee_usate_parcheggio = []

        # Trova tutte le linee associate ordinate per distanza arrivo
        linee_assoc = linee_per_parcheggio.get(parcheggio['id'], [])
        linee_assoc = sorted(linee_assoc, key=lambda l: geodesic(
            (float(str(l['arrivo_lat']).replace(',', '.')), float(str(l['arrivo_lng']).replace(',', '.'))), DOZZA_COORDS).meters)

        for linea in linee_assoc:
            capienza_linea = linea.get('capienza', 0)
            viaggi = linea.get('viaggi', 1)
            capienza_totale_linea = capienza_linea * viaggi
            if capienza_totale_linea <= 0:
                continue

            # Quanti turisti posso ancora mandare su questa linea?
            turisti_su_linea = min(turisti_restanti, capienza_p, capienza_totale_linea)
            if turisti_su_linea > 0:
                linee_usate.add(linea['id'])
                linee_usate_parcheggio.append({
                    'linea_id': linea['id'],
                    'turisti': turisti_su_linea
                })
                turisti_assegnati_parcheggio += turisti_su_linea
                assegnati += turisti_su_linea
                turisti_restanti -= turisti_su_linea
                capienza_p -= turisti_su_linea
            if assegnati >= n_turisti or capienza_p <= 0 or turisti_restanti <= 0:
                break

        # Se non ci sono linee associate, puoi comunque assegnare i turisti (caso parcheggio senza linea)
        if not linee_assoc and capienza_p > 0 and turisti_restanti > 0:
            turisti_da_inviare = min(turisti_restanti, capienza_p)
            turisti_assegnati_parcheggio += turisti_da_inviare
            assegnati += turisti_da_inviare
            capienza_p -= turisti_da_inviare

        if turisti_assegnati_parcheggio > 0:
            risultato[parcheggio['nome']] = turisti_assegnati_parcheggio
            parcheggio_copy = parcheggio.copy()
            parcheggio_copy['linee_usate'] = linee_usate_parcheggio  # lista di dict {linea_id, turisti}
            parcheggi_usati.append(parcheggio_copy)

        if assegnati >= n_turisti:
            break

    # Filtra solo le linee effettivamente usate
    linee_utilizzate = [l for l in linee if l['id'] in linee_usate]

    return {
        'risultato': risultato,
        'parcheggi_usati': parcheggi_usati,
        'linee_usate': linee_utilizzate
    }


# Run the Flask app on port 8080
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

