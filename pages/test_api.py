import streamlit as st

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()
    
import sys
import os
import importlib.util
import streamlit as st
from datetime import datetime
import base64  # Pour gérer les fichiers CV en base64 si besoin pour export

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# -------------------- Données par défaut --------------------
SOURCING_MATRIX_DATA = {
    "🌟 Haut Potentiel": [],
    "💎 Rare & stratégique": [],
    "⚡ Rapide à mobiliser": [],
    "📚 Facilement disponible": []
}

# Initialiser dans session_state si manquant
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = {k: [] for k in SOURCING_MATRIX_DATA.keys()}

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🗺️ Cartographie des talents")

# -------------------- Choix quadrant --------------------
quadrant_choisi = st.selectbox("Quadrant:", list(SOURCING_MATRIX_DATA.keys()), key="carto_quadrant")

# -------------------- Ajout candidat --------------------
st.subheader("➕ Ajouter un candidat")
col1, col2, col3, col4 = st.columns(4)  # Ajout d'une colonne pour LinkedIn
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
            "cv_content": cv_file.read() if cv_file else None,  # Stockage des bytes du fichier
            "cv_type": cv_file.type if cv_file else None
        }
        st.session_state.cartographie_data[quadrant_choisi].append(entry)
        st.success(f"✅ {nom} ajouté à {quadrant_choisi}")
    else:
        st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

st.divider()

# -------------------- Affichage données --------------------
st.subheader(f"📋 Candidats dans : {quadrant_choisi}")

if not st.session_state.cartographie_data[quadrant_choisi]:
    st.info("Aucun candidat dans ce quadrant.")
else:
    for i, cand in enumerate(st.session_state.cartographie_data[quadrant_choisi][::-1]):
        with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
            st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
            st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
            st.write(f"**Notes :** {cand.get('notes', '')}")

            if cand.get('cv_name'):
                st.write(f"**CV :** {cand['cv_name']}")
                # Bouton pour télécharger le CV
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
                    st.session_state.cartographie_data[quadrant_choisi].pop(len(st.session_state.cartographie_data[quadrant_choisi]) - 1 - i)
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