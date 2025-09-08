import pandas as pd
import re
import streamlit as st
import json
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="BriefTool Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Gestion des briefs sauvegardés ---
def load_briefs():
    if os.path.exists("briefs.json"):
        with open("briefs.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_briefs():
    with open("briefs.json", "w", encoding="utf-8") as f:
        json.dump(st.session_state.saved_briefs, f, ensure_ascii=False, indent=4)

# Initialisation de l'état de session
if "saved_briefs" not in st.session_state:
    st.session_state.saved_briefs = load_briefs()

if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

if "poste_intitule" not in st.session_state:
    st.session_state.poste_intitule = ""

# --- Catégories (avec tes renoms) ---
CATEGORIES = [
    "Synonymes (Intitulés proches)",   # ancien "Intitulé du poste"
    "Mission globale",                  # NOUVELLE LIGNE
    "Tâches/Missions",
    "Connaissances/Diplômes/Certifs",
    "Compétences/Outils",
    "Case libre"
]
# NB: la ligne "Salaire proposé" a été SUPPRIMÉE comme demandé.

# --- Aide par ligne (lampe) ---
HELP_BRIEF = {
    "Synonymes (Intitulés proches)": {
        "mes_infos": "Intitulé officiel dans la demande interne + variantes internes.",
        "source": "Synonymes trouvés dans annonces/profils/fiches métiers (ex: Data Engineer / Ingénieur Data...)."
    },
    "Mission globale": {
        "mes_infos": "En 1 phrase: raison d'être du poste (but, valeur produite).",
        "source": "Formulations de mission vue dans annonces/fiches (ex: 'concevoir et fiabiliser la plateforme data')."
    },
    "Tâches/Missions": {
        "mes_infos": "Tâches listées dans la demande interne (jour/semaine/mois).",
        "source": "Actions concrètes récurrentes observées (verbes d'action, granularité opérationnelle)."
    },
    "Connaissances/Diplômes/Certifs": {
        "mes_infos": "Diplômes/certifications exigés en interne.",
        "source": "Diplômes/certifs fréquents sur le marché (APEC, Pôle Emploi, ONISEP/O*NET)."
    },
    "Compétences/Outils": {
        "mes_infos": "Compétences/outils impératifs côté interne.",
        "source": "Compétences/outils les plus fréquents (serviront au tri G1/G2/G3)."
    },
    "Case libre": {
        "mes_infos": "Contraintes, pics saisonniers, normes, infos utiles internes.",
        "source": "Points notables vus dans certaines sources (ex: périodes fortes Q4...)."
    },
}

# --- Heuristique optionnelle pour pré-classer G1/G2/G3 ---
def _tokenize(txt: str):
    return [t.strip().lower() for t in re.split(r"[,\n;/•\-–]+", (txt or "")) if t.strip()]

def suggest_groups_from_sources(df: pd.DataFrame, source_cols) -> dict:
    """
    Agrège 'Mes infos (Demande interne)' + colonnes sources.
    Règle: >=3 apparitions -> G1, 2 -> G2, 1 -> G3 (à titre indicatif).
    """
    sugg = {}
    for _, row in df.iterrows():
        bag = {}
        cols = ["Mes infos (Demande interne)"] + list(source_cols)
        for c in cols:
            for it in _tokenize(row.get(c)):
                bag[it] = bag.get(it, 0) + 1
        cat = row["Catégorie"]
        sugg[cat] = {it: ("G1 Incontournable" if f >= 3 else "G2 Fréquent" if f == 2 else "G3 Atout")
                     for it, f in bag.items()}
    return sugg

# --- État / init ---
def init_avant_brief_state_v4():
    st.session_state.setdefault("avant_brief_method", "🧠 Complète (1 h)")
    st.session_state.setdefault("source_cols", ["Source 1", "Source 2", "Source 3"])
    if "sources_df" not in st.session_state:
        data = {"Catégorie": CATEGORIES, "Mes infos (Demande interne)": [""] * len(CATEGORIES)}
        for s in st.session_state.source_cols:
            data[s] = [""] * len(CATEGORIES)
        data["Classement"] = [""] * len(CATEGORIES)
        st.session_state.sources_df = pd.DataFrame(data)
    # Aide (lampe) par ligne
    st.session_state.setdefault("help_open", {cat: False for cat in CATEGORIES})

def align_sources_df_columns_v4():
    """Assure: Catégorie + Mes infos + sources dynamiques + Classement; supprime les colonnes en trop."""
    df = st.session_state.sources_df.copy()
    base_cols = ["Catégorie", "Mes infos (Demande interne)"]
    desired = base_cols + list(st.session_state.source_cols) + ["Classement"]
    for col in desired:
        if col not in df.columns:
            df[col] = ""
    to_drop = [c for c in df.columns if (c not in desired)]
    if to_drop:
        df = df.drop(columns=to_drop)
    df = df[desired]
    # Garantir l'ordre des catégories
    if list(df["Catégorie"]) != CATEGORIES:
        df = pd.DataFrame({"Catégorie": CATEGORIES}).merge(
            df.set_index("Catégorie"), left_on="Catégorie", right_index=True, how="left"
        ).fillna("")
    st.session_state.sources_df = df

# --- UI gestion des colonnes Source ---
def manage_sources_ui_v4():
    st.markdown("#### ⚙️ Colonnes de **sources** (ajouter / supprimer / renommer)")
    # Ajouter
    if st.button("➕ Ajouter une source", key="btn_add_src"):
        base = "Source"
        idx = 1
        existing = set(st.session_state.source_cols)
        while f"{base} {idx}" in existing:
            idx += 1
        new_col = f"{base} {idx}"
        st.session_state.source_cols.append(new_col)
        st.session_state.sources_df[new_col] = ""
        st.experimental_rerun()

    # Renommer / Supprimer
    for i, s in enumerate(list(st.session_state.source_cols)):
        c1, c2 = st.columns([6,1])
        new_name = c1.text_input("Nom de la colonne", value=s, key=f"srcname_{i}")
        if new_name != s:
            if s in st.session_state.sources_df.columns:
                st.session_state.sources_df.rename(columns={s: new_name}, inplace=True)
            st.session_state.source_cols[i] = new_name
        if c2.button("🗑️", key=f"del_src_{i}"):
            if len(st.session_state.source_cols) > 1:
                if s in st.session_state.sources_df.columns:
                    st.session_state.sources_df.drop(columns=[s], inplace=True)
                st.session_state.source_cols.pop(i)
                st.experimental_rerun()
            else:
                st.warning("Au moins une colonne Source est requise.")

# --- UI aide par ligne (lampe) ---
def render_help_panel_v4():
    st.markdown("#### 💡 Aide par ligne (clique sur la lampe pour afficher/masquer)")
    for cat in CATEGORIES:
        if st.button(f"💡 {cat}", key=f"helpbtn_{cat}"):
            st.session_state.help_open[cat] = not st.session_state.help_open.get(cat, False)
        if st.session_state.help_open.get(cat, False):
            tips = HELP_BRIEF.get(cat, {})
            st.info(
                f"**Mes infos (Demande interne)** → {tips.get('mes_infos','')}  \n"
                f"**Source X** → {tips.get('source','')}"
            )

# --- Rendu principal ---
def render_avant_brief_complete_v4():
    init_avant_brief_state_v4()

    st.subheader(f"🧠 Avant‑brief — Méthode complète (1 h) — {st.session_state.get('poste_intitule','')}")
    st.caption("Remplis 3–5 sources puis classe en **G1/G2/G3** pour préparer le brief (LEDR).")

    with st.expander("⚙️ Colonnes de sources", expanded=True):
        manage_sources_ui_v4()

    with st.expander("💡 Aide rapide par ligne", expanded=True):
        render_help_panel_v4()

    align_sources_df_columns_v4()
    st.session_state.sources_df = st.data_editor(
        st.session_state.sources_df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Classement": st.column_config.SelectboxColumn(
                "Classement", options=["", "G1 Incontournable", "G2 Fréquent", "G3 Atout"]
            ),
            "Catégorie": st.column_config.TextColumn("Catégorie", disabled=True),
        },
        hide_index=True
    )

    # -------- Partie D : Contexte & options (avec Localisation, sans Impact stratégique) --------
    st.markdown("### 📌 Contexte & options (Partie D)")
    colA, colB = st.columns(2)
    with colA:
        st.text_area("Raison ouverture", key="raison_ouverture", height=80)
        st.text_area("Rattachement hiérarchique", key="rattachement", height=80)
        st.text_area("Défis principaux", key="defis_principaux", height=80)
        st.text_area("Entreprises où trouver ce profil", key="entreprises_profil", height=80)
    with colB:
        st.text_area("Canaux à utiliser", key="canaux_profil", height=80)
        st.text_input("Budget", key="budget")
        st.text_input("Localisation", key="localisation")  # <--- AJOUT
        st.number_input("Nombre d'années d'expérience", min_value=0, max_value=40, step=1, key="annees_experience")
        st.text_area("Commentaires libres", key="commentaires", height=80)

    # -------- Actions --------
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("💡 Pré-classer (G1/G2/G3)"):
            st.session_state.g_suggestions = suggest_groups_from_sources(
                st.session_state.sources_df, st.session_state.source_cols
            )
            st.success("Suggestions générées (révisables manuellement).")
    with c2:
        if st.button("💾 Sauvegarder Avant‑brief", type="primary"):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                name = st.session_state.current_brief_name
                st.session_state.saved_briefs[name].update({
                    "avant_brief_method": "🧠 Complète (1 h)",
                    "sources_df": st.session_state.sources_df.to_dict("records"),
                    "source_cols": st.session_state.source_cols,
                    "g_suggestions": st.session_state.get("g_suggestions", {}),
                    # Partie D (sans impact_strategique) + Localisation + Expérience
                    "raison_ouverture": st.session_state.get("raison_ouverture",""),
                    "rattachement": st.session_state.get("rattachement",""),
                    "defis_principaux": st.session_state.get("defis_principaux",""),
                    "entreprises_profil": st.session_state.get("entreprises_profil",""),
                    "canaux_profil": st.session_state.get("canaux_profil",""),
                    "budget": st.session_state.get("budget",""),
                    "localisation": st.session_state.get("localisation",""),               # <--- AJOUT
                    "annees_experience": st.session_state.get("annees_experience", 0),     # <--- CHAMP SÉPARÉ
                    "commentaires": st.session_state.get("commentaires",""),
                })
                save_briefs()  # <- ta fonction existante
                st.success("✅ Avant‑brief sauvegardé.")
            else:
                st.error("❌ Crée ou charge d'abord un brief dans l'onglet Gestion.")
    with c3:
        if st.session_state.get("g_suggestions"):
            st.info("Suggestions de tri disponibles (g_suggestions).")

