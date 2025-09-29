import streamlit as st
import sys, os
from datetime import datetime
import json
import pandas as pd
from datetime import date

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

# --- DEBUG démarrage (ajouter juste après les imports existants) ---
st.write("DEBUG: script démarré à", datetime.utcnow().isoformat())

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
    
    # Cette ligne appelle la fonction pour charger toutes les données de la feuille, 
    # puis len() compte le nombre total de briefs.
    total_briefs = len(load_briefs())
    
    # Cette ligne affiche le total que vous avez calculé.
    st.metric("📋 Briefs créés", total_briefs)

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
            date_brief_raw = brief_data.get("date_brief", st.session_state.get("date_brief", date.today()))  # correction : valeur par défaut correcte

            # Correction : on force la valeur dans session_state à être du bon type
            if "date_brief" in st.session_state and not isinstance(st.session_state["date_brief"], date):
                try:
                    st.session_state["date_brief"] = datetime.strptime(str(st.session_state["date_brief"]), "%Y-%m-%d").date()
                except Exception:
                    try:
                        st.session_state["date_brief"] = datetime.strptime(str(st.session_state["date_brief"]), "%d/%m/%Y").date()
                    except Exception:
                        st.session_state["date_brief"] = date.today()

            # Conversion de la valeur à afficher
            if isinstance(date_brief_raw, str):
                try:
                    date_brief_value = datetime.strptime(date_brief_raw, "%Y-%m-%d").date()
                except Exception:
                    try:
                        date_brief_value = datetime.strptime(date_brief_raw, "%d/%m/%Y").date()
                    except Exception:
                        date_brief_value = date.today()
            elif isinstance(date_brief_raw, datetime):
                date_brief_value = date_brief_raw.date()
            elif isinstance(date_brief_raw, date):
                date_brief_value = date_brief_raw
            else:
                date_brief_value = date.today()
            st.date_input("Date du brief", key="date_brief", value=date_brief_value)

        if st.button("💾 Créer brief", type="primary", use_container_width=True, key="create_brief"):
            required_fields = ["poste_intitule", "manager_nom", "affectation_nom", "date_brief"]
            missing_fields = [field for field in required_fields if not st.session_state.get(field)]
            if missing_fields:
                st.error(f"Veuillez remplir les champs suivants : {', '.join(missing_fields)}")
            else:
                # Nom automatique (ajout date si signature attend 3 params)
                try:
                    new_brief_name = generate_automatic_brief_name(
                        st.session_state.poste_intitule,
                        st.session_state.manager_nom,
                        st.session_state.date_brief
                    )
                except TypeError:
                    new_brief_name = generate_automatic_brief_name(
                        st.session_state.poste_intitule,
                        st.session_state.manager_nom
                    )
                st.session_state.current_brief_name = new_brief_name

                new_brief_data = {}
                # Champs de base (lower + upper)
                base_pairs = {
                    "poste_intitule": "POSTE_INTITULE",
                    "manager_nom": "MANAGER_NOM",
                    "recruteur": "RECRUTEUR",
                    "affectation_type": "AFFECTATION_TYPE",
                    "affectation_nom": "AFFECTATION_NOM",
                    "date_brief": "DATE_BRIEF"
                }
                for low, up in base_pairs.items():
                    v = st.session_state.get(low, "")
                    new_brief_data[low] = v
                    new_brief_data[up] = v
                # Champs Avant-brief
                for k in all_field_keys:
                    v = st.session_state.get(k, "")
                    # Stockage lower
                    new_brief_data[k] = v
                    # Stockage upper normal
                    if k.startswith("profil_link_"):
                        # Mapper vers LIEN_PROFIL_X
                        suffix = k.split("_")[-1]
                        new_brief_data[f"LIEN_PROFIL_{suffix}"] = v
                    else:
                        new_brief_data[k.upper()] = v

                st.session_state.saved_briefs[new_brief_name] = new_brief_data
                save_briefs()

                # Payload Google Sheets (upper déjà prêts)
                save_brief_to_gsheet(new_brief_name, new_brief_data)

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

