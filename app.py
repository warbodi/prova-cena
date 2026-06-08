import streamlit as st
import json
import requests
from datetime import datetime

st.set_page_config(page_title="Ordina la tua Cena!", page_icon="🍕")

# --- RECUPERO CHIAVI DA STREAMLIT SECRETS ---
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
TABLE_NAME = "Ordini"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# --- FUNZIONI AIRTABLE ---
def leggi_ordini():
    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            records = response.json().get("records", [])
            ordini = []
            for r in records:
                f = r["fields"]
                # Airtable non restituisce i campi vuoti, quindi usiamo .get() per evitare errori
                ordine = {
                    "ID": str(f.get("ID", "")),
                    "Nome": f.get("Nome", ""),
                    "Articolo": f.get("Articolo", ""),
                    "Variazioni": f.get("Variazioni", ""),
                    "Status": f.get("Status", ""),
                    "Timestamp": f.get("Timestamp", ""),
                    "airtable_id": r["id"] # Questo ID interno serve per le modifiche
                }
                ordini.append(ordine)
            return ordini
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
    return []

def inserisci_ordine(articolo, variazione, nome, ordine_id):
    data = {
        "fields": {
            "ID": str(ordine_id),
            "Nome": nome.title(),
            "Articolo": articolo,
            "Variazioni": variazione,
            "Status": "In Coda",
            "Timestamp": datetime.now().strftime("%H:%M:%S")
        }
    }
    requests.post(URL, headers=HEADERS, json=data)

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

# --- CARICAMENTO MENU ---
@st.cache_data
def carica_menu():
    with open('menu.json', 'r', encoding='utf-8') as f:
        return json.load(f)

menu = carica_menu()

if 'carrello' not in st.session_state:
    st.session_state.carrello = []

st.title("🍕 Il Menù di Stasera")
nome_utente = st.text_input("Chi sta ordinando? (Scrivi il tuo nome)")

st.divider()

# --- SEZIONE 1: IL MENÙ VISUALE ---
st.subheader("Scegli cosa mangiare")
tabs = st.tabs(list(menu.keys()))

for i, categoria in enumerate(menu.keys()):
    with tabs[i]:
        for articolo in menu[categoria]:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{articolo}**")
            with col2:
                if st.button("Aggiungi", key=f"add_{categoria}_{articolo}"):
                    st.session_state.carrello.append({"Articolo": articolo, "Variazioni": ""})
                    st.rerun()

# --- SEZIONE 2: IL CARRELLO ---
if len(st.session_state.carrello) > 0:
    st.divider()
    st.header("🛒 Il tuo vassoio")
    
    for idx, item in enumerate(st.session_state.carrello):
        col_a, col_b, col_c = st.columns([3, 4, 1])
        with col_a:
            st.markdown(f"👉 **{item['Articolo']}**")
        with col_b:
            item['Variazioni'] = st.text_input(
                "Note", 
                key=f"note_{idx}", 
                label_visibility="collapsed", 
                placeholder="Es. Senza mozzarella"
            )
        with col_c:
            if st.button("❌", key=f"del_{idx}"):
                st.session_state.carrello.pop(idx)
                st.rerun()
                
    if st.button("🚀 Invia Ordine in Cucina", type="primary", use_container_width=True):
        if not nome_utente.strip():
            st.error("Ehi, ricordati di inserire il tuo nome in alto prima di inviare!")
        else:
            ordini_totali = leggi_ordini()
            prossimo_id = len(ordini_totali) + 1
            
            for item in st.session_state.carrello:
                inserisci_ordine(item["Articolo"], item["Variazioni"], nome_utente, prossimo_id)
                prossimo_id += 1
            
            st.session_state.carrello.clear() 
            st.success(f"Tutto ricevuto {nome_utente.title()}! Ordine in preparazione.")
            st.rerun()

st.divider()

# --- SEZIONE 3: CONTROLLA LA CODA ---
st.header("⏳ A che punto è la mia roba?")
nome_controllo = st.text_input("Inserisci il tuo nome per controllare")

if nome_controllo:
    ordini_totali = leggi_ordini()
    ordini_utente = [o for o in ordini_totali if o["Nome"] == nome_controllo.title()]
    
    if not ordini_utente:
        st.warning("Nessun ordine trovato con questo nome.")
    else:
        for ordine in ordini_utente:
            if ordine["Status"] == "Evaso":
                colore_status = "🟢 Evaso"
            elif ordine["Status"] == "Cancellato":
                colore_status = "⚪ Cancellato"
            else:
                colore_status = "🟡 In Coda"
                
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 2, 1])
                with col1:
                    st.markdown(f"**{ordine['Articolo']}**")
                    if ordine['Variazioni']:
                        st.caption(f"Note: {ordine['Variazioni']}")
                with col2:
                    st.write(f"Stato: {colore_status}")
                with col3:
                    if ordine["Status"] == "In Coda":
                        if st.button("❌", key=f"cancella_utente_{ordine['airtable_id']}"):
                            aggiorna_status(ordine['airtable_id'], "Cancellato")
                            st.toast("Ordine annullato!")
                            st.rerun()
                            
        ordini_attivi_utente = [o for o in ordini_utente if o["Status"] == "In Coda"]
        if ordini_attivi_utente:
            ordini_in_coda_totali = [o for o in ordini_totali if o["Status"] == "In Coda"]
            try:
                ultimo_ordine = ordini_attivi_utente[-1]
                ids_in_coda = [o["airtable_id"] for o in ordini_in_coda_totali]
                posizione = ids_in_coda.index(ultimo_ordine["airtable_id"]) + 1
                st.info(f"Il tuo ultimo ordine è in posizione {posizione} nella coda della cucina.")
            except:
                pass