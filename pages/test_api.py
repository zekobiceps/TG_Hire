import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import importlib.util  # Import explicite pour éviter l'erreur

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

# -------------------- Import utils --------------------
# Assurez-vous que utils.py existe dans le dossier parent
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# -------------------- Persistance des données --------------------
DATA_FILE = "cartographie_data.json"

# Charger les données depuis le fichier JSON au démarrage
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "🌟 Haut Potentiel": [],
        "💎 Rare & stratégique": [],
        "⚡ Rapide à mobiliser": [],
        "📚 Facilement disponible": []
    }

# Sauvegarder les données dans le fichier JSON
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(st.session_state.cartographie_data, f, indent=2)

# Initialiser les données dans session_state
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data()

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🗺️ Cartographie des talents")

# -------------------- Dashboard --------------------
st.subheader("📊 Vue globale de la cartographie")
counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
if sum(counts.values()) > 0:
    fig = px.pie(
        names=list(counts.keys()),
        values=list(counts.values()),
        title="Répartition des candidats par quadrant",
        color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    )
    st.plotly_chart(fig)
else:
    st.info("Aucun candidat dans la cartographie pour l'instant.")

# -------------------- Choix quadrant --------------------
quadrant_choisi = st.selectbox("Quadrant:", list(st.session_state.cartographie_data.keys()), key="carto_quadrant")

# -------------------- Ajout candidat --------------------
st.subheader("➕ Ajouter un candidat")
col1, col2, col3, col4 = st.columns(4)
with col1:
    nom = st.text_input("Nom du candidat", key="carto_nom")
with col2:
    poste = st.text_input("Poste", key="carto_poste")
with col3:
    entreprise = st.text_input("Entreprise", key="carto_entreprise")
with col4:
    linkedin = st.text_input("Lien LinkedIn", key="carto_linkedin")

notes = st.text_area("Notes / Observations", key="carto_notes", height=100)
cv_file = st.file_uploader("Télécharger CV (PDF ou DOCX)", type=["pdf", "docx"], key="carto_cv")

if st.button("💾 Ajouter à la cartographie", type="primary", use_container_width=True, key="btn_add_carto"):
    if nom and poste:
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nom": nom,
            "poste": poste,
            "entreprise": entreprise,
            "linkedin": linkedin,
            "notes": notes,
            "cv_name": cv_file.name if cv_file else None,
            "cv_content": cv_file.read() if cv_file else None,  # Stockage des bytes
            "cv_type": cv_file.type if cv_file else None
        }
        st.session_state.cartographie_data[quadrant_choisi].append(entry)
        save_data()  # Sauvegarde dans le fichier JSON
        st.success(f"✅ {nom} ajouté à {quadrant_choisi}")
    else:
        st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

st.divider()

# -------------------- Recherche --------------------
st.subheader("🔍 Rechercher un candidat")
search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")
filtered_cands = [
    cand for cand in st.session_state.cartographie_data[quadrant_choisi][::-1]
    if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
]

# -------------------- Affichage données --------------------
st.subheader(f"📋 Candidats dans : {quadrant_choisi}")

if not filtered_cands:
    st.info("Aucun candidat correspondant dans ce quadrant.")
else:
    for i, cand in enumerate(filtered_cands):
        with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
            st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
            st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
            st.write(f"**Notes :** {cand.get('notes', '')}")

            if cand.get('cv_name'):
                st.write(f"**CV :** {cand['cv_name']}")
                st.download_button(
                    label="⬇️ Télécharger CV",
                    data=cand['cv_content'],
                    file_name=cand['cv_name'],
                    mime=cand['cv_type'],
                    key=f"download_cv_{quadrant_choisi}_{i}"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"delete_carto_{quadrant_choisi}_{i}"):
                    original_index = len(st.session_state.cartographie_data[quadrant_choisi]) - 1 - st.session_state.cartographie_data[quadrant_choisi][::-1].index(cand)
                    st.session_state.cartographie_data[quadrant_choisi].pop(original_index)
                    save_data()  # Sauvegarde après suppression
                    st.success("✅ Candidat supprimé")
                    st.rerun()
            with col2:
                export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {cand.get('cv_name', 'Aucun')}"
                st.download_button(
                    "⬇️ Exporter",
                    data=export_text,
                    file_name=f"cartographie_{cand['nom']}.txt",
                    mime="text/plain",
                    key=f"download_carto_{quadrant_choisi}_{i}"
                )

# -------------------- Export global --------------------
st.subheader("📤 Exporter toute la cartographie")
if st.button("⬇️ Exporter en CSV"):
    all_data = []
    for quad, cands in st.session_state.cartographie_data.items():
        for cand in cands:
            cand_copy = cand.copy()
            cand_copy['quadrant'] = quad
            cand_copy.pop('cv_content', None)  # Exclure contenu lourd
            cand_copy.pop('cv_type', None)
            all_data.append(cand_copy)
    df = pd.DataFrame(all_data)
    st.download_button(
        "Télécharger CSV",
        df.to_csv(index=False),
        file_name="cartographie_talents.csv",
        mime="text/csv"
    )