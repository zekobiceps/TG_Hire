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
            with st.expander("ℹ️ Méthode KSA", expanded=False):
                st.markdown("""
**KSA = Knowledge / Skills / Abilities**  
Exemples rapides :
- Skills / Situationnelle → "Si un livrable critique est bloqué, que faites-vous ?"
- Knowledge / Technique → "Explique la différence entre deux méthodes d'analyse."
- Abilities / Comportementale → "Raconte une situation où ton leadership a débloqué un problème."
🎯 Objectif : Structurer l’entretien & réduire les biais.
""")

            # Formulaire ajout critère
            with st.form("add_ksa_form_rb"):
                c1, c2, c3, c4 = st.columns([1,1,1,1])
                with c1:
                    rubrique = st.selectbox("Rubrique", ["Knowledge","Skills","Abilities"],
                                            key="rb_new_rubrique",
                                            index=["Knowledge","Skills","Abilities"].index(
                                                st.session_state.get("rb_new_rubrique","Knowledge")
                                            ) if st.session_state.get("rb_new_rubrique","Knowledge") in ["Knowledge","Skills","Abilities"] else 0)
                with c2:
                    type_q = st.selectbox("Type de question",
                                          ["Comportementale","Situationnelle","Technique","Générale"],
                                          key="rb_new_type_question",
                                          index=["Comportementale","Situationnelle","Technique","Générale"].index(
                                              st.session_state.get("rb_new_type_question","Comportementale")
                                          ) if st.session_state.get("rb_new_type_question","Comportementale") in
                                          ["Comportementale","Situationnelle","Technique","Générale"] else 0)
                with c3:
                    critere = st.text_input("Critère", key="rb_new_critere",
                                            value=st.session_state.get("rb_new_critere",""))
                with c4:
                    evaluateur = st.selectbox("Évaluateur",
                                              ["Recruteur","Manager","Les deux"],
                                              key="rb_new_evaluateur",
                                              index=["Recruteur","Manager","Les deux"].index(
                                                  st.session_state.get("rb_new_evaluateur","Recruteur")
                                              ) if st.session_state.get("rb_new_evaluateur","Recruteur") in
                                              ["Recruteur","Manager","Les deux"] else 0)
                # Placeholder question
                placeholders = {
                    ("Skills","Situationnelle"): "Ex: Si un site prend 2 semaines de retard...",
                    ("Skills","Technique"): "Ex: Décris ta méthode de diagnostic...",
                    ("Abilities","Comportementale"): "Ex: Raconte une situation de conflit géré...",
                    ("Knowledge","Technique"): "Ex: Explique un concept clé récent...",
                }
                dyn_q = placeholders.get((rubrique, type_q), "Ex: Formule une question ciblée.")
                qc, evalc = st.columns([3,1])
                with qc:
                    question = st.text_input("Question pour l'entretien",
                                             key="rb_new_question",
                                             value=st.session_state.get("rb_new_question",""),
                                             placeholder=dyn_q)
                with evalc:
                    evaluation = st.slider("Évaluation (1-5)", 1,5,
                                           key="rb_new_evaluation",
                                           value=st.session_state.get("rb_new_evaluation",3))
                pc1, pc2 = st.columns([2,2])
                with pc1:
                    ai_prompt = st.text_input("Prompt IA",
                                              key="rb_ai_prompt",
                                              value=st.session_state.get("rb_ai_prompt",""),
                                              placeholder="Ex: question situationnelle priorisation")
                with pc2:
                    concise_mode = st.checkbox("⚡ Concis", key="rb_ai_concise")

                btn_left, btn_right = st.columns([1,1])
                with btn_left:
                    gen_btn = st.form_submit_button("💡 Générer IA", use_container_width=True)
                with btn_right:
                    add_btn = st.form_submit_button("➕ Ajouter", use_container_width=True)

                st.markdown("""
<style>
button[kind="secondary"] {
    background:#cc0000 !important;
    color:#fff !important;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

                if gen_btn:
                    if not ai_prompt:
                        st.warning("Indique un prompt.")
                    else:
                        try:
                            resp = generate_ai_question(ai_prompt, concise=concise_mode)
                            if resp.lower().startswith("question:"):
                                resp = resp.split(":",1)[1].strip()
                            st.session_state.rb_new_question = resp
                            st.success("Question générée.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur IA: {e}")

                if add_btn:
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
                        if "ksa_matrix" not in st.session_state or st.session_state.ksa_matrix.empty:
                            st.session_state.ksa_matrix = pd.DataFrame([new_row])
                        else:
                            st.session_state.ksa_matrix = pd.concat(
                                [st.session_state.ksa_matrix, pd.DataFrame([new_row])],
                                ignore_index=True
                            )
                        # Sauvegarde
                        try:
                            brief_data["KSA_MATRIX_JSON"] = st.session_state.ksa_matrix.to_json(orient="records", force_ascii=False)
                            st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                            save_briefs()
                            save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                        except Exception:
                            pass
                        st.success("Critère ajouté.")
                        st.rerun()

            # Éditeur
            if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
                edited = st.data_editor(
                    st.session_state.ksa_matrix,
                    hide_index=True,
                    use_container_width=True,
                    key="rb_ksa_editor",
                    column_config={
                        "Rubrique": st.column_config.SelectboxColumn("Rubrique", options=["Knowledge","Skills","Abilities"]),
                        "Critère": st.column_config.TextColumn("Critère"),
                        "Type de question": st.column_config.SelectboxColumn("Type de question",
                            options=["Comportementale","Situationnelle","Technique","Générale"]),
                        "Question pour l'entretien": st.column_config.TextColumn("Question pour l'entretien"),
                        "Évaluation (1-5)": st.column_config.NumberColumn("Évaluation (1-5)", min_value=1, max_value=5),
                        "Évaluateur": st.column_config.SelectboxColumn("Évaluateur", options=["Recruteur","Manager","Les deux"])
                    }
                )
                if not edited.equals(st.session_state.ksa_matrix):
                    st.session_state.ksa_matrix = edited
                    try:
                        brief_data["KSA_MATRIX_JSON"] = edited.to_json(orient="records", force_ascii=False)
                        st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                        save_briefs()
                        save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    except Exception:
                        pass
                try:
                    vals = edited["Évaluation (1-5)"].dropna().astype(float)
                    if len(vals) > 0:
                        avg = round(vals.mean(), 2)
                        st.markdown(f"<h3 style='margin-top:6px;'>Score cible moyen : {avg} / 5 🎯</h3>", unsafe_allow_html=True)
                except:
                    pass
            else:
                st.info("Aucun critère KSA pour l’instant.")

        # ---------------- ÉTAPE 3 ----------------
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
            left_c, right_c = st.columns(2)
            with left_c:
                st.text_area(
                    "🚫 Critères d'exclusion",
                    key="criteres_exclusion",
                    height=200,
                    placeholder="Ex: Moins de 3 ans sur poste similaire / Pas d'expérience multi-sites..."
                )
            with right_c:
                st.text_area(
                    "🛠️ Processus d'évaluation",
                    key="processus_evaluation",
                    height=200,
                    placeholder="Ex: 1. Screening / 2. Manager / 3. Visite / 4. Décision."
                )

        # ---------------- ÉTAPE 4 ----------------
        elif step == 4:
            st.markdown("### ✅ Étape 4 : Validation finale")
            st.text_area(
                "🗒️ Notes / Commentaires finaux du manager",
                key="manager_notes",
                height=220,
                placeholder="Ex: Sensibilité sécurité, posture terrain, autonomie attendue..."
            )
            st.info("Clique sur Sauvegarder & Finaliser pour activer la Synthèse.")
            if st.button("💾 Sauvegarder & Finaliser", key="finalize_brief"):
                bname = st.session_state.current_brief_name
                bdata = st.session_state.saved_briefs.get(bname, {})
                bdata["MANAGER_NOTES"] = st.session_state.get("manager_notes","")
                # Ajouter KSA JSON si présent
                if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
                    try:
                        bdata["KSA_MATRIX_JSON"] = st.session_state.ksa_matrix.to_json(orient="records", force_ascii=False)
                    except Exception:
                        pass
                st.session_state.saved_briefs[bname] = bdata
                save_briefs()
                save_brief_to_gsheet(bname, bdata)
                st.session_state.reunion_completed = True
                st.success("Brief finalisé. Accédez à la Synthèse.")
                st.rerun()

        # --- Navigation Wizard (après contenu étape) ---
        nav_left, nav_right = st.columns([1,1])
        with nav_left:
            if step > 1 and st.button("⬅️ Précédent", key=f"prev_{step}", help="Retour étape précédente"):
                st.session_state.reunion_step -= 1
                st.rerun()
        with nav_right:
            if step < total_steps and st.button("Suivant ➡️", key=f"next_{step}", help="Étape suivante"):
                # Auto-save (étapes 1–3 seulement)
                if step in (1,2,3) and st.session_state.current_brief_name:
                    bname = st.session_state.current_brief_name
                    bdata = st.session_state.saved_briefs.get(bname, {})
                    bdata["CRITERES_EXCLUSION"] = st.session_state.get("criteres_exclusion","")
                    bdata["PROCESSUS_EVALUATION"] = st.session_state.get("processus_evaluation","")
                    bdata["MANAGER_NOTES"] = st.session_state.get("manager_notes","")
                    if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
                        try:
                            bdata["KSA_MATRIX_JSON"] = st.session_state.ksa_matrix.to_json(orient="records", force_ascii=False)
                        except Exception:
                            pass
                    bdata.pop("ksa_matrix", None)
                    st.session_state.saved_briefs[bname] = bdata
                    save_briefs()
                    save_brief_to_gsheet(bname, bdata)
                st.session_state.reunion_step += 1
                st.rerun()

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

# --- Fin du fichier (fonctions utilitaires centralisées dans utils.py) ---