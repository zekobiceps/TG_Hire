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
            from datetime import date as _Date, datetime as _DateTime

            def _parse_date_any(v):
                if isinstance(v, _Date) and not isinstance(v, _DateTime):
                    return v
                if isinstance(v, _DateTime):
                    return v.date()
                if isinstance(v, str):
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                        try:
                            return _DateTime.strptime(v, fmt).date()
                        except:
                            continue
                return _Date.today()

            # Toujours re-normaliser (même si déjà présent)
            raw_val = st.session_state.get("date_brief")
            if raw_val is None:
                raw_val = brief_data.get("DATE_BRIEF") or brief_data.get("date_brief") or _Date.today()
            norm = _parse_date_any(raw_val)
            st.session_state.date_brief = norm  # on force un objet date

            # IMPORTANT: ne pas passer 'value=' puisque key déjà défini
            st.date_input("Date du brief", key="date_brief")

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

                new_brief_data["BRIEF_NAME"] = new_brief_name

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

    # Affichage des briefs : seulement après Filtrer OU après activation recherche
    briefs_to_show = {}
    if st.session_state.get("show_filtered_results"):
        briefs_to_show = st.session_state.filtered_briefs
    # Recherche (masque sinon)
    if st.checkbox("🔍 Chercher un brief", key="toggle_search_briefs"):
        search = st.text_input("Rechercher (nom contient...)", key="search_brief_query")
        briefs_to_show = st.session_state.get("saved_briefs", {})
        if search:
            briefs_to_show = {k: v for k, v in briefs_to_show.items() if search.lower() in k.lower()}

    if briefs_to_show:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
        for name in sorted(briefs_to_show.keys()):
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                st.write(f"• {name}")
            with c2:
                if st.button("✏️", key=f"edit_{name}", help="Éditer"):
                    st.session_state.import_brief_flag = True
                    st.session_state.brief_to_import = name
                    st.rerun()
            with c3:
                if st.button("🗑️", key=f"del_{name}", help="Supprimer"):
                    st.session_state.saved_briefs.pop(name, None)
                    save_briefs()
                    st.success("Supprimé.")
                    st.rerun()
    else:
        st.info("Aucun brief affiché (utilisez Filtrer ou Chercher).")

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

    # Barre de progression étapes (toujours visible)
    total_steps = 4
    if "reunion_step" not in st.session_state or not isinstance(st.session_state.reunion_step, int):
        st.session_state.reunion_step = 1
    step = st.session_state.reunion_step
    pct = int(((step - 1) / (total_steps - 1)) * 100)
    st.progress(pct, text=f"Étape {step}/{total_steps}")

    if not st.session_state.current_brief_name:
        st.info("Sélectionnez ou créez d'abord un brief dans l'onglet Gestion.")
    else:
        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})

        # --- Import KSA si vide & JSON dispo ---
        if ("ksa_matrix" not in st.session_state or st.session_state.ksa_matrix is None or getattr(st.session_state.ksa_matrix, "empty", True)) and brief_data.get("KSA_MATRIX_JSON"):
            try:
                raw = json.loads(brief_data["KSA_MATRIX_JSON"])
                if isinstance(raw, list) and raw:
                    df_imp = pd.DataFrame(raw)
                    rename_map = {
                        "Échelle d'évaluation (1-5)": "Évaluation (1-5)",
                        "Echelle d'évaluation (1-5)": "Évaluation (1-5)",
                        "Evaluation (1-5)": "Évaluation (1-5)",
                        "Question": "Question pour l'entretien",
                        "Question entretien": "Question pour l'entretien"
                    }
                    for k, v in list(rename_map.items()):
                        if k in df_imp.columns and v not in df_imp.columns:
                            df_imp = df_imp.rename(columns={k: v})
                    needed = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
                    for c in needed:
                        if c not in df_imp.columns:
                            df_imp[c] = ""
                    st.session_state.ksa_matrix = df_imp[needed]
            except Exception:
                st.session_state.ksa_matrix = pd.DataFrame(columns=["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"])

        # Utilitaire pour valeurs
        def get_brief_value(brief_dict: dict, key: str, default: str = ""):
            if key.startswith("profil_link_"):
                suf = key.split("_")[-1]
                cand = [f"LIEN_PROFIL_{suf}", key.upper(), key]
            else:
                cand = [key.upper(), key]
            for c in cand:
                if c in brief_dict and brief_dict[c] not in ("", None):
                    return brief_dict[c]
            return default

        # ---------------- ÉTAPE 1 ----------------
        if step == 1:
            st.markdown("### 📝 Étape 1 : Vue consolidée & commentaires manager")
            table_data = []
            for section in sections:
                if section["title"] == "Profils pertinents":
                    continue
                for title, key, _ in section["fields"]:
                    table_data.append({
                        "Section": section["title"],
                        "Item": title,
                        "Infos": get_brief_value(brief_data, key, ""),
                        "Commentaire manager": brief_data.get("manager_comments", {}).get(key, ""),
                        "_key": key
                    })
            if not table_data:
                st.warning("Veuillez remplir l’Avant-brief d’abord.")
            else:
                df = pd.DataFrame(table_data)
                edited = st.data_editor(
                    df,
                    hide_index=True,
                    column_config={
                        "Section": st.column_config.TextColumn(disabled=True),
                        "Item": st.column_config.TextColumn(disabled=True),
                        "Infos": st.column_config.TextColumn(disabled=True),
                        "Commentaire manager": st.column_config.TextColumn()
                    },
                    key="manager_comments_editor_rb"
                )
                if st.button("💾 Enregistrer commentaires", key="save_mgr_comments"):
                    new_comments = {
                        row["_key"]: row["Commentaire manager"]
                        for _, row in edited.iterrows() if row["Commentaire manager"]
                    }
                    brief_data["manager_comments"] = new_comments
                    brief_data["MANAGER_COMMENTS_JSON"] = json.dumps(new_comments, ensure_ascii=False)
                    st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    st.success("Commentaires sauvegardés.")
                    st.rerun()

        # ---------------- ÉTAPE 2 (KSA) ----------------
        elif step == 2:
            st.markdown("### 📊 Étape 2 : Matrice KSA")
            with st.expander("ℹ️ Méthode KSA (détails & exemples)", expanded=False):
                st.markdown("""
**KSA = Knowledge / Skills / Abilities**  
Objectif : structurer les questions d'entretien pour réduire les biais et couvrir tous les angles essentiels.

🧠 Knowledge (Connaissances)  
- Ce que la personne sait (théorique / réglementaire).  
- Ex: Normes sécurité BTP, réglementation environnementale, principes Lean.

💪 Skills (Compétences pratiquées)  
- Ce qu’elle sait faire concrètement / transférable.  
- Ex: Planification chantier, usage d’AutoCAD, gestion fournisseurs, animation réunion sécurité.

✨ Abilities (Aptitudes / Capacités)  
- Traits durables & comportement stable observable.  
- Ex: Leadership terrain, prise de décision rapide, négociation sous pression.

🎯 Types de questions :
- Comportementale → passé réel (méthode STAR)
- Situationnelle → hypothétique « que feriez-vous si… »
- Technique → validation expertise ciblée
- Générale → vision, structuration, maturité

Exemples de formulation :
- Skills / Situationnelle : “Si deux urgences chantier tombent simultanément, que priorisez-vous et pourquoi ?”
- Knowledge / Technique : “Expliquez les étapes critiques d’un PPSPS sur chantier.”
- Abilities / Comportementale : “Décrivez une situation où vous avez dû recadrer un sous-traitant en tension.”

Bonnes pratiques :
- 4 à 7 critères bien calibrés suffisent pour une grille initiale.
- Chaque question doit mesurer un critère unique.
- Indiquer l’évaluateur (Manager / Recruteur / Les deux) pour structurer le déroulé.
""")

            # Charger JSON si pas encore en mémoire
            if ("ksa_matrix" not in st.session_state or st.session_state.ksa_matrix is None or getattr(st.session_state.ksa_matrix, "empty", True)) and brief_data.get("KSA_MATRIX_JSON"):
                try:
                    parsed = json.loads(brief_data["KSA_MATRIX_JSON"])
                    st.session_state.ksa_matrix = pd.DataFrame(parsed)
                except Exception:
                    st.session_state.ksa_matrix = pd.DataFrame(columns=["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"])

            with st.form("add_ksa_form"):
                c1, c2, c3, c4 = st.columns([1,1,1,1])
                with c1:
                    rubrique = st.selectbox("Rubrique", ["Knowledge","Skills","Abilities"], key="ksa_form_rubrique")
                with c2:
                    critere = st.text_input("Critère", key="ksa_form_critere")
                with c3:
                    type_q = st.selectbox("Type de question", ["Comportementale","Situationnelle","Technique","Générale"], key="ksa_form_type_q")
                with c4:
                    evaluateur = st.selectbox("Évaluateur", ["Recruteur","Manager","Les deux"], key="ksa_form_evaluateur")

                q_col, eval_col = st.columns([3,1])
                with q_col:
                    question = st.text_input("Question pour l'entretien", key="ksa_form_question", placeholder="Ex: Si un retard critique menace la livraison...")
                with eval_col:
                    evaluation = st.slider("Évaluation (1-5)", 1, 5, 3, key="ksa_form_eval")

                # Prompt + mode rapide dessous
                prompt = st.text_input("Prompt IA (génération de question ciblée)", key="ksa_form_prompt",
                                       placeholder="Ex: question situationnelle sur gestion de risques chantier")
                st.checkbox("⚡ Mode rapide (réponse concise)", key="ksa_form_concise")

                col_btn_gen, col_btn_add = st.columns(2)
                with col_btn_gen:
                    gen = st.form_submit_button("💡 Générer IA", use_container_width=True)
                with col_btn_add:
                    add = st.form_submit_button("➕ Ajouter", use_container_width=True)

                # CSS bouton Générer uniquement
                st.markdown("""
<style>
button[kind="secondary"]:contains('Générer IA'),
div[data-testid="baseButton-secondary"] button:has(span:contains('Générer IA')) {
    background:#c40000 !important;
    color:#fff !important;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

                if gen:
                    if not prompt:
                        st.warning("Indique un prompt.")
                    else:
                        try:
                            resp = generate_ai_question(prompt, concise=st.session_state.ksa_form_concise)
                            if resp.lower().startswith("question:"):
                                resp = resp.split(":",1)[1].strip()
                            st.session_state.ksa_form_question = resp
                            st.success("Question générée.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur IA: {e}")

                if add:
                    if not critere or not question:
                        st.error("Critère + question requis.")
                    else:
                        new_row = {
                            "Rubrique": rubrique,
                            "Critère": critere,
                            "Type de question": type_q,
                            "Question pour l'entretien": question,
                            "Évaluation (1-5)": evaluation,
                            "Évaluateur": evaluateur
                        }
                        if "ksa_matrix" not in st.session_state or st.session_state.ksa_matrix is None or st.session_state.ksa_matrix.empty:
                            st.session_state.ksa_matrix = pd.DataFrame([new_row])
                        else:
                            st.session_state.ksa_matrix = pd.concat(
                                [st.session_state.ksa_matrix, pd.DataFrame([new_row])],
                                ignore_index=True
                            )
                        save_ksa_matrix_to_current_brief()
                        st.success("Critère ajouté.")
                        st.rerun()

            if "ksa_matrix" in st.session_state and isinstance(st.session_state.ksa_matrix, pd.DataFrame) and not st.session_state.ksa_matrix.empty:
                cols_order = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
                for c in cols_order:
                    if c not in st.session_state.ksa_matrix.columns:
                        st.session_state.ksa_matrix[c] = ""
                edited = st.data_editor(
                    st.session_state.ksa_matrix[cols_order],
                    hide_index=True,
                    use_container_width=True,
                    key="ksa_editor_step2",
                    column_config={
                        "Rubrique": st.column_config.SelectboxColumn("Rubrique", options=["Knowledge","Skills","Abilities"]),
                        "Type de question": st.column_config.SelectboxColumn("Type de question",
                            options=["Comportementale","Situationnelle","Technique","Générale"]),
                        "Évaluation (1-5)": st.column_config.NumberColumn("Évaluation (1-5)", min_value=1, max_value=5),
                        "Évaluateur": st.column_config.SelectboxColumn("Évaluateur", options=["Recruteur","Manager","Les deux"])
                    }
                )
                if not edited.equals(st.session_state.ksa_matrix[cols_order]):
                    st.session_state.ksa_matrix = edited
                    save_ksa_matrix_to_current_brief()
                try:
                    avg = round(st.session_state.ksa_matrix["Évaluation (1-5)"].astype(float).mean(), 2)
                    st.markdown(f"<div style='font-size:22px;margin-top:8px;'>🎯 Score cible moyen : {avg} / 5</div>", unsafe_allow_html=True)
                except:
                    pass
            else:
                st.info("Aucun critère KSA actuellement.")

# --- SYNTHÈSE : AJOUT NOTE CIBLE MOYENNE EN BAS (REMPLACER L'AFFICHAGE KSA) ---
        if "ksa_matrix" not in st.session_state or st.session_state.ksa_matrix is None or st.session_state.ksa_matrix.empty:
            # Tenter de charger depuis JSON du brief
            kjson = brief_data.get("KSA_MATRIX_JSON","")
            if kjson:
                try:
                    st.session_state.ksa_matrix = pd.DataFrame(json.loads(kjson))
                except:
                    st.session_state.ksa_matrix = pd.DataFrame()

        if "ksa_matrix" in st.session_state and isinstance(st.session_state.ksa_matrix, pd.DataFrame) and not st.session_state.ksa_matrix.empty:
            st.subheader("📊 Matrice KSA")
            show_df = st.session_state.ksa_matrix.copy()
            needed_cols = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
            for c in needed_cols:
                if c not in show_df.columns:
                    show_df[c] = ""
            st.dataframe(show_df[needed_cols], use_container_width=True, hide_index=True)
            try:
                avg2 = round(show_df["Évaluation (1-5)"].astype(float).mean(), 2)
                st.markdown(f"<div style='font-size:22px;margin-top:6px;'>🎯 Score cible moyen : {avg2} / 5</div>", unsafe_allow_html=True)
            except:
                pass

# --- ASSURER LA SAUVEGARDE KSA DANS L'ÉTAPE 4 FINALE ---
# Dans le bouton de finalisation / sauvegarde réunion ou synthèse, ajouter l'appel :
#   save_ksa_matrix_to_current_brief()
def save_ksa_matrix_to_current_brief():
    """
    Sauvegarde la matrice KSA courante (st.session_state.ksa_matrix) dans le brief actif :
    - Sérialise en JSON (KSA_MATRIX_JSON)
    - Retire la DataFrame brute du dict avant save_briefs()
    """
    import pandas as pd
    if not st.session_state.get("current_brief_name"):
        return
    if "ksa_matrix" not in st.session_state or not isinstance(st.session_state.ksa_matrix, pd.DataFrame):
        return
    df = st.session_state.ksa_matrix
    if df.empty:
        return
    # Colonnes attendues
    cols = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    bname = st.session_state.current_brief_name
    brief_dict = st.session_state.saved_briefs.get(bname, {})
    try:
        brief_dict["KSA_MATRIX_JSON"] = df.to_json(orient="records", force_ascii=False)
        # on n'essaie pas de stocker la DataFrame brute dans le dict
        if "ksa_matrix" in brief_dict:
            brief_dict.pop("ksa_matrix", None)
        st.session_state.saved_briefs[bname] = brief_dict
        save_briefs()
        save_brief_to_gsheet(bname, brief_dict)
    except Exception as e:
        st.warning(f"Erreur sauvegarde KSA: {e}")