import os
import uuid
import joblib

from flask import Blueprint, request, jsonify, json, send_file
from geopy.distance import geodesic

from utils import *

api = Blueprint('api', __name__)

#------------------------MAPPA API------------------------------
@api.route('/api/mappa/dati', methods=['GET'])
def mappa_dati():
    try:
        # Ottengo Linee e Parcheggi
        parcheggi = load_parcheggi()
        linee = load_linee()

        # filtro solo quelli attivi:
        parcheggi_attivi = [p for p in parcheggi if p.get("attivo") == 1]
        linee_attive = [l for l in linee if l.get("attiva") == 1]

        # Trasformo le coordinate in float "puliti"
        for p in parcheggi_attivi:
            if isinstance(p["latitudine"], str):
                p["latitudine"] = float(p["latitudine"].replace(",", "."))
            if isinstance(p["longitudine"], str):
                p["longitudine"] = float(p["longitudine"].replace(",", "."))

        for l in linee_attive:
            for campo in ["partenza_lat", "partenza_lng", "arrivo_lat", "arrivo_lng"]:
                if isinstance(l[campo], str):
                    l[campo] = float(l[campo].replace(",", "."))

        # Ritorno JSON unico
        return jsonify({
            "parcheggi": parcheggi_attivi,
            "linee_trasporto": linee_attive
        })

    except Exception as e:
        print("Errore in mappa_dati:", e)
        return jsonify({"error": str(e)}), 500

#------------------------PARCHEGGI API------------------------------

#se voglio una lista di parcheggi come una lista dei dati e non un json
def load_parcheggi():
    conn = get_db_connectionParcheggi()
    rows = conn.execute("SELECT * FROM parcheggi").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Restituisce tutti i parcheggi in JSON
@api.route('/api/parcheggi', methods=['GET'])
def get_parcheggi():
    parcheggi = load_parcheggi()
    return jsonify(parcheggi)


# GET un parcheggio specifico
@api.route('/api/parcheggi/<id>', methods=['GET'])
def get_parcheggio(id):
    conn = get_db_connectionParcheggi()
    row = conn.execute("SELECT * FROM parcheggi WHERE id = ?", (id,)).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    else:
        return jsonify({'error': 'Parcheggio non trovato'}), 404

# POST nuovo parcheggio
@api.route('/api/parcheggi', methods=['POST'])
def add_parcheggio():
    data = request.json
    try:
        nome = str(data.get("nome", ""))
        comune = str(data.get("comune", ""))
        capienza = int(data.get("capienza", 0))
        attivo = 1 if data.get("attivo") in [True, "true", "1", 1] else 0
        latitudine = float(str(data.get("latitudine", "0")).replace(",", "."))
        longitudine = float(str(data.get("longitudine", "0")).replace(",", "."))

        conn = sqlite3.connect("databases/parcheggi.db")
        conn.execute(
            "INSERT INTO parcheggi (nome, comune, capienza, attivo, latitudine, longitudine) VALUES (?, ?, ?, ?, ?, ?)",
            (nome, comune, capienza, attivo, latitudine, longitudine),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True}), 201

    except Exception as e:
        print("Errore in add_parcheggio:", e, " -- Dati ricevuti:", data)
        return jsonify({"error": str(e)}), 400


# PUT modifica parcheggio
@api.route('/api/parcheggi/<id>', methods=['PUT'])
def update_parcheggio(id):
    data = request.json
    try:
        nome = str(data.get("nome", ""))
        comune = str(data.get("comune", ""))
        capienza = int(data.get("capienza", 0))
        attivo = 1 if data.get("attivo") in [True, "true", "1", 1] else 0
        latitudine = float(str(data.get("latitudine", "0")).replace(",", "."))
        longitudine = float(str(data.get("longitudine", "0")).replace(",", "."))

        conn = sqlite3.connect("databases/parcheggi.db")
        conn.execute(
            "UPDATE parcheggi SET nome=?, comune=?, capienza=?, attivo=?, latitudine=?, longitudine=? WHERE id=?",
            (nome, comune, capienza, attivo, latitudine, longitudine, int(id))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("Errore in update_parcheggio:", e, "-- dati ricevuti:", data)
        return jsonify({"error": str(e)}), 400

# DELETE parcheggio
@api.route('/api/parcheggi/<id>', methods=['DELETE'])
def delete_parcheggio(id):
    conn = get_db_connectionParcheggi()
    conn.execute("DELETE FROM parcheggi WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ---------------- LINEE BUS -----------------

#se voglio una lista di linee come una lista dei dati e non un json

def load_linee():
    """Restituisce una lista di tutte le linee come dict (senza jsonify)."""
    conn = get_db_connectionLinee()
    rows = conn.execute("SELECT * FROM linee").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# GET tutte le linee (JSON API)
@api.route('/api/linee', methods=['GET'])
def get_linee():
    linee = load_linee()
    return jsonify(linee)

# GET una singola linea
@api.route('/api/linee/<id>', methods=['GET'])
def get_linea(id):
    conn = get_db_connectionLinee()
    row = conn.execute("SELECT * FROM linee WHERE id=?", (int(id),)).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "Linea non trovata"}), 404


