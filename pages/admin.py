import streamlit as st
import json
import requests

st.set_page_config(page_title="Gestione Ordini", page_icon="👨‍🍳", layout="wide")

st.title("👨‍🍳 Pannello di Controllo Ordini")

# --- CONFIGURAZIONE AIRTABLE ---
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
TABLE_NAME = "Ordini"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

def leggi_ordini():
    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            records = response.json().get("records", [])
            ordini = []
            for r in records:
                f = r["fields"]
                ordine = {
                    "ID": str(f.get("ID", "")),
                    "Nome": f.get("Nome", ""),
                    "Articolo": f.get("Articolo", ""),
                    "Variazioni": f.get("Variazioni", ""),
                    "Status": f.get("Status", ""),
                    "Timestamp": f.get("Timestamp", ""),
                    "airtable_id": r["id"]
                }
                ordini.append(ordine)
            return ordini
    except:
        pass
    return []

def aggiorna_status(airtable_id, nuovo_status):
    data = {
        "records": [
            {
                "id": airtable_id,
                "fields": {"Status": nuovo_status}
            }
        ]
    }
    requests.patch(URL, headers=HEADERS, json=data)

@st.cache_data
def carica_menu():
    with open('menu.json', 'r', encoding='utf-8') as f:
        return json.load(f)

menu = carica_menu()

ordini_totali = leggi_ordini()
ordini_attivi = [o for o in ordini_totali if o["Status"] == "In Coda"]

if not ordini_attivi:
    st.success("Tutti gli ordini sono stati evasi o non ci sono ordinazioni! Rilassati. 😎")
    if st.button("🔄 Aggiorna Pagina", type="primary"):
        st.rerun()
else:
    col_titolo, col_aggiorna = st.columns([5, 1])
    with col_titolo:
        st.subheader(f"Ordini totali da preparare: {len(ordini_attivi)}")
    with col_aggiorna:
        if st.button("🔄 Aggiorna Coda", use_container_width=True):
            st.rerun()
            
    st.divider()
    
    categorie = list(menu.keys())
    
    # Visualizzazione verticale divisa per categorie
    for cat in categorie:
        ordini_di_categoria = [o for o in ordini_attivi if o["Articolo"] in menu[cat]]
        
        if ordini_di_categoria:
            st.header(f"🍽️ {cat}")
            
            for ordine in ordini_di_categoria:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])
                    
                    with col1:
                        st.markdown(f"👤 **{ordine['Nome']}** — ⏰ *{ordine['Timestamp']}*")
                        st.markdown(f"🍔 **{ordine['Articolo']}**")
                        if ordine['Variazioni']:
                            st.markdown(f"⚠️ *Note: {ordine['Variazioni']}*")
                            
                    with col2:
                        if st.button("✓ Evadi", key=f"evadi_admin_{ordine['airtable_id']}", type="primary"):
                            aggiorna_status(ordine['airtable_id'], "Evaso")
                            st.rerun()
            st.divider()

def svuota_storico_evasi():
    # 1. Leggiamo tutti gli ordini presenti
    ordini = leggi_ordini()
    
    # 2. Selezioniamo solo gli ID degli ordini che sono già stati "Evasi" o "Cancellati"
    # Lasciamo intatti quelli "In Coda" per sicurezza!
    da_eliminare = [o["airtable_id"] for o in ordini if o["Status"] in ["Evaso", "Cancellato"]]
    
    # 3. Airtable cancella massimo 10 record alla volta, quindi andiamo a blocchi
    for i in range(0, len(da_eliminare), 10):
        blocco = da_eliminare[i:i+10]
        # Passiamo gli ID come parametri della richiesta DELETE
        requests.delete(URL, headers=HEADERS, params={"records[]": blocco})

        # --- SEZIONE MANUTENZIONE AL CENTRO DELLA PAGINA ---
st.divider()
st.subheader("🧹 Pulizia Database")
st.caption("Usa questo tasto prima di iniziare una nuova cena per azzerare i vecchi ordini su Airtable.")

if st.button("🗑️ Svuota tutti gli Ordini Evasi e Cancellati", type="secondary"):
    with st.spinner("Pulizia del database in corso..."):
        svuota_storico_evasi()
    st.success("Database ripulito! Pronto per la prossima cena. 🚀")
    st.rerun()
