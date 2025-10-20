import sqlite3

UTENTI = "databases/utenti.db"
PARCHEGGI = "databases/parcheggi.db"
LINEE = "databases/linee.db"
SIMULAZIONI = "databases/simulazioni.db"


def get_db_connectionUtenti():
    conn = sqlite3.connect(UTENTI)
    conn.row_factory = sqlite3.Row  # permette di accedere ai campi per nome
    return conn

def get_db_connectionParcheggi():
    conn = sqlite3.connect(PARCHEGGI)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_connectionLinee():
    conn = sqlite3.connect(LINEE)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_connectionSimulazioni():
    conn = sqlite3.connect(SIMULAZIONI)
    conn.row_factory = sqlite3.Row
    return conn