# POST nuova linea
@api.route('/api/linee', methods=['POST'])
def add_linea():
    data = request.json
    try:
        nome = str(data.get("nome", ""))
        comune_partenza = str(data.get("comune_partenza", ""))
        partenza_lat = float(str(data.get("partenza_lat", "0")).replace(",", "."))
        partenza_lng = float(str(data.get("partenza_lng", "0")).replace(",", "."))
        comune_arrivo = str(data.get("comune_arrivo", ""))
        arrivo_lat = float(str(data.get("arrivo_lat", "0")).replace(",", "."))
        arrivo_lng = float(str(data.get("arrivo_lng", "0")).replace(",", "."))
        capienza = int(data.get("capienza", 0))
        attiva = 1 if data.get("attiva") in [True, "true", "1", 1] else 0
        sabato = 1 if data.get("sabato") in [True, "true", "1", 1] else 0
        domenica = 1 if data.get("domenica") in [True, "true", "1", 1] else 0
        frequenza_giornaliera = int(data.get("frequenza_giornaliera", 0))

        conn = get_db_connectionLinee()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO linee 
               (nome, comune_partenza, partenza_lat, partenza_lng, comune_arrivo,
                arrivo_lat, arrivo_lng, capienza, attiva, sabato, domenica, frequenza_giornaliera)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, comune_partenza, partenza_lat, partenza_lng, comune_arrivo,
             arrivo_lat, arrivo_lng, capienza, attiva, sabato, domenica, frequenza_giornaliera)
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"id": new_id}), 201

    except Exception as e:
        print("Errore in add_linea:", e, "-- dati:", data)
        return jsonify({"error": str(e)}), 400


