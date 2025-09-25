from google.cloud import firestore
import pandas as pd
from werkzeug.security import generate_password_hash
from secret import main_user, main_password


db = 'mobility-dozza'
db = firestore.Client.from_service_account_json('credentials.json', database=db)


db.collection('utenti').add({
            'email': main_user,
            'password': generate_password_hash(main_password),
            'ruolo': 'admin'
})


collections = ["dataset/DATASET-PARCHEGGI.csv","dataset/DATASET-LINEE-BUS.csv"]
collection_name = ["parcheggi", "linee_bus"]
n = 0

for collection in collections:

    df = pd.read_csv(collection)
    df = df.reset_index(drop=True) #resetto l'indice del dataframe in modo che sia numerico

    for i, row in df.iterrows():
        doc_id = str(i) # Utilizzo l'indice del dataframe come ID del documento
        data = row.to_dict()
        db.collection(collection_name[n]).document(doc_id).set(data)

    print(f"Collezione '{collection_name[n]}' popolata con {len(df)} documenti.")
    n += 1