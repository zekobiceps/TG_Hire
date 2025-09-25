import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
import importlib.util

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# -------------------- Dossier pour les CV --------------------
CV_DIR = "cvs"
if not os.path.exists(CV_DIR):
    try:
        os.makedirs(CV_DIR)
        st.info(f"📁 Dossier {CV_DIR} créé avec succès.")
    except Exception as e:
        st.error(f"❌ Erreur lors de la création du dossier {CV_DIR}: {e}")

# -------------------- Persistance des données --------------------
DATA_FILE = "cartographie_data.json"

# Charger les données depuis le fichier JSON au démarrage
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                st.info(f"✅ Fichier {DATA_FILE} chargé avec succès.")
                return data
        else:
            st.info(f"ℹ️ Fichier {DATA_FILE} non trouvé, initialisation avec données par défaut.")
            return {
                "🌟 Haut Potentiel": [],
                "💎 Rare & stratégique": [],
                "⚡ Rapide à mobiliser": [],
                "📚 Facilement disponible": []
            }
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de {DATA_FILE}: {e}")
        return {
            "🌟 Haut Potentiel": [],
            "💎 Rare & stratégique": [],
            "⚡ Rapide à mobiliser": [],
            "📚 Facilement disponible": []
        }

# Sauvegarder les données dans le fichier JSON
def save_data():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(st.session_state.cartographie_data, f, indent=2)
        st.info(f"✅ Données sauvegardées dans {DATA_FILE}.")
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde dans {DATA_FILE}: {e}")

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

# -------------------- Onglets --------------------
tab1, tab2 = st.tabs(["Gestion des candidats", "Vue globale"])

# -------------------- Onglet 1 : Gestion des candidats --------------------
with tab1:
    # Choix quadrant
    quadrant_choisi = st.selectbox("Quadrant:", list(st.session_state.cartographie_data.keys()), key="carto_quadrant")

    # Ajout candidat
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
            cv_path = None
            if cv_file:
                try:
                    cv_filename = f"{nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cv_file.name}"
                    cv_path = os.path.join(CV_DIR, cv_filename)
                    with open(cv_path, "wb") as f:
                        f.write(cv_file.read())
                    st.info(f"✅ CV sauvegardé dans {cv_path}.")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la sauvegarde du CV: {e}")
            
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "nom": nom,
                "poste": poste,
                "entreprise": entreprise,
                "linkedin": linkedin,
                "notes": notes,
                "cv_path": cv_path
            }
            st.session_state.cartographie_data[quadrant_choisi].append(entry)
            save_data()  # Sauvegarde dans le fichier JSON
            st.success(f"✅ {nom} ajouté à {quadrant_choisi}")
        else:
            st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

    st.divider()

    # Recherche
    st.subheader("🔍 Rechercher un candidat")
    search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")
    filtered_cands = [
        cand for cand in st.session_state.cartographie_data[quadrant_choisi][::-1]
        if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
    ]

    # Affichage données
    st.subheader(f"📋 Candidats dans : {quadrant_choisi}")
    if not filtered_cands:
        st.info("Aucun candidat correspondant dans ce quadrant.")
    else:
        for i, cand in enumerate(filtered_cands):
            with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
                st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
                st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
                st.write(f"**Notes :** {cand.get('notes', '')}")

                if cand.get('cv_path') and os.path.exists(cand['cv_path']):
                    st.write(f"**CV :** {os.path.basename(cand['cv_path'])}")
                    with open(cand['cv_path'], "rb") as f:
                        st.download_button(
                            label="⬇️ Télécharger CV",
                            data=f,
                            file_name=os.path.basename(cand['cv_path']),
                            mime="application/pdf" if cand['cv_path'].endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_cv_{quadrant_choisi}_{i}"
                        )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Supprimer", key=f"delete_carto_{quadrant_choisi}_{i}"):
                        original_index = len(st.session_state.cartographie_data[quadrant_choisi]) - 1 - st.session_state.cartographie_data[quadrant_choisi][::-1].index(cand)
                        if cand.get('cv_path') and os.path.exists(cand['cv_path']):
                            try:
                                os.remove(cand['cv_path'])
                                st.info(f"✅ CV {cand['cv_path']} supprimé.")
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la suppression du CV: {e}")
                        st.session_state.cartographie_data[quadrant_choisi].pop(original_index)
                        save_data()  # Sauvegarde après suppression
                        st.success("✅ Candidat supprimé")
                        st.rerun()
                with col2:
                    export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {os.path.basename(cand['cv_path']) if cand.get('cv_path') else 'Aucun'}"
                    st.download_button(
                        "⬇️ Exporter",
                        data=export_text,
                        file_name=f"cartographie_{cand['nom']}.txt",
                        mime="text/plain",
                        key=f"download_carto_{quadrant_choisi}_{i}"
                    )

    # Export global
    st.subheader("📤 Exporter toute la cartographie")
    if st.button("⬇️ Exporter en CSV"):
        all_data = []
        for quad, cands in st.session_state.cartographie_data.items():
            for cand in cands:
                cand_copy = cand.copy()
                cand_copy['quadrant'] = quad
                all_data.append(cand_copy)
        df = pd.DataFrame(all_data)
        st.download_button(
            "Télécharger CSV",
            df.to_csv(index=False),
            file_name="cartographie_talents.csv",
            mime="text/csv"
        )

# -------------------- Onglet 2 : Vue globale --------------------
with tab2:
    st.subheader("📊 Vue globale de la cartographie")
    try:
        import plotly.express as px
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
    except ImportError:
        st.warning("⚠️ La bibliothèque Plotly n'est pas installée. Le dashboard n'est pas disponible. Installez Plotly avec 'pip install plotly'.")