# PUT modifica linea
@api.route('/api/linee/<id>', methods=['PUT'])
def update_linea(id):
    data = request.json
    try:
        nome = str(data.get("nome", ""))
        comune_partenza = str(data.get("comune_partenza", ""))
        partenza_lat = float(str(data.get("partenza_lat", "0")).replace(",", "."))
        partenza_lng = float(str(data.get("partenza_lng", "0")).replace(",", "."))
        comune_arrivo = str(data.get("comune_arrivo", ""))
        arrivo_lat = float(str(data.get("arrivo_lat", "0")).replace(",", "."))
        arrivo_lng = float(str(data.get("arrivo_lng", "0")).replace(",", "."))
        capienza = int(data.get("capienza", 0))
        attiva = 1 if data.get("attiva") in [True, "true", "1", 1] else 0
        sabato = 1 if data.get("sabato") in [True, "true", "1", 1] else 0
        domenica = 1 if data.get("domenica") in [True, "true", "1", 1] else 0
        frequenza_giornaliera = int(data.get("frequenza_giornaliera", 0))

        conn = get_db_connectionLinee()
        conn.execute(
            """UPDATE linee 
               SET nome=?, comune_partenza=?, partenza_lat=?, partenza_lng=?, 
                   comune_arrivo=?, arrivo_lat=?, arrivo_lng=?, capienza=?, attiva=?, 
                   sabato=?, domenica=?, frequenza_giornaliera=? 
               WHERE id=?""",
            (nome, comune_partenza, partenza_lat, partenza_lng, comune_arrivo,
             arrivo_lat, arrivo_lng, capienza, attiva, sabato, domenica, frequenza_giornaliera, int(id))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    except Exception as e:
        print("Errore in update_linea:", e, "-- dati:", data)
        return jsonify({"error": str(e)}), 400


# DELETE linea
@api.route('/api/linee/<id>', methods=['DELETE'])
def delete_linea(id):
    conn = get_db_connectionLinee()
    conn.execute("DELETE FROM linee WHERE id=?", (int(id),))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ---------------- SIMULAZIONI ---------------

# GET simulazioni
@api.route('/api/simulazioni', methods=['GET'])
def get_simulazioni():
    # --- Carica tutte le simulazioni ---
    conn_sim = get_db_connectionSimulazioni()
    rows = conn_sim.execute("SELECT * FROM simulazioni ORDER BY timestamp DESC").fetchall()
    conn_sim.close()
    simulazioni = [dict(r) for r in rows]

    # --- Carica parcheggi e linee ---
    parcheggi = load_parcheggi()
    linee = load_linee()

    return jsonify({
        "simulazioni": simulazioni,
        "parcheggi": parcheggi,
        "linee": linee
    })

# DELETE simulazione
@api.route('/api/simulazioni/<sim_id>', methods=['DELETE'])
def delete_simulazione(sim_id):
    try:
        conn = get_db_connectionSimulazioni()
        cur = conn.cursor()
        cur.execute("DELETE FROM simulazioni WHERE id = ?", (sim_id,))
        conn.commit()
        conn.close()

        # Se nessuna riga è stata cancellata
        if cur.rowcount == 0:
            return jsonify({"error": "Simulazione non trovata"}), 404

        return jsonify({"success": True}), 200

    except Exception as e:
        print("Errore in delete_simulazione:", e)
        return jsonify({"error": str(e)}), 500

# GET singola simulazione
@api.route('/api/simulazioni/<sim_id>', methods=['GET'])
def get_simulazione_dettaglio(sim_id):
    try:
        conn = get_db_connectionSimulazioni()
        row = conn.execute("SELECT * FROM simulazioni WHERE id=?", (sim_id,)).fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Simulazione non trovata"}), 404

        sim = dict(row)

        # Converte i campi JSON in Python
        for key in ["risultato", "parcheggi_usati", "linee_usate", "parcheggi_esclusi", "linee_escluse"]:
            try:
                sim[key] = json.loads(sim.get(key, "[]") or "[]")
            except Exception:
                sim[key] = []

        simulazione = {
            "id": sim["id"],
            "data": sim["data"],
            "n_turisti": sim["n_turisti"],
            "parcheggi": sim["parcheggi_usati"],
            "linee": sim["linee_usate"],
            "parcheggi_esclusi": sim["parcheggi_esclusi"],
            "linee_escluse": sim["linee_escluse"]
        }

        return jsonify(simulazione), 200

    except Exception as e:
        print("❌ Errore in get_simulazione_dettaglio:", e)
        return jsonify({"error": str(e)}), 500

@api.route('/api/simulazioni/esporta', methods=['POST'])
def esporta_simulazione():
    try:
        sim_data = request.get_json()
        sim_id = sim_data.get('id')

        if not sim_id:
            return jsonify({'error': 'ID simulazione mancante'}), 400

        # --- Connessione al DB ---
        conn = get_db_connectionSimulazioni()
        cur = conn.cursor()
        cur.execute("SELECT * FROM simulazioni WHERE id = ?", (sim_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify({'error': 'Simulazione non trovata'}), 404

        # --- Ricostruisci i dati ---
        columns = [desc[0] for desc in cur.description]
        sim = dict(zip(columns, row))
        conn.close()

        def safe_json_loads(value):
            try:
                return json.loads(value) if value else []
            except Exception:
                return []

        export_data = {
            "data": sim.get("data"),
            "n_turisti": sim.get("n_turisti"),
            "parcheggi_aperti": safe_json_loads(sim.get("parcheggi_usati")),
            "parcheggi_esclusi": safe_json_loads(sim.get("parcheggi_esclusi")),
            "linee_utilizzate": safe_json_loads(sim.get("linee_usate")),
            "linee_escluse": safe_json_loads(sim.get("linee_escluse")),
        }

        # --- Crea file JSON ---
        os.makedirs("exports", exist_ok=True)
        filename = f"simulazione_{sim_id}.json"
        export_path = os.path.join("exports", filename)

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=4)

        # --- Ritorna il file come download ---
        return send_file(
            export_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/json"
        )

    except Exception as e:
        print("❌ Errore in /api/simulazioni/esporta:", e)
        return jsonify({'error': str(e)}), 500

# esegui la simulazione
@api.route('/api/sim', methods=['POST'])
def api_simulazione():
    try:
        data = request.get_json()

        data_sim = data.get('data')
        n_turisti = int(data.get('n_turisti', 0))
        parcheggi_esclusi_ids = data.get('parcheggi_esclusi', [])
        linee_escluse_ids = data.get('linee_escluse', [])

        if not data_sim or n_turisti <= 0:
            return jsonify({'error': 'Dati non validi'}), 400

        # 🔹 Esegui la logica della simulazione
        sim_id, sim_doc = run_simulazione(data_sim, n_turisti, parcheggi_esclusi_ids, linee_escluse_ids)

        # 🔹 Risposta JSON
        return jsonify({'id': sim_id, 'simulazione': sim_doc}), 201

    except Exception as e:
        print("❌ Errore in /api/sim:", e)
        return jsonify({'error': str(e)}), 500


def run_simulazione(data, n_turisti, parcheggi_esclusi_ids, linee_escluse_ids):
    """Esegue la simulazione e salva i risultati nel DB SQLite"""
    # --- Recupera parcheggi e linee ---
    parcheggi = load_parcheggi()
    linee = load_linee()

    # --- Filtra esclusi ---
    parcheggi_esclusi = [p for p in parcheggi if str(p["id"]) in parcheggi_esclusi_ids]
    linee_escluse = [l for l in linee if str(l["id"]) in linee_escluse_ids]
    parcheggi = [p for p in parcheggi if str(p["id"]) not in parcheggi_esclusi_ids]
    linee = [l for l in linee if str(l["id"]) not in linee_escluse_ids]

    # --- Esegui simulazione ---
    output = ottimizza_risorse(parcheggi, linee, n_turisti)
    risultato = output["risultato"]
    parcheggi_usati = output["parcheggi_usati"]
    linee_usate = output["linee_usate"]

    sim_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # --- Salva in DB simulazioni ---
    try:
        conn = get_db_connectionSimulazioni()
        conn.execute("""
            INSERT INTO simulazioni (id, data, n_turisti, risultato, parcheggi_usati, linee_usate,
                                     parcheggi_esclusi, linee_escluse, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sim_id, data, n_turisti,
            json.dumps(risultato),
            json.dumps(parcheggi_usati),
            json.dumps(linee_usate),
            json.dumps(parcheggi_esclusi),
            json.dumps(linee_escluse),
            timestamp
        ))
        conn.commit()
    except Exception as e:
        print("❌ Errore durante il salvataggio simulazione:", e)
    finally:
        conn.close()

    return sim_id, {
        "id": sim_id,
        "data": data,
        "n_turisti": n_turisti,
        "risultato": risultato,
        "parcheggi_usati": parcheggi_usati,
        "linee_usate": linee_usate,
        "parcheggi_esclusi": parcheggi_esclusi,
        "linee_escluse": linee_escluse,
        "timestamp": timestamp
    }

def ottimizza_risorse(parcheggi, linee, n_turisti):
    DOZZA_COORDS = (44.3511, 11.6519)
    risultato = {}
    assegnati = 0
    parcheggi_usati = []
    linee_usate = set()

    # Mappa: parcheggio_id → linee collegate
    linee_per_parcheggio = {}
    for p in parcheggi:
        lat_p, lng_p = to_float(p['latitudine']), to_float(p['longitudine'])
        for linea in linee:
            lat_l, lng_l = to_float(linea['partenza_lat']), to_float(linea['partenza_lng'])
            if sono_vicini(lat_p, lng_p, lat_l, lng_l, soglia_m=1000):
                linee_per_parcheggio.setdefault(p['id'], []).append(linea)

    # Calcola distanza di ogni parcheggio da Dozza
    parcheggi_distanze = [
        (p, geodesic((to_float(p['latitudine']), to_float(p['longitudine'])), DOZZA_COORDS).meters)
        for p in parcheggi
    ]
    parcheggi_distanze.sort(key=lambda x: x[1])  # Ordina per distanza crescente

    for parcheggio, distanza in parcheggi_distanze:
        if assegnati >= n_turisti:
            break

        capienza_p = parcheggio.get('capienza', 0)
        if capienza_p <= 0:
            continue

        turisti_restanti = n_turisti - assegnati
        turisti_assegnati_parcheggio = 0
        linee_usate_parcheggio = []

        # Linee associate ordinate per vicinanza dell’arrivo a Dozza
        linee_assoc = sorted(
            linee_per_parcheggio.get(parcheggio['id'], []),
            key=lambda l: geodesic(
                (to_float(l['arrivo_lat']), to_float(l['arrivo_lng'])),
                DOZZA_COORDS
            ).meters
        )

        for linea in linee_assoc:
            capienza_linea = linea.get('capienza', 0)
            viaggi = int(float(str(linea.get('frequenza_giornaliera', 1)).replace(',', '.')))
            capienza_totale_linea = capienza_linea * viaggi

            turisti_su_linea = min(turisti_restanti, capienza_p, capienza_totale_linea)
            if turisti_su_linea > 0:
                linee_usate.add(linea['id'])
                linee_usate_parcheggio.append({'linea_id': linea['id'], 'turisti': turisti_su_linea})
                turisti_assegnati_parcheggio += turisti_su_linea
                assegnati += turisti_su_linea
                capienza_p -= turisti_su_linea
                turisti_restanti = n_turisti - assegnati
            if assegnati >= n_turisti or capienza_p <= 0:
                break

        if not linee_assoc and capienza_p > 0 and turisti_restanti > 0:
            turisti_da_inviare = min(turisti_restanti, capienza_p)
            turisti_assegnati_parcheggio += turisti_da_inviare
            assegnati += turisti_da_inviare

        if turisti_assegnati_parcheggio > 0:
            risultato[parcheggio['nome']] = turisti_assegnati_parcheggio
            parcheggio_copy = parcheggio.copy()
            parcheggio_copy['linee_usate'] = linee_usate_parcheggio
            parcheggi_usati.append(parcheggio_copy)

    linee_utilizzate = [l for l in linee if l['id'] in linee_usate]

    return {
        'risultato': risultato,
        'parcheggi_usati': parcheggi_usati,
        'linee_usate': linee_utilizzate
    }

def sono_vicini(lat1, lng1, lat2, lng2, soglia_m=1000):
    """True se la distanza tra due punti è minore della soglia in metri."""
    return geodesic((lat1, lng1), (lat2, lng2)).meters <= soglia_m

def to_float(val):
    if isinstance(val, (float, int)):
        return float(val)
    try:
        return float(str(val).replace(',', '.'))
    except:
        return 0.0

# ---------------- PREDIZIONE  ----------------

from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# === Caricamento modelli ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "previsioni_files")

try:
    model = joblib.load(os.path.join(FILES_DIR, "mobility_model.pkl"))
    scaler = joblib.load(os.path.join(FILES_DIR, "scaler.pkl"))
    label_encoder = joblib.load(os.path.join(FILES_DIR, "label_encoder.pkl"))
    #print("Modello di previsione caricato correttamente.")
except Exception as e:
    print("Errore nel caricamento dei file di previsione:", e)
    model = scaler = label_encoder = None


@api.route('/api/predizioni', methods=['POST'])
def api_predizioni():
    """
    Genera previsioni di afflusso turistico per Dozza (intera area)
    considerando tutti i layer associati al comune (08|034|...).
    """
    if model is None or scaler is None or label_encoder is None:
        return jsonify({"error": "Modelli non caricati"}), 500

    data = request.json
    if not data:
        return jsonify({"error": "Nessun dato fornito"}), 400

    try:
        mese = int(data.get("mese"))
        anno = int(data.get("anno"))

        # 🔹 Seleziona solo i layerid che appartengono a Dozza
        dozza_layerids = [lid for lid in label_encoder.classes_ if lid.startswith("08|037|025")]

        if not dozza_layerids:
            return jsonify({"error": "Nessun layer trovato per Dozza"}), 404

        # 🔹 Calcola le date del mese richiesto
        start_date = datetime(anno, mese, 1)
        next_month = datetime(anno + (mese // 12), (mese % 12) + 1, 1)
        num_days = (next_month - start_date).days

        predictions = []
        # 🔹 Per ogni giorno del mese
        for i in range(num_days):
            giorno = start_date + timedelta(days=i)
            weekday = giorno.weekday()
            week = giorno.isocalendar().week - 35
            weekend = 1 if weekday in [5, 6] else 0
            date_int = int(giorno.timestamp() * 1e9)

            preds_day = []
            # 🔹 Predici per ogni layer di Dozza
            for lid in dozza_layerids:
                encoded_layerid = label_encoder.transform([lid])[0]
                X = pd.DataFrame([{
                    "date": date_int,
                    "layerid": encoded_layerid,
                    "weekday": weekday,
                    "week": week,
                    "weekend": weekend
                }])

                X_scaled = scaler.transform(X)
                y_log_pred = model.predict(X_scaled)
                y_pred = np.expm1(y_log_pred)
                preds_day.append(y_pred[0])
            # 🔹 Calcola la media (in questo caso non necessaria perchè dozza ha solo un layerid)
            mean_pred = float(np.mean(preds_day))
            print(dozza_layerids)
            #print(preds_day, "preds day")
            print(mean_pred)
            predictions.append({
                "data": giorno.strftime("%Y-%m-%d"),
                "turisti": mean_pred
            })

        return jsonify({
            "anno": anno,
            "mese": mese,
            "previsioni": predictions
        })

    except Exception as e:
        print("❌ Errore durante la previsione:", e)
        return jsonify({"error": str(e)}), 500