# --- Interface principale ---
st.title("📋 BriefTool Pro")
st.markdown("Outil de préparation et gestion de briefs recrutement")

# Onglets
tab1, tab2, tab3 = st.tabs(["📁 Gestion des briefs", "🧠 Avant‑brief", "📊 Visualisation"])

with tab1:
    st.header("📁 Gestion des briefs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Créer un nouveau brief")
        new_brief_name = st.text_input("Nom du nouveau brief")
        if st.button("Créer le brief"):
            if new_brief_name:
                if new_brief_name in st.session_state.saved_briefs:
                    st.error("Un brief avec ce nom existe déjà")
                else:
                    st.session_state.saved_briefs[new_brief_name] = {
                        "created_at": datetime.now().isoformat(),
                        "poste_intitule": "",
                        "sources_df": [],
                        "source_cols": ["Source 1", "Source 2", "Source 3"],
                        "g_suggestions": {}
                    }
                    st.session_state.current_brief_name = new_brief_name
                    save_briefs()
                    st.success(f"Brief '{new_brief_name}' créé avec succès!")
                    st.rerun()
            else:
                st.error("Veuillez saisir un nom pour le brief")
    
    with col2:
        st.subheader("Charger un brief existant")
        if st.session_state.saved_briefs:
            brief_to_load = st.selectbox(
                "Sélectionner un brief",
                options=list(st.session_state.saved_briefs.keys()),
                index=0
            )
            if st.button("Charger le brief"):
                st.session_state.current_brief_name = brief_to_load
                brief_data = st.session_state.saved_briefs[brief_to_load]
                
                # Charger les données dans l'état de session
                if "sources_df" in brief_data and brief_data["sources_df"]:
                    st.session_state.sources_df = pd.DataFrame(brief_data["sources_df"])
                if "source_cols" in brief_data:
                    st.session_state.source_cols = brief_data["source_cols"]
                if "poste_intitule" in brief_data:
                    st.session_state.poste_intitule = brief_data["poste_intitule"]
                if "g_suggestions" in brief_data:
                    st.session_state.g_suggestions = brief_data["g_suggestions"]
                
                st.success(f"Brief '{brief_to_load}' chargé avec succès!")
                st.rerun()
        else:
            st.info("Aucun brief sauvegardé")
    
    st.subheader("Briefs sauvegardés")
    if st.session_state.saved_briefs:
        for brief_name, brief_data in st.session_state.saved_briefs.items():
            with st.expander(f"{brief_name} - Créé le {brief_data.get('created_at', 'N/A')}"):
                st.json(brief_data)
                if st.button(f"Supprimer {brief_name}", key=f"del_{brief_name}"):
                    del st.session_state.saved_briefs[brief_name]
                    if st.session_state.current_brief_name == brief_name:
                        st.session_state.current_brief_name = ""
                    save_briefs()
                    st.success(f"Brief '{brief_name}' supprimé")
                    st.rerun()
    else:
        st.info("Aucun brief sauvegardé pour le moment")

with tab2:
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.stop()
    
    # Champ pour l'intitulé du poste
    st.session_state.poste_intitule = st.text_input(
        "Intitulé du poste à briefER",
        value=st.session_state.get("poste_intitule", ""),
        placeholder="ex: Data Analyst, Développeur Fullstack..."
    )
    
    render_avant_brief_complete_v4()

with tab3:
    st.header("📊 Visualisation des données")
    st.info("Fonctionnalité en cours de développement")
    
    if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
        st.subheader(f"Données du brief: {st.session_state.current_brief_name}")
        
        if "sources_df" in st.session_state:
            st.dataframe(st.session_state.sources_df, use_container_width=True)
        
        if st.session_state.get("g_suggestions"):
            st.subheader("Suggestions de classement")
            st.json(st.session_state.g_suggestions)
    else:
        st.warning("Veuillez d'abord créer ou charger un brief")