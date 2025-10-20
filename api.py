import sqlite3
from flask import Blueprint, request, jsonify

from utils import *

api = Blueprint('api', __name__)

# ------------------ API LOGIN UTENTE ------------------
@api.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email, password = data.get('email'), data.get('password')

    if not email or not password:
        return jsonify(success=False, message="Dati mancanti"), 400

    with get_db_connectionUtenti() as conn:
        user = conn.execute("SELECT * FROM utenti WHERE email = ?", (email,)).fetchone()

    if user and user["password"] == password:
        return jsonify(
            success=True,
            message="Login riuscito",
            user={"id": user["id"], "email": user["email"], "ruolo": user["ruolo"]}
        ), 200

    return jsonify(success=False, message="Credenziali non valide"), 401

# 🔹 LOGIN ADMIN
@api.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.get_json() or {}
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400

    conn = get_db_connectionUtenti()
    admin = conn.execute("SELECT * FROM utenti WHERE email=? AND ruolo='admin'", (email,)).fetchone()
    conn.close()

    if admin and admin["password"] == password:
        return jsonify({'success': True, 'user': {'id': admin['id'], 'email': admin['email'], 'ruolo': admin['ruolo']}}), 200
    return jsonify({'success': False, 'message': 'Credenziali non valide'}), 401


# 🔹 LISTA UTENTI
@api.route('/api/admin/utenti', methods=['GET'])
def api_get_utenti():
    conn = get_db_connectionUtenti()
    utenti = [dict(u) for u in conn.execute("SELECT id, email, ruolo FROM utenti").fetchall()]
    conn.close()
    return jsonify(utenti), 200


# 🔹 AGGIUNGI UTENTE
@api.route('/api/admin/utenti', methods=['POST'])
def api_add_utente():
    data = request.get_json() or {}
    email, password, ruolo = data.get('email'), data.get('password'), data.get('ruolo', 'user')
    if not email or not password:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400

    conn = get_db_connectionUtenti()
    try:
        conn.execute("INSERT INTO utenti (email, password, ruolo) VALUES (?, ?, ?)", (email, password, ruolo))
        conn.commit()
        result = {'success': True, 'message': 'Utente aggiunto'}
        code = 201
    except sqlite3.IntegrityError:
        result = {'success': False, 'message': 'Utente già esistente'}
        code = 409
    finally:
        conn.close()
    return jsonify(result), code

# 🔹 ELIMINA UTENTE
@api.route('/api/admin/utenti/<int:utente_id>', methods=['DELETE'])
def api_delete_utente(utente_id):
    conn = get_db_connectionUtenti()
    cur = conn.execute("DELETE FROM utenti WHERE id = ?", (utente_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return jsonify({'success': deleted}), (200 if deleted else 404)

#------------------------PARCHEGGI API------------------------------

# Restituisce tutti i parcheggi in JSON
@api.route('/api/parcheggi', methods=['GET'])
def get_parcheggi():
    conn = get_db_connectionParcheggi()
    rows = conn.execute("SELECT * FROM parcheggi").fetchall()
    conn.close()
    parcheggi = [dict(row) for row in rows]
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

# GET tutte le linee (JSON API)
@api.route('/api/linee', methods=['GET'])
def get_linee():
    conn = get_db_connectionLinee()
    rows = conn.execute("SELECT * FROM linee").fetchall()
    conn.close()
    linee = [dict(row) for row in rows]
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
#non metto nulla perchè i metodi o hanno dei redirect, quindi dipendono da html
#oppure hanno render template che dipende da html anche lui, oppure sono solo dei metodi
#e non hanno senso di stare nella pagina delle api, avrei solo una o 2 robe da mettere qua
#mentre gli altri metodi che sembrerebbero rest ma dipendono da html rimarrebbero


