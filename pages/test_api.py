import streamlit as st
import sys, os
from datetime import datetime
import json
import pandas as pd
from datetime import date
import random
from io import BytesIO
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    PDF_LIB_OK = True
except Exception:
    PDF_LIB_OK = False

# ✅ permet d'accéder à utils.py à la racine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    load_briefs,
    get_example_for_field,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
    generate_automatic_brief_name,
    save_library,
    generate_ai_question,
    test_deepseek_connection,
    save_brief_to_gsheet,
    export_brief_pdf_pretty,
    refresh_saved_briefs,          # <-- AJOUT
    load_all_local_briefs          # <-- AJOUT (si tu veux debugger)
)

# --- CSS pour augmenter la taille du texte des onglets ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 10px 16px !important;
    }
    .stButton > button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
    }
    .stDataFrame {
        width: 100%;
    }
    .stTextArea textarea {
        min-height: 100px;
        resize: vertical;
        white-space: pre-wrap !important;
    }
    </style>
""", unsafe_allow_html=True)

def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau et permet l'ajout de critères."""
    try:
        with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
            st.markdown("""### Méthode KSA (Knowledge, Skills, Abilities)
- **Knowledge (Connaissances)** : Savoirs théoriques nécessaires. Ex: Connaissances en normes de sécurité BTP (ISO 45001).
- **Skills (Compétences)** : Aptitudes pratiques acquises. Ex: Maîtrise d'AutoCAD pour dessiner des plans de chantier.
- **Abilities (Aptitudes)** : Capacités innées ou développées. Ex: Capacité à gérer des crises sur chantier.
            """)
        if "ksa_matrix" not in st.session_state:
            st.session_state.ksa_matrix = pd.DataFrame(columns=[
                "Rubrique", "Critère", "Type de question", "Cible / Standard attendu",
                "Échelle d'évaluation (1-5)", "Évaluateur"
            ])

        placeholder_dict = {
            "Comportementale": "Ex: Décrivez une situation où vous avez géré une équipe sous pression (méthode STAR).",
            "Situationnelle": "Ex: Que feriez-vous si un délai de chantier était menacé par un retard de livraison ?",
            "Technique": "Ex: Expliquez comment vous utilisez AutoCAD pour la modélisation de structures BTP.",
            "Générale": "Ex: Parlez-moi de votre expérience globale dans le secteur BTP."
        }

        with st.expander("➕ Ajouter un critère", expanded=True):
            # (bloc inchangé sauf que toutes les occurrences unsafe_allow_html sont confirmées)
            with st.form(key="add_ksa_criterion_form"):
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                cible = st.text_area("Cible / Standard attendu",
                                     placeholder="Définissez la cible ou le standard attendu pour ce critère.",
                                     key="new_cible", height=100,
                                     value=st.session_state.get("new_cible", ""))
                st.markdown("</div>", unsafe_allow_html=True)

                col1, col2, col3 = st.columns([1, 1, 1.5])
                with col1:
                    st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                    rubrique = st.selectbox(
                        "Rubrique", ["Knowledge", "Skills", "Abilities"],
                        key="new_rubrique",
                        index=["Knowledge", "Skills", "Abilities"].index(
                            st.session_state.get("new_rubrique", "Knowledge")
                        ) if st.session_state.get("new_rubrique") in ["Knowledge", "Skills", "Abilities"] else 0
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                    critere = st.text_input("Critère", key="new_critere",
                                            value=st.session_state.get("new_critere", ""))
                    type_question = st.selectbox(
                        "Type de question",
                        ["Comportementale", "Situationnelle", "Technique", "Générale"],
                        key="new_type_question",
                        index=["Comportementale", "Situationnelle", "Technique", "Générale"].index(
                            st.session_state.get("new_type_question", "Comportementale")
                        ) if st.session_state.get("new_type_question") in
                           ["Comportementale", "Situationnelle", "Technique", "Générale"] else 0
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                with col3:
                    st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                    evaluation = st.slider("Échelle d'évaluation (1-5)", 1, 5,
                                           value=st.session_state.get("new_evaluation", 3),
                                           step=1, key="new_evaluation")
                    evaluateur = st.selectbox(
                        "Évaluateur", ["Manager", "Recruteur", "Les deux"],
                        key="new_evaluateur",
                        index=["Manager", "Recruteur", "Les deux"].index(
                            st.session_state.get("new_evaluateur", "Manager")
                        ) if st.session_state.get("new_evaluateur") in
                           ["Manager", "Recruteur", "Les deux"] else 0
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("**Demander une question à l'IA**")
                ai_prompt = st.text_input(
                    "Décrivez ce que l'IA doit générer :",
                    placeholder="Ex: une question générale sur l'expérience en gestion de projet",
                    key="ai_prompt", value=st.session_state.get("ai_prompt", "")
                )
                st.checkbox("⚡ Mode rapide (réponse concise)", key="concise_checkbox")

                col_buttons = st.columns([1, 1])
                with col_buttons[0]:
                    if st.form_submit_button("💡 Générer question IA", use_container_width=True):
                        if ai_prompt:
                            try:
                                ai_response = generate_ai_question(
                                    ai_prompt,
                                    concise=st.session_state.concise_checkbox
                                )
                                st.session_state.ai_response = ai_response
                            except Exception as e:
                                st.error(f"Erreur génération IA : {e}")
                        else:
                            st.error("Veuillez entrer un prompt pour l'IA")

                with col_buttons[1]:
                    if st.form_submit_button("➕ Ajouter le critère", use_container_width=True):
                        if not critere or not cible:
                            st.error("Veuillez remplir au moins le critère et la cible.")
                        else:
                            new_row = pd.DataFrame([{
                                "Rubrique": rubrique,
                                "Critère": critere,
                                "Type de question": type_question,
                                "Cible / Standard attendu": cible,
                                "Échelle d'évaluation (1-5)": evaluation,
                                "Évaluateur": evaluateur
                            }])
                            st.session_state.ksa_matrix = pd.concat(
                                [st.session_state.ksa_matrix, new_row],
                                ignore_index=True
                            )
                            st.success("✅ Critère ajouté.")
                            st.rerun()

            if "ai_response" in st.session_state and st.session_state.ai_response:
                st.success(f"**Question :** {st.session_state.ai_response}")
                st.session_state.ai_response = ""

        if not st.session_state.ksa_matrix.empty:
            st.session_state.ksa_matrix = st.data_editor(
                st.session_state.ksa_matrix,
                hide_index=True,
                column_config={
                    "Rubrique": st.column_config.SelectboxColumn(
                        "Rubrique", options=["Knowledge", "Skills", "Abilities"], required=True),
                    "Critère": st.column_config.TextColumn("Critère", required=True),
                    "Type de question": st.column_config.SelectboxColumn(
                        "Type de question",
                        options=["Comportementale", "Situationnelle", "Technique", "Générale"],
                        required=True),
                    "Cible / Standard attendu": st.column_config.TextColumn(
                        "Cible / Standard attendu", required=True),
                    "Échelle d'évaluation (1-5)": st.column_config.NumberColumn(
                        "Échelle d'évaluation (1-5)", min_value=1, max_value=5, step=1, format="%d"),
                    "Évaluateur": st.column_config.SelectboxColumn(
                        "Évaluateur", options=["Manager", "Recruteur", "Les deux"], required=True),
                },
                num_rows="dynamic",
                use_container_width=True,
            )
    except Exception as e:
        st.error(f"❌ Erreur dans render_ksa_matrix: {e}")

def delete_current_brief():
    """Supprime le brief actuel et retourne à l'onglet Gestion"""
    if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
        brief_name = st.session_state.current_brief_name
        file_path = os.path.join("briefs", f"{brief_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            st.session_state.saved_briefs.pop(brief_name, None)
            save_briefs()
            
            st.session_state.current_brief_name = ""
            st.session_state.avant_brief_completed = True
            st.session_state.reunion_completed = True
            st.session_state.reunion_step = 1
            
            keys_to_reset = [
                "manager_nom", "niveau_hierarchique", "affectation_type", 
                "recruteur", "affectation_nom", "date_brief", "raison_ouverture",
                "impact_strategique", "rattachement", "taches_principales",
                "must_have_experience", "must_have_diplomes", "must_have_competences",
                "must_have_softskills", "nice_to_have_experience", "nice_to_have_diplomes",
                "nice_to_have_competences", "entreprises_profil", "synonymes_poste",
                "canaux_profil", "budget", "commentaires", "notes_libres"
            ]
            
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success(f"✅ Brief '{brief_name}' supprimé avec succès")
            st.session_state.brief_phase = "📁 Gestion"
            st.rerun()

# ---------------- INIT ----------------
init_session_state()
st.set_page_config(
    page_title="TG-Hire IA - Brief",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "brief_phase" not in st.session_state:
    st.session_state.brief_phase = "📁 Gestion"

if "reunion_step" not in st.session_state:
    st.session_state.reunion_step = 1

if "filtered_briefs" not in st.session_state:
    st.session_state.filtered_briefs = {}

if "avant_brief_completed" not in st.session_state:
    st.session_state.avant_brief_completed = True

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = True

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Gestion"

if "save_message" not in st.session_state:
    st.session_state.save_message = None
if "save_message_tab" not in st.session_state:
    st.session_state.save_message_tab = None

if "import_brief_flag" not in st.session_state:
    st.session_state.import_brief_flag = False
if "brief_to_import" not in st.session_state:
    st.session_state.brief_to_import = None

key_mapping = {
    "POSTE_INTITULE": "poste_intitule",
    "MANAGER_NOM": "manager_nom",
    "RECRUTEUR": "recruteur",
    "AFFECTATION_TYPE": "affectation_type",
    "AFFECTATION_NOM": "affectation_nom",
    "DATE_BRIEF": "date_brief",
    "RAISON_OUVERTURE": "raison_ouverture",
    "IMPACT_STRATEGIQUE": "impact_strategique",
    "TACHES_PRINCIPALES": "taches_principales",
    "MUST_HAVE_EXP": "must_have_experience",
    "MUST_HAVE_DIP": "must_have_diplomes",
    "MUST_HAVE_COMPETENCES": "must_have_competences",
    "MUST_HAVE_SOFTSKILLS": "must_have_softskills",
    "NICE_TO_HAVE_EXP": "nice_to_have_experience",
    "NICE_TO_HAVE_DIP": "nice_to_have_diplomes",
    "NICE_TO_HAVE_COMPETENCES": "nice_to_have_competences",
    "RATTACHEMENT": "rattachement",
    "BUDGET": "budget",
    "ENTREPRISES_PROFIL": "entreprises_profil",
    "SYNONYMES_POSTE": "synonymes_poste",
    "CANAUX_PROFIL": "canaux_profil",
    "LIEN_PROFIL_1": "profil_link_1",
    "LIEN_PROFIL_2": "profil_link_2",
    "LIEN_PROFIL_3": "profil_link_3",
    "COMMENTAIRES": "commentaires",
    "NOTES_LIBRES": "notes_libres"
}

sections = [
    {"title": "Contexte du poste", "fields": [
        ("Raison de l'ouverture", "raison_ouverture", ""),
        ("Impact stratégique", "impact_strategique", ""),
        ("Tâches principales", "taches_principales", "")]},
    {"title": "Must-have (Indispensables)", "fields": [
        ("Expérience", "must_have_experience", ""),
        ("Connaissances / Diplômes / Certifications", "must_have_diplomes", ""),
        ("Compétences / Outils", "must_have_competences", ""),
        ("Soft skills / aptitudes comportementales", "must_have_softskills", "")]},
    {"title": "Nice-to-have (Atouts)", "fields": [
        ("Expérience additionnelle", "nice_to_have_experience", ""),
        ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", ""),
        ("Compétences complémentaires", "nice_to_have_competences", "")]},
    {"title": "Conditions et contraintes", "fields": [
        ("Localisation", "rattachement", ""),
        ("Budget recrutement", "budget", "")]},
    {"title": "Sourcing et marché", "fields": [
        ("Entreprises où trouver ce profil", "entreprises_profil", ""),
        ("Synonymes / intitulés proches", "synonymes_poste", ""),
        ("Canaux à utiliser", "canaux_profil", "")]},
    {"title": "Profils pertinents", "fields": [
        ("Lien profil 1", "profil_link_1", ""),
        ("Lien profil 2", "profil_link_2", ""),
        ("Lien profil 3", "profil_link_3", "")]},
    {"title": "Notes libres", "fields": [
        ("Points à discuter ou à clarifier avec le manager", "commentaires", ""),
        ("Case libre", "notes_libres", "")]},
]

# --- Bloc d'import automatique ---
if st.session_state.import_brief_flag and st.session_state.brief_to_import:
    brief = load_briefs().get(st.session_state.brief_to_import, {})
    for sheet_key, session_key in key_mapping.items():
        st.session_state[session_key] = brief.get(sheet_key, "")
    for section in sections:
        for title, field_key, _ in section["fields"]:
            unique_key = f"{section['title'].replace(' ', '_')}_{field_key}"
            st.session_state[unique_key] = brief.get(key_mapping.get(field_key.upper(), field_key), "")
    st.session_state.current_brief_name = st.session_state.brief_to_import
    st.session_state.avant_brief_completed = True
    st.session_state.reunion_completed = True
    st.session_state.reunion_step = 1
    st.session_state.import_brief_flag = False
    st.session_state.brief_to_import = None
    st.rerun()
# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques Brief")

    # Rafraîchit (fusion) avant calcul
    merged = refresh_saved_briefs()
    total_briefs = len(merged)
    st.metric("📋 Briefs créés", total_briefs)

    if st.button("🔁 Recharger locaux", key="reload_local_briefs"):
        refresh_saved_briefs()
        st.rerun()

    st.divider()
    if st.button("Tester Connexion IA", key="test_deepseek"):
        test_deepseek_connection()

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

# Define tabs before using them
tabs = st.tabs([
    "📁 Gestion",
    "🔄 Avant-brief",
    "✅ Réunion de brief",
    "📝 Synthèse"
])

st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px;
}
.stTextArea textarea {
    white-space: pre-wrap !important;
}
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
    background-color: var(--background-color) !important;
    border-color: var(--border-color) !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select,
.stDateInput > div > div > input {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
}
:root {
    --background-color: #f0f2f6;
    --text-color: #31333F;
    --border-color: #d0d0d0;
}
@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #0e1117;
        --text-color: #fafafa;
        --border-color: #555555;
    }
}
</style>
""", unsafe_allow_html=True)

if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

all_field_keys = [
    "raison_ouverture", "impact_strategique", "taches_principales",
    "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
    "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences",
    "rattachement", "budget",
    "entreprises_profil", "synonymes_poste", "canaux_profil",
    "profil_link_1", "profil_link_2", "profil_link_3",
    "commentaires", "notes_libres",
    "canaux_prioritaires", "criteres_exclusion", "processus_evaluation", "manager_notes"
]

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {}) if st.session_state.current_brief_name else {}

    col_left, col_right = st.columns([2, 2])

    # Bloc "Créer un brief"
    with col_left:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Informations de base</h3>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Poste à recruter", key="poste_intitule", value=brief_data.get("poste_intitule", ""))
        with col2:
            st.text_input("Manager", key="manager_nom", value=brief_data.get("manager_nom", ""))
        with col3:
            st.selectbox("Recruteur", ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"], key="recruteur",
                index=["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"].index(brief_data.get("recruteur", "Zakaria")) if brief_data.get("recruteur", "Zakaria") in ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"] else 0)
        col4, col5, col6 = st.columns(3)
        with col4:
            st.selectbox("Type d'affectation", ["Chantier", "Siège", "Dépôt"], key="affectation_type",
                index=["Chantier", "Siège", "Dépôt"].index(brief_data.get("affectation_type", "Chantier")) if brief_data.get("affectation_type", "Chantier") in ["Chantier", "Siège", "Dépôt"] else 0)
        with col5:
            st.text_input("Nom affectation", key="affectation_nom", value=brief_data.get("affectation_nom", ""))
        with col6:
            # --- Normalisation robuste de la date avant le widget ---
            def _parse_date_any(v):
                if isinstance(v, date):
                    return v
                if isinstance(v, datetime):
                    return v.date()
                if isinstance(v, str):
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                        try:
                            return datetime.strptime(v, fmt).date()
                        except:
                            continue
                return date.today()

            # Valeur prioritaire : session_state si déjà existante
            if "date_brief" in st.session_state:
                # Sécurise le type avant d'appeler le widget (sinon warning)
                if not isinstance(st.session_state.date_brief, (date, datetime)):
                    st.session_state.date_brief = _parse_date_any(st.session_state.date_brief)
                elif isinstance(st.session_state.date_brief, datetime):
                    st.session_state.date_brief = st.session_state.date_brief.date()
                # IMPORTANT : ne pas passer 'value=' si key déjà présent (évite le warning jaune)
                chosen_date = st.date_input("Date du brief", key="date_brief")
            else:
                raw = brief_data.get("date_brief", brief_data.get("DATE_BRIEF", date.today()))
                date_brief_value = _parse_date_any(raw)
                chosen_date = st.date_input("Date du brief", value=date_brief_value, key="date_brief")

        if st.button("💾 Créer brief", type="primary", use_container_width=True, key="create_brief"):
            required_fields = ["poste_intitule", "manager_nom", "affectation_nom", "date_brief"]
            missing_fields = [field for field in required_fields if not st.session_state.get(field)]
            if missing_fields:
                st.error(f"Veuillez remplir les champs suivants : {', '.join(missing_fields)}")
            else:
                date_arg = st.session_state.date_brief
                if isinstance(date_arg, str):
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                        try:
                            date_arg = datetime.strptime(date_arg, fmt).date()
                            break
                        except:
                            continue
                if isinstance(date_arg, datetime):
                    date_arg = date_arg.date()

                new_brief_name = generate_automatic_brief_name(
                    st.session_state.poste_intitule,
                    st.session_state.manager_nom,
                    date_arg
                )
                date_str = date_arg.strftime("%Y-%m-%d")

                new_brief_data = {}
                base_pairs = {
                    "poste_intitule": "POSTE_INTITULE",
                    "manager_nom": "MANAGER_NOM",
                    "recruteur": "RECRUTEUR",
                    "affectation_type": "AFFECTATION_TYPE",
                    "affectation_nom": "AFFECTATION_NOM",
                    "date_brief": "DATE_BRIEF"
                }
                for low, up in base_pairs.items():
                    v = date_str if low == "date_brief" else st.session_state.get(low, "")
                    new_brief_data[low] = v
                    new_brief_data[up] = v

                for k in all_field_keys:
                    v = st.session_state.get(k, "")
                    new_brief_data[k] = v
                    if k.startswith("profil_link_"):
                        suffix = k.split("_")[-1]
                        new_brief_data[f"LIEN_PROFIL_{suffix}"] = v
                    else:
                        new_brief_data[k.upper()] = v

                # Mise à jour session + sauvegarde
                st.session_state.saved_briefs[new_brief_name] = new_brief_data
                st.session_state.current_brief_name = new_brief_name
                st.session_state.reunion_step = 1
                st.session_state.reunion_completed = False
                save_briefs()
                save_brief_to_gsheet(new_brief_name, new_brief_data)
                # Recalcule les stats immédiatement
                refresh_saved_briefs()
                st.success(f"✅ Brief '{new_brief_name}' créé avec succès !")
                st.rerun()

    # Bloc "Filtrer les briefs"
    with col_right:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">🔍 Filtrer les briefs</h3>', unsafe_allow_html=True)
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.date_input("Date", key="filter_date", value=None)
        with col_filter2:
            st.text_input("Recruteur", key="filter_recruteur", value=st.session_state.get("filter_recruteur", ""))
        with col_filter3:
            st.text_input("Manager", key="filter_manager", value=st.session_state.get("filter_manager", ""))

        col_filter4, col_filter5, col_filter6 = st.columns(3)
        with col_filter4:
            st.selectbox("Affectation", ["", "Chantier", "Siège", "Dépôt"], key="filter_affectation",
                        index=["", "Chantier", "Siège", "Dépôt"].index(st.session_state.get("filter_affectation", ""))
                        if st.session_state.get("filter_affectation") in ["", "Chantier", "Siège", "Dépôt"] else 0)
        with col_filter5:
            st.text_input("Nom affectation", key="filter_nom_affectation", value=st.session_state.get("filter_nom_affectation", ""))
        with col_filter6:
            st.selectbox("Type de brief", ["", "Standard", "Urgent", "Stratégique"], key="filter_brief_type",
                        index=["", "Standard", "Urgent", "Stratégique"].index(st.session_state.get("filter_brief_type", ""))
                        if st.session_state.get("filter_brief_type") in ["", "Standard", "Urgent", "Stratégique"] else 0)

        if st.button("🔎 Filtrer", use_container_width=True, key="apply_filter"):
            filter_month = st.session_state.filter_date.strftime("%m") if st.session_state.filter_date else ""
            st.session_state.filtered_briefs = filter_briefs(
                st.session_state.saved_briefs,
                filter_month,
                st.session_state.filter_recruteur,
                st.session_state.filter_brief_type,
                st.session_state.filter_manager,
                st.session_state.filter_affectation,
                st.session_state.filter_nom_affectation
            )
            st.session_state.show_filtered_results = True
            st.rerun()

    # Affichage des briefs sauvegardés
    briefs_to_show = st.session_state.saved_briefs if not st.session_state.get("show_filtered_results", False) else st.session_state.filtered_briefs

    if briefs_to_show and len(briefs_to_show) > 0:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
        for name, brief in briefs_to_show.items():
            col_brief1, col_brief2 = st.columns([6, 1])
            with col_brief1:
                st.markdown(f"**{name}**")
            with col_brief2:
                if st.button("📝 Éditer", key=f"edit_{name}"):
                    st.session_state.import_brief_flag = True
                    st.session_state.brief_to_import = name
                    st.rerun()
    else:
        st.info("Aucun brief sauvegardé ou correspondant aux filtres.")

# ---------------- AVANT-BRIEF ----------------
# Dans l'onglet Avant-brief (tabs[1])
with tabs[1]:
    brief_data = load_briefs().get(st.session_state.current_brief_name, {}) if st.session_state.current_brief_name else {}

    with st.form(key="avant_brief_form"):
        for section in sections:
            with st.expander(f"📋 {section['title']}", expanded=False):
                for title, key, placeholder in section["fields"]:
                    sheet_key = key.upper()
                    value = st.session_state.get(key, brief_data.get(sheet_key, ""))
                    st.text_area(
                        title,
                        value=value,
                        key=key,
                        placeholder=placeholder,
                        height=150
                    )
                    if st.session_state.get(f"advice_{key}", ""):
                        st.info(f"**Conseil IA :**\n{st.session_state[f'advice_{key}']}")
        # Ajout du bouton de soumission
        col_save = st.columns(1)[0]
        with col_save:
            if st.form_submit_button("💾 Enregistrer modifications", type="primary", use_container_width=True):
                if st.session_state.current_brief_name:
                    current_brief_name = st.session_state.current_brief_name
                    brief_to_update = st.session_state.saved_briefs.get(current_brief_name, {})
                    for section in sections:
                        for _, key, _ in section["fields"]:
                            val = st.session_state.get(key, "")
                            brief_to_update[key] = val
                            if key.startswith("profil_link_"):
                                suffix = key.split("_")[-1]
                                brief_to_update[f"LIEN_PROFIL_{suffix}"] = val
                            else:
                                brief_to_update[key.upper()] = val
                    # Champs de base si modifiés
                    for low in ["poste_intitule", "manager_nom", "recruteur",
                                "affectation_type", "affectation_nom", "date_brief"]:
                        if low in st.session_state:
                            v = st.session_state.get(low, "")
                            brief_to_update[low] = v
                            brief_to_update[low.upper()] = v
                    st.session_state.saved_briefs[current_brief_name] = brief_to_update
                    save_briefs()
                    save_brief_to_gsheet(current_brief_name, brief_to_update)
                    st.success("✅ Modifications sauvegardées avec succès.")
                    st.rerun()

# ---------------- REUNION BRIEF ----------------
with tabs[2]:
    st.subheader("✅ Réunion de brief")

    # Sécurisation de la variable d'étape
    if "reunion_step" not in st.session_state or not isinstance(st.session_state.reunion_step, int):
        st.session_state.reunion_step = 1
    total_steps = 4
    step = st.session_state.reunion_step

    if not st.session_state.current_brief_name:
        st.info("Sélectionnez ou créez d'abord un brief dans l'onglet Gestion.")
    else:
        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
        manager_comments_json = brief_data.get("MANAGER_COMMENTS_JSON", "{}")
        try:
            manager_comments = json.loads(manager_comments_json) if manager_comments_json else {}
        except Exception:
            manager_comments = {}

        # Utilitaire robuste
        def get_brief_value(brief_dict: dict, key: str, default: str = ""):
            if not brief_dict:
                return default
            if key.startswith("profil_link_"):
                suf = key.split("_")[-1]
                cand = [f"LIEN_PROFIL_{suf}", key.upper(), key]
            else:
                cand = [key.upper(), key]
            for c in cand:
                val = brief_dict.get(c, "")
                if val not in ("", None):
                    return val
            return default

        st.progress(int(step / total_steps * 100), text=f"Étape {step} sur {total_steps}")

        # ---------------- ÉTAPE 1 ----------------
        if step == 1:
            st.markdown("### 📝 Étape 1 : Portrait robot & Commentaires manager")
            table_data = []
            for section in sections:
                if section["title"] == "Profils pertinents":
                    continue
                for title, key, _ in section["fields"]:
                    table_data.append({
                        "Section": section["title"],
                        "Détails": title,
                        "Informations": get_brief_value(brief_data, key, ""),
                        "Commentaires du manager": manager_comments.get(key, ""),
                        "_key": key
                    })
            if not table_data:
                st.warning("Veuillez d'abord remplir l'onglet Avant-brief.")
            else:
                df = pd.DataFrame(table_data)
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Section": st.column_config.TextColumn(disabled=True),
                        "Détails": st.column_config.TextColumn(disabled=True),
                        "Informations": st.column_config.TextColumn(disabled=True, width="large"),
                        "Commentaires du manager": st.column_config.TextColumn(width="large"),
                        "_key": None
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="manager_comments_editor"
                )
                if st.button("💾 Enregistrer commentaires", type="primary"):
                    new_comments = {
                        row["_key"]: row["Commentaires du manager"]
                        for _, row in edited_df.iterrows()
                        if row["Commentaires du manager"]
                    }
                    brief_data["MANAGER_COMMENTS_JSON"] = json.dumps(new_comments, ensure_ascii=False, indent=2)
                    brief_data["manager_comments"] = new_comments
                    st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    st.success("Commentaires sauvegardés.")
                    st.rerun()

        # ---------------- ÉTAPE 2 ----------------
        elif step == 2:
            st.markdown("### 📊 Étape 2 : Matrice KSA")

            # Import silencieux
            def _import_ksa_from_json():
                json_str = (brief_data.get("KSA_MATRIX_JSON") or "").strip()
                if not json_str:
                    return
                try:
                    data = json.loads(json_str)
                    if not isinstance(data, list):
                        return
                    df = pd.DataFrame(data)
                    rename_map = {}
                    for col in df.columns:
                        c = col.strip()
                        lc = c.lower()
                        if lc.startswith("question"):
                            rename_map[col] = "Question pour l'entretien"
                        elif "échelle" in lc or "évaluation" in lc:
                            rename_map[col] = "Évaluation (1-5)"
                        elif "crit" in lc:
                            rename_map[col] = "Critère"
                        elif "rubrique" in lc:
                            rename_map[col] = "Rubrique"
                        elif "évaluateur" in lc:
                            rename_map[col] = "Évaluateur"
                        elif "type de question" in lc:
                            rename_map[col] = "Type de question"
                    if rename_map:
                        df = df.rename(columns=rename_map)
                    expected = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
                    for ccol in expected:
                        if ccol not in df.columns:
                            df[ccol] = ""
                    st.session_state.ksa_matrix = df[expected]
                except Exception:
                    pass

            if ("ksa_matrix" not in st.session_state) or st.session_state.ksa_matrix.empty:
                if brief_data.get("KSA_MATRIX_JSON"):
                    _import_ksa_from_json()
                else:
                    st.session_state.ksa_matrix = pd.DataFrame(columns=[
                        "Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"
                    ])

            # Exemples dynamiques (3 par combinaison Rubrique / Type)
            ksa_examples = {
                "Knowledge": {
                    "Comportementale": [
                        "Décrivez une norme clé que vous avez dû apprendre récemment.",
                        "Expliquez comment vous suivez les évolutions réglementaires.",
                        "Parlez d'une base de connaissances que vous avez structurée."
                    ],
                    "Situationnelle": [
                        "Si une nouvelle norme arrive la veille d'un audit, que faites-vous ?",
                        "Comment réagir si l'équipe ignore une procédure critique ?",
                        "Que faites-vous si la doc technique est obsolète ?"
                    ],
                    "Technique": [
                        "Citez les éléments essentiels d'une veille efficace.",
                        "Explique la différence entre deux cadres réglementaires.",
                        "Décrivez le processus de mise à jour documentaire."
                    ],
                    "Générale": [
                        "Comment évaluez-vous votre niveau de connaissances métier ?",
                        "Quelles sources vous utilisez pour apprendre rapidement ?",
                        "Comment structurez-vous vos apprentissages ?"
                    ]
                },
                "Skills": {
                    "Comportementale": [
                        "Décrivez une situation où vous avez optimisé un processus.",
                        "Parlez d'une action concrète ayant amélioré la qualité.",
                        "Décrivez une mission critique livrée sous pression."
                    ],
                    "Situationnelle": [
                        "Si une tâche prioritaire entre en conflit avec un blocage équipe ?",
                        "Que faites-vous si un livrable majeur est en retard ?",
                        "Comment adaptez-vous votre méthode si la charge double soudainement ?"
                    ],
                    "Technique": [
                        "Expliquez comment vous utilisez un outil clé du poste.",
                        "Décrivez votre méthode de diagnostic d'une panne complexe.",
                        "Comment automatisez-vous une tâche répétitive ?"
                    ],
                    "Générale": [
                        "Quelle compétence vous distingue le plus ?",
                        "Comment maintenez-vous vos compétences techniques ?",
                        "Donnez un exemple de montée en compétence rapide."
                    ]
                },
                "Abilities": {
                    "Comportementale": [
                        "Racontez une situation où votre résilience a été déterminante.",
                        "Expliquez un moment où votre leadership a redressé une équipe.",
                        "Parlez d'une situation nécessitant adaptabilité."
                    ],
                    "Situationnelle": [
                        "Que faites-vous si une décision rapide est requise avec peu d'infos ?",
                        "Comment réagissez-vous si deux parties clés sont en conflit ?",
                        "Si un imprévu majeur arrive en pleine phase critique ?"
                    ],
                    "Technique": [
                        "Comment structurez-vous votre analyse dans un contexte flou ?",
                        "Décrivez comment vous hiérarchisez des risques.",
                        "Expliquez comment vous cadrez une problématique complexe."
                    ],
                    "Générale": [
                        "Quelle est votre plus grande force transversale ?",
                        "Comment cultivez-vous votre adaptabilité ?",
                        "Qu'est-ce qui vous aide à rester concentré ?"
                    ]
                }
            }

            prompt_examples = {
                "Comportementale": [
                    "Ex: Génère une question comportementale sur la gestion de conflit.",
                    "Ex: Donne une question sur un échec transformé en réussite.",
                    "Ex: Propose une question sur l'amélioration continue."
                ],
                "Situationnelle": [
                    "Ex: Crée une question situationnelle sur un retard critique.",
                    "Ex: Génère une question sur priorisation multi-projets.",
                    "Ex: Donne une mise en situation sur gestion d'incident."
                ],
                "Technique": [
                    "Ex: Génère une question technique sur analyse de risque.",
                    "Ex: Donne une question sur optimisation d'un process.",
                    "Ex: Crée une question sur diagnostic de panne."
                ],
                "Générale": [
                    "Ex: Donne une question générale sur motivation.",
                    "Ex: Génère une question pour explorer adaptabilité.",
                    "Ex: Propose une question sur style de collaboration."
                ]
            }

            with st.expander("➕ Ajouter / Modifier un critère", expanded=True):
                with st.form("add_ksa_step2_form"):
                    col_top1, col_top2, col_top3, col_top4 = st.columns([1,1,1,1])
                    with col_top1:
                        rubrique = st.selectbox("Rubrique", ["Knowledge","Skills","Abilities"],
                                                key="step2_new_rubrique",
                                                index=["Knowledge","Skills","Abilities"].index(
                                                    st.session_state.get("step2_new_rubrique","Knowledge")
                                                ) if st.session_state.get("step2_new_rubrique","Knowledge") in ["Knowledge","Skills","Abilities"] else 0)
                    with col_top2:
                        type_question = st.selectbox("Type de question",
                                                     ["Comportementale","Situationnelle","Technique","Générale"],
                                                     key="step2_new_type_question",
                                                     index=["Comportementale","Situationnelle","Technique","Générale"].index(
                                                         st.session_state.get("step2_new_type_question","Comportementale")
                                                     ) if st.session_state.get("step2_new_type_question","Comportementale") in
                                                     ["Comportementale","Situationnelle","Technique","Générale"] else 0)
                    with col_top3:
                        critere = st.text_input("Critère", key="step2_new_critere",
                                                value=st.session_state.get("step2_new_critere",""))
                    with col_top4:
                        evaluateur = st.selectbox("Évaluateur",
                                                  ["Recruteur","Manager","Les deux"],
                                                  key="step2_new_evaluateur",
                                                  index=["Recruteur","Manager","Les deux"].index(
                                                      st.session_state.get("step2_new_evaluateur","Recruteur")
                                                  ) if st.session_state.get("step2_new_evaluateur","Recruteur") in
                                                  ["Recruteur","Manager","Les deux"] else 0)

                    # Placeholder dynamique pour la question
                    examples_list = ksa_examples.get(rubrique, {}).get(type_question, [])
                    dyn_q_placeholder = random.choice(examples_list) if examples_list else "Ex: Décrivez une situation pertinente."
                    prompt_list = prompt_examples.get(type_question, [])
                    dyn_prompt_placeholder = random.choice(prompt_list) if prompt_list else "Ex: Génère une question adaptée."

                    col_mid1, col_mid2 = st.columns([2,1])
                    with col_mid1:
                        question = st.text_area(
                            "Question pour l'entretien",
                            key="step2_new_question",
                            value=st.session_state.get("step2_new_question",""),
                            placeholder=dyn_q_placeholder,
                            height=60
                        )
                    with col_mid2:
                        evaluation = st.slider("Évaluation (1-5)", 1, 5,
                                               value=st.session_state.get("step2_new_evaluation",3),
                                               key="step2_new_evaluation")

                    cible = st.text_area(
                        "Cible / Standard attendu",
                        key="step2_new_cible",
                        value=st.session_state.get("step2_new_cible",""),
                        placeholder="Ex: Réponse structurée (méthode STAR), mise en avant de la coopération, précision factuelle.",
                        height=90
                    )

                    ai_prompt = st.text_input(
                        "Prompt IA (génération de question)",
                        key="step2_ai_prompt",
                        value=st.session_state.get("step2_ai_prompt",""),
                        placeholder=dyn_prompt_placeholder
                    )
                    concise_mode = st.checkbox("⚡ Mode rapide (réponse concise)", key="step2_concise_mode")

                    st.markdown("""
<style>
div.full-btn-container button {
    width:100% !important;
    font-weight:600;
    padding:0.8rem 1rem;
    font-size:0.95rem;
}
button[kind="secondary"] {
    background-color:#d30000 !important;
    color:#ffffff !important;
}
</style>
""", unsafe_allow_html=True)

                    gen_btn = st.form_submit_button("💡 Générer question IA", use_container_width=True)
                    add_btn = st.form_submit_button("➕ Ajouter le critère", use_container_width=True)

                    if gen_btn:
                        if ai_prompt:
                            try:
                                ai_resp = generate_ai_question(ai_prompt, concise=concise_mode)
                                if ai_resp.lower().startswith("question:"):
                                    ai_resp = ai_resp.split(":",1)[1].strip()
                                st.session_state.step2_new_question = ai_resp
                                st.success("Question générée.")
                            except Exception as e:
                                st.error(f"Erreur IA : {e}")
                        else:
                            st.warning("Entrez un prompt.")
                    if add_btn:
                        if not critere or not question:
                            st.error("Critère et question requis.")
                        else:
                            new_row = pd.DataFrame([{
                                "Rubrique": rubrique,
                                "Critère": critere,
                                "Type de question": type_question,
                                "Question pour l'entretien": question,
                                "Évaluation (1-5)": evaluation,
                                "Évaluateur": evaluateur
                            }])
                            if st.session_state.ksa_matrix.empty:
                                st.session_state.ksa_matrix = new_row
                            else:
                                st.session_state.ksa_matrix = pd.concat(
                                    [st.session_state.ksa_matrix, new_row],
                                    ignore_index=True
                                )
                            # Auto-save après ajout
                            try:
                                brief_data["KSA_MATRIX_JSON"] = st.session_state.ksa_matrix.to_json(orient="records", force_ascii=False)
                                st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                                save_briefs()
                                save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                            except Exception:
                                pass
                            st.success("Critère ajouté.")
                            st.rerun()

            # Edition + auto-save
            if not st.session_state.ksa_matrix.empty:
                edited = st.data_editor(
                    st.session_state.ksa_matrix,
                    hide_index=True,
                    use_container_width=True,
                    key="ksa_editor_step2",
                    num_rows="dynamic",
                    column_config={
                        "Rubrique": st.column_config.SelectboxColumn("Rubrique", options=["Knowledge","Skills","Abilities"]),
                        "Critère": st.column_config.TextColumn("Critère"),
                        "Type de question": st.column_config.SelectboxColumn("Type de question",
                            options=["Comportementale","Situationnelle","Technique","Générale"]),
                        "Question pour l'entretien": st.column_config.TextColumn("Question pour l'entretien", width="large"),
                        "Évaluation (1-5)": st.column_config.NumberColumn("Évaluation (1-5)", min_value=1, max_value=5, step=1),
                        "Évaluateur": st.column_config.SelectboxColumn("Évaluateur",
                            options=["Recruteur","Manager","Les deux"])
                    }
                )
                if not edited.equals(st.session_state.ksa_matrix):
                    st.session_state.ksa_matrix = edited
                    # Auto-save silencieux
                    try:
                        brief_data["KSA_MATRIX_JSON"] = st.session_state.ksa_matrix.to_json(orient="records", force_ascii=False)
                        st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                        save_briefs()
                        save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    except Exception:
                        pass

                # Score cible (moyenne)
                try:
                    if "Évaluation (1-5)" in st.session_state.ksa_matrix.columns:
                        avg_score = st.session_state.ksa_matrix["Évaluation (1-5)"].replace("", None).dropna().astype(float)
                        if len(avg_score) > 0:
                            score = round(avg_score.mean(), 2)
                            st.markdown(f"**Score cible moyen : {score} / 5**")
                            st.progress(min(1.0, score / 5))
                except Exception:
                    pass
            else:
                st.info("Aucun critère KSA pour le moment.")

# ================== PATCH ÉTAPE 3 (remplacer le bloc elif step == 3:) ==================
        elif step == 3:
            st.markdown("### 🛠️ Étape 3 : Stratégie & Processus")
            channels = ["LinkedIn","Jobboards","Jobzyn","Chasse de tête","Annonces","CVthèques"]
            if "canaux_prioritaires" not in st.session_state or not isinstance(st.session_state.canaux_prioritaires, list):
                st.session_state.canaux_prioritaires = []
            st.multiselect(
                "Canaux prioritaires de sourcing",
                channels,
                key="canaux_prioritaires",
                default=st.session_state.canaux_prioritaires
            )
            st.text_area(
                "🚫 Critères d'exclusion",
                key="criteres_exclusion",
                height=160,
                value=brief_data.get("CRITERES_EXCLUSION", st.session_state.get("criteres_exclusion","")),
                placeholder="Ex: Moins de 3 ans d'expérience / Pas de mobilité / Pas de certification X / Manque de maîtrise d'outil Y..."
            )
            st.text_area(
                "✅ Processus d'évaluation",
                key="processus_evaluation",
                height=160,
                value=brief_data.get("PROCESSUS_EVALUATION", st.session_state.get("processus_evaluation","")),
                placeholder="Ex: 1) Entretien téléphonique 2) Entretien technique 3) Étude de cas 4) Entretien final..."
            )
            if st.button("💾 Sauvegarder Étape 3", type="primary", key="save_step3"):
                brief_data["canaux_prioritaires"] = st.session_state.get("canaux_prioritaires", [])
                brief_data["CANAUX_PRIORITAIRES"] = json.dumps(brief_data["canaux_prioritaires"], ensure_ascii=False)
                for low, up in {
                    "criteres_exclusion":"CRITERES_EXCLUSION",
                    "processus_evaluation":"PROCESSUS_EVALUATION"
                }.items():
                    val = st.session_state.get(low,"")
                    brief_data[low] = val
                    brief_data[up] = val
                st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                save_briefs()
                save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                st.success("Étape 3 sauvegardée.")

# ---------------- SYNTHÈSE ----------------
with tabs[3]:
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Synthèse"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    if not st.session_state.current_brief_name:
        st.warning("⚠️ Veuillez créer ou sélectionner un brief dans l'onglet Gestion avant d'accéder à cette section.")
    elif not st.session_state.reunion_completed:
        st.warning("⚠️ Veuillez compléter la réunion de brief avant d'accéder à cette section.")
    else:
        st.subheader(f"📝 Synthèse - {st.session_state.current_brief_name}")
        
        brief_data = load_briefs().get(st.session_state.current_brief_name, {})
        # Fallback MAJUSCULE -> minuscules -> session_state
        poste = brief_data.get('POSTE_INTITULE') or brief_data.get('poste_intitule') or st.session_state.get('poste_intitule', 'N/A')
        manager = brief_data.get('MANAGER_NOM') or brief_data.get('manager_nom') or st.session_state.get('manager_nom', 'N/A')
        affect_nom = brief_data.get('AFFECTATION_NOM') or brief_data.get('affectation_nom') or st.session_state.get('affectation_nom', 'N/A')
        affect_type = brief_data.get('AFFECTATION_TYPE') or brief_data.get('affectation_type') or st.session_state.get('affectation_type', 'N/A')
        date_brief_disp = brief_data.get('DATE_BRIEF') or brief_data.get('date_brief') or str(st.session_state.get('date_brief', 'N/A'))

        st.write("### Informations générales")
        st.write(f"- **Poste :** {poste}")
        st.write(f"- **Manager :** {manager}")
        st.write(f"- **Affectation :** {affect_nom} ({affect_type})")
        st.write(f"- **Date :** {date_brief_disp}")
        
        st.write("### Détails du brief")
        for section in sections:
            with st.expander(f"📋 {section['title']}"):
                for title, key, _ in section["fields"]:
                    # Fallback clé upper / lower / session
                    value = (brief_data.get(key.upper()) or
                             brief_data.get(key) or
                             st.session_state.get(key, ""))
                    if value:
                        st.write(f"- **{title} :** {value}")
        
        if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
            st.subheader("📊 Matrice KSA")
            st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
        
        st.write("### Actions")
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True, key="save_synthese"):
                if st.session_state.current_brief_name:
                    save_briefs()
                    brief_data_to_save = load_briefs().get(st.session_state.current_brief_name, {})
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data_to_save)
                    st.session_state.save_message = f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !"
                    st.session_state.save_message_tab = "Synthèse"
                    st.rerun()
                else:
                    st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")
        
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_synthese"):
                delete_current_brief()

        st.subheader("📄 Export du Brief complet")
        col1, col2 = st.columns(2)
        with col1:
            if PDF_AVAILABLE:
                if st.session_state.current_brief_name:
                    ksa_df = st.session_state.ksa_matrix if "ksa_matrix" in st.session_state else None
                    pdf_buf = export_brief_pdf_pretty(st.session_state.current_brief_name, brief_data, ksa_df)
                    if pdf_buf:
                        st.download_button(
                            "⬇️ Télécharger PDF",
                            data=pdf_buf,
                            file_name=f"{st.session_state.current_brief_name}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ PDF non dispo (pip install reportlab)")
        with col2:
            if WORD_AVAILABLE:
                if st.session_state.current_brief_name:
                    word_buf = export_brief_word()
                    if word_buf:
                        st.download_button(
                            "⬇️ Télécharger Word",
                            data=word_buf,
                            file_name=f"{st.session_state.current_brief_name}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ Word non dispo (pip install python-docx)")

def save_briefs():
    """
    Sauvegarde locale :
    - briefs/briefs.json (global)
    - briefs/<nom>.json (un fichier par brief pour compatibilité ancienne logique)
    Conversion sûre des dates / datetime en chaînes ISO.
    """
    import json, os
    from datetime import date, datetime
    briefs = st.session_state.get("saved_briefs", {}) or {}

    def convert(obj):
        if isinstance(obj, (date, datetime)):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(x) for x in obj]
        return obj

    os.makedirs("briefs", exist_ok=True)
    safe_global = {}
    for name, data in briefs.items():
        safe_data = convert(data)
        safe_global[name] = safe_data
        # fichier individuel
        try:
            with open(os.path.join("briefs", f"{name}.json"), "w", encoding="utf-8") as f_ind:
                json.dump(safe_data, f_ind, ensure_ascii=False, indent=2)
        except Exception as e:
            st.warning(f"⚠️ Impossible d'écrire le fichier individuel '{name}.json': {e}")

    try:
        with open(os.path.join("briefs", "briefs.json"), "w", encoding="utf-8") as f_all:
            json.dump(safe_global, f_all, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde locale des briefs: {e}")

@st.cache_data(ttl=120)
def load_all_local_briefs():
    """
    Charge tous les briefs depuis briefs.json (fallback : fichiers individuels).
    """
    import json, os
    folder = "briefs"
    collected = {}
    try:
        path_global = os.path.join(folder, "briefs.json")
        if os.path.exists(path_global):
            with open(path_global, "r", encoding="utf-8") as f:
                collected = json.load(f)
        else:
            if os.path.isdir(folder):
                for fn in os.listdir(folder):
                    if fn.endswith(".json") and fn != "briefs.json":
                        try:
                            with open(os.path.join(folder, fn), "r", encoding="utf-8") as f:
                                data = json.load(f)
                                name = fn[:-5]
                                collected[name] = data
                        except:
                            continue
    except Exception:
        pass
    return collected

def refresh_saved_briefs():
    """
    Fusion (sans écraser les briefs déjà en session avec modifications récentes).
    """
    local = load_all_local_briefs()
    sess = st.session_state.get("saved_briefs", {})
    merged = {**local, **sess}  # priorité aux données en session
    st.session_state.saved_briefs = merged
    return merged