# ---------------- REUNION BRIEF (WIZARD) ----------------
with tabs[2]:
    st.markdown("""
        <style>
            .stTextArea > div > label > div {
                color: #A9A9A9;
            }
            .stTextArea > div > div > textarea {
                background-color: #2F333B;
                color: white;
                border-color: #555555;
            }
            .stTextInput > div > div > input {
                background-color: #2F333B;
                color: white;
                border-color: #555555;
            }
            div[data-testid="stForm"] {
                padding: 1rem;
                border: 1px solid #555555;
                border-radius: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialisation
    if "reunion_step" not in st.session_state:
        st.session_state.reunion_step = 1
    
    step = st.session_state.reunion_step
    total_steps = 4

    # Vérification brief existant
    if not st.session_state.current_brief_name:
        st.warning("Veuillez créer ou sélectionner un brief dans l'onglet Gestion.")
    else:
        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
        
        # Affichage en-tête et progression
        brief_display_name = f"Réunion de brief - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
        st.markdown(f"<h3 style='color: #FFFFFF;'>{brief_display_name}</h3>", unsafe_allow_html=True)
        st.progress(int((step / total_steps) * 100), text=f"**Étape {step} sur {total_steps}**")

        # ==================== ÉTAPE 1 : VALIDATION BRIEF ====================
        if step == 1:
            st.subheader("Étape 1 : Validation du brief et commentaires du manager")
            
            with st.expander("Portrait robot du candidat - Validation", expanded=True):
                # Récupération commentaires manager
                manager_comments_json = brief_data.get("MANAGER_COMMENTS_JSON", "{}")
                try:
                    manager_comments = json.loads(manager_comments_json) if manager_comments_json else {}
                except:
                    manager_comments = {}

                # Construction tableau
                table_data = []
                for section in sections:
                    if section["title"] == "Profils pertinents":
                        continue
                    for title, key, _ in section["fields"]:
                        info_value = brief_data.get(key.upper(), brief_data.get(key, ""))
                        table_data.append({
                            "Section": section["title"],
                            "Détails": title,
                            "Informations": info_value,
                            "Commentaires du manager": manager_comments.get(key, ""),
                            "_key": key
                        })
                
                if not table_data:
                    st.warning("Veuillez d'abord remplir l'onglet 'Avant-brief'.")
                else:
                    df = pd.DataFrame(table_data)
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Section": st.column_config.TextColumn(disabled=True),
                            "Détails": st.column_config.TextColumn(disabled=True),
                            "Informations": st.column_config.TextColumn(disabled=True, width="large"),
                            "Commentaires du manager": st.column_config.TextColumn(width="large"),
                            "_key": None,
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="manager_comments_editor"
                    )

                    if st.button("Enregistrer les commentaires", type="primary"):
                        comments_to_save = {
                            row["_key"]: row["Commentaires du manager"]
                            for _, row in edited_df.iterrows()
                            if row["Commentaires du manager"]
                        }
                        st.session_state.saved_briefs[st.session_state.current_brief_name]["manager_comments"] = comments_to_save
                        save_briefs()

                        payload_for_gsheet = st.session_state.saved_briefs[st.session_state.current_brief_name].copy()
                        payload_for_gsheet['MANAGER_COMMENTS_JSON'] = json.dumps(comments_to_save, indent=4, ensure_ascii=False)
                        
                        mapping = {
                            "poste_intitule": "POSTE_INTITULE", "manager_nom": "MANAGER_NOM", "recruteur": "RECRUTEUR",
                            "affectation_type": "AFFECTATION_TYPE", "affectation_nom": "AFFECTATION_NOM", "date_brief": "DATE_BRIEF",
                            "raison_ouverture": "RAISON_OUVERTURE", "impact_strategique": "IMPACT_STRATEGIQUE",
                            "rattachement": "RATTACHEMENT", "taches_principales": "TACHES_PRINCIPALES",
                            "must_have_experience": "MUST_HAVE_EXP", "must_have_diplomes": "MUST_HAVE_DIP",
                            "must_have_competences": "MUST_HAVE_COMPETENCES", "must_have_softskills": "MUST_HAVE_SOFTSKILLS",
                            "nice_to_have_experience": "NICE_TO_HAVE_EXP", "nice_to_have_diplomes": "NICE_TO_HAVE_DIP",
                            "nice_to_have_competences": "NICE_TO_HAVE_COMPETENCES",
                            "entreprises_profil": "ENTREPRISES_PROFIL", "synonymes_poste": "SYNONYMES_POSTE",
                            "canaux_profil": "CANAUX_PROFIL", "budget": "BUDGET", "commentaires": "COMMENTAIRES",
                            "notes_libres": "NOTES_LIBRES",
                            "profil_link_1": "LIEN_PROFIL_1", "profil_link_2": "LIEN_PROFIL_2", "profil_link_3": "LIEN_PROFIL_3"
                        }
                        for session_key, gsheet_key in mapping.items():
                            if session_key in payload_for_gsheet:
                                payload_for_gsheet[gsheet_key] = payload_for_gsheet[session_key]

                        if "ksa_matrix" in payload_for_gsheet and isinstance(payload_for_gsheet["ksa_matrix"], pd.DataFrame) and not payload_for_gsheet["ksa_matrix"].empty:
                            payload_for_gsheet['KSA_MATRIX_JSON'] = payload_for_gsheet["ksa_matrix"].to_csv(index=False, sep=";", encoding="utf-8")
                        
                        save_brief_to_gsheet(st.session_state.current_brief_name, payload_for_gsheet)
                        st.success("Commentaires sauvegardés et synchronisés avec Google Sheets")
                        st.rerun()

        # ==================== ÉTAPE 2 : MATRICE KSA ====================
        elif step == 2:
            st.subheader("Étape 2 : Matrice KSA")
            
            with st.expander("Explications de la méthode KSA", expanded=False):
                st.markdown("""
                    ### Méthode KSA (Knowledge, Skills, Abilities)
                    La méthode KSA permet de décomposer un poste en trois catégories de compétences pour une évaluation plus précise.
                    
                    **Knowledge (Connaissances)** : Connaissances des protocoles de sécurité IT (ISO 27001), maîtrise des concepts de comptabilité analytique.
                    
                    **Skills (Compétences)** : Capacité à utiliser Adobe Photoshop, expertise en négociation commerciale, maîtrise de la gestion de projet Agile.
                    
                    **Abilities (Aptitudes)** : Capacité à gérer le stress, aptitude à communiquer clairement des idées complexes, capacité à travailler en équipe.
                """)

            with st.expander("Ajouter un critère", expanded=True):
                with st.form(key="add_criteria_form"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
                    with col2:
                        critere = st.text_input("Critère", placeholder="Ex: Leadership", key="new_critere")
                    with col3:
                        type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], key="new_type_question")
                    with col4:
                        evaluateur = st.selectbox("Évaluateur", ["Recruteur", "Manager", "Les deux"], key="new_evaluateur")

                    col_q_text, col_slider = st.columns([2, 1])
                    
                    with col_q_text:
                        question = st.text_input("Question pour l'entretien", 
                                               placeholder="Ex: Parlez-moi d'une situation où vous avez dû faire preuve de leadership.", 
                                               key="new_question")
                    with col_slider:
                        evaluation = st.slider("Évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                    
                    ai_prompt = st.text_input("Décrivez ce que l'IA doit générer comme Question", 
                                            placeholder="Ex: Donne-moi une question pour évaluer la gestion de projets", 
                                            key="ai_prompt_input")
                    concise_mode = st.checkbox("Mode rapide (réponse concise)", key="concise_mode")
                    
                    st.markdown("---")
                    
                    col_ai, col_add = st.columns(2)
                    with col_ai:
                        if st.form_submit_button("Générer question IA", type="primary", use_container_width=True):
                            if ai_prompt:
                                with st.spinner("Génération en cours..."):
                                    try:
                                        ai_response = generate_ai_question(ai_prompt, concise=concise_mode)
                                        if ai_response.strip().startswith("Question:"):
                                            ai_response = ai_response.strip().replace("Question:", "", 1).strip()
                                        st.session_state.ai_generated_question = ai_response
                                    except Exception as e:
                                        st.error(f"Erreur lors de la génération : {e}")
                            else:
                                st.error("Veuillez entrer un prompt pour l'IA.")
                    
                    with col_add:
                        if st.form_submit_button("Ajouter le critère", type="secondary", use_container_width=True):
                            if not st.session_state.new_critere or not question:
                                st.error("Veuillez remplir au moins le critère et la question.")
                            else:
                                new_row = pd.DataFrame([{
                                    "Rubrique": rubrique,
                                    "Critère": critere,
                                    "Type de question": type_question,
                                    "Question pour l'entretien": question,
                                    "Évaluation (1-5)": evaluation,
                                    "Évaluateur": evaluateur
                                }])
                                if "ksa_matrix" not in st.session_state:
                                    st.session_state.ksa_matrix = pd.DataFrame(columns=[
                                        "Rubrique", "Critère", "Type de question", "Question pour l'entretien",
                                        "Évaluation (1-5)", "Évaluateur"
                                    ])
                                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, new_row], ignore_index=True)
                                st.success("Critère ajouté avec succès")
                                st.rerun()

                if "ai_generated_question" in st.session_state and st.session_state.ai_generated_question:
                    st.success(f"**Question :** {st.session_state.ai_generated_question}")
                    st.session_state.ai_generated_question = ""
            
            if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
                st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
                
                avg_rating = st.session_state.ksa_matrix["Évaluation (1-5)"].mean()
                st.markdown(f"**Note cible moyenne : {avg_rating:.2f} / 5**")

        # ==================== ÉTAPE 3 : STRATÉGIE ====================
        elif step == 3:
            st.subheader("Étape 3 : Stratégie et Processus")
            
            with st.expander("Stratégie et Processus", expanded=True):
                st.info("Définissez les canaux de sourcing et les critères d'évaluation.")
                
                canaux_prioritaires = st.multiselect(
                    "Canaux prioritaires",
                    ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"],
                    default=brief_data.get("canaux_prioritaires", []),
                    key="canaux_prioritaires"
                )
                
                st.markdown("---")
                st.subheader("Critères d'exclusion et Processus d'évaluation")
                col1, col2 = st.columns(2)
                with col1:
                    criteres_exclusion = st.text_area(
                        "Critères d'exclusion",
                        height=150,
                        placeholder="Ex: ne pas avoir d'expérience dans le secteur public...",
                        value=brief_data.get("criteres_exclusion", ""),
                        key="criteres_exclusion"
                    )
                with col2:
                    processus_evaluation = st.text_area(
                        "Processus d'évaluation (détails)",
                        height=150,
                        placeholder="Ex: Entretien RH (30min), Test technique, Entretien manager (60min)...",
                        value=brief_data.get("processus_evaluation", ""),
                        key="processus_evaluation"
                    )
                
                if st.button("Sauvegarder l'étape 3", type="primary"):
                    brief_data["canaux_prioritaires"] = canaux_prioritaires
                    brief_data["criteres_exclusion"] = criteres_exclusion
                    brief_data["processus_evaluation"] = processus_evaluation
                    st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    st.success("Étape 3 sauvegardée")

        # ==================== ÉTAPE 4 : FINALISATION ====================
        elif step == 4:
            st.subheader("Étape 4 : Finalisation")
            
            with st.form(key="reunion_final_form"):
                with st.expander("Notes générales du manager", expanded=True):
                    manager_notes = st.text_area(
                        "Notes et commentaires généraux du manager",
                        height=250,
                        value=brief_data.get("manager_notes", ""),
                        key="manager_notes"
                    )
                    
                    criteres_exclusion = st.text_area(
                        "Critères d'exclusion",
                        height=150,
                        placeholder="Ex: ne pas avoir d'expérience dans le secteur public...",
                        value=brief_data.get("criteres_exclusion", ""),
                        key="criteres_exclusion_final"
                    )
                    
                    processus_evaluation = st.text_area(
                        "Processus d'évaluation (détails)",
                        height=150,
                        placeholder="Ex: Entretien RH (30min), Test technique, Entretien manager (60min)...",
                        value=brief_data.get("processus_evaluation", ""),
                        key="processus_evaluation_final"
                    )

                st.markdown("---")
                
                if st.form_submit_button("Enregistrer la réunion", type="primary", use_container_width=True):
                    if st.session_state.current_brief_name:
                        brief_data_to_save = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {}).copy()
                        
                        brief_data_to_save.update({
                            "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                            "criteres_exclusion": criteres_exclusion,
                            "processus_evaluation": processus_evaluation,
                            "manager_notes": manager_notes
                        })
                        
                        ksa_matrix_df = st.session_state.get("ksa_matrix", pd.DataFrame())
                        brief_data_to_save["ksa_matrix"] = ksa_matrix_df
                        manager_comments_dict = brief_data_to_save.get("manager_comments", {})
                        
                        st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data_to_save
                        save_briefs()
                        
                        payload_for_gsheet = brief_data_to_save.copy()
                        if not ksa_matrix_df.empty:
                            payload_for_gsheet['KSA_MATRIX_JSON'] = ksa_matrix_df.to_csv(index=False, sep=";", encoding="utf-8")
                        if manager_comments_dict:
                            payload_for_gsheet['MANAGER_COMMENTS_JSON'] = json.dumps(manager_comments_dict, indent=4, ensure_ascii=False)
                        
                        mapping = {
                            "poste_intitule": "POSTE_INTITULE", "manager_nom": "MANAGER_NOM", "recruteur": "RECRUTEUR",
                            "affectation_type": "AFFECTATION_TYPE", "affectation_nom": "AFFECTATION_NOM", "date_brief": "DATE_BRIEF",
                            "raison_ouverture": "RAISON_OUVERTURE", "impact_strategique": "IMPACT_STRATEGIQUE",
                            "rattachement": "RATTACHEMENT", "taches_principales": "TACHES_PRINCIPALES",
                            "must_have_experience": "MUST_HAVE_EXP", "must_have_diplomes": "MUST_HAVE_DIP",
                            "must_have_competences": "MUST_HAVE_COMPETENCES", "must_have_softskills": "MUST_HAVE_SOFTSKILLS",
                            "nice_to_have_experience": "NICE_TO_HAVE_EXP", "nice_to_have_diplomes": "NICE_TO_HAVE_DIP",
                            "nice_to_have_competences": "NICE_TO_HAVE_COMPETENCES",
                            "entreprises_profil": "ENTREPRISES_PROFIL", "synonymes_poste": "SYNONYMES_POSTE",
                            "canaux_profil": "CANAUX_PROFIL", "budget": "BUDGET", "commentaires": "COMMENTAIRES",
                            "notes_libres": "NOTES_LIBRES",
                            "profil_link_1": "LIEN_PROFIL_1", "profil_link_2": "LIEN_PROFIL_2", "profil_link_3": "LIEN_PROFIL_3",
                            "canaux_prioritaires": "CANAUX_PRIORITAIRES",
                            "criteres_exclusion": "CRITERES_EXCLUSION",
                            "processus_evaluation": "PROCESSUS_EVALUATION",
                            "manager_notes": "MANAGER_NOTES"
                        }
                        for session_key, gsheet_key in mapping.items():
                            if session_key in payload_for_gsheet:
                                value = payload_for_gsheet[session_key]
                                if isinstance(value, (list, dict)):
                                    payload_for_gsheet[gsheet_key] = json.dumps(value, indent=4, ensure_ascii=False)
                                else:
                                    payload_for_gsheet[gsheet_key] = value
                        
                        save_brief_to_gsheet(st.session_state.current_brief_name, payload_for_gsheet)
                        
                        st.session_state.reunion_completed = True
                        st.success("Données de réunion sauvegardées et synchronisées avec succès")
                        st.rerun()
                    else:
                        st.error("Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

        # ==================== NAVIGATION ====================
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 6, 1])
        
        with col1:
            if step > 1:
                if st.button("Précédent", key="prev_step", use_container_width=True):
                    st.session_state.reunion_step -= 1
                    st.rerun()
        
        with col3:
            if step < total_steps:
                if st.button("Suivant", key="next_step", use_container_width=True):
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
                    pdf_buf = export_brief_pdf()
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