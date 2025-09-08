import pandas as pd
import re
import streamlit as st
import json
import os
from datetime import datetime
import base64
from io import BytesIO

# Configuration de la page
st.set_page_config(
    page_title="BriefTool Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Fonctions utilitaires ---
def load_briefs():
    if os.path.exists("briefs.json"):
        try:
            with open("briefs.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_briefs():
    with open("briefs.json", "w", encoding="utf-8") as f:
        json.dump(st.session_state.saved_briefs, f, ensure_ascii=False, indent=4)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Brief')
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, filename):
    val = to_excel(df)
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.xlsx">Télécharger le brief Excel</a>'

# --- Initialisation de l'état de session ---
if "saved_briefs" not in st.session_state:
    st.session_state.saved_briefs = load_briefs()

if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

if "poste_intitule" not in st.session_state:
    st.session_state.poste_intitule = ""

if "current_wizard_step" not in st.session_state:
    st.session_state.current_wizard_step = 1

if "reunion_brief_status" not in st.session_state:
    st.session_state.reunion_brief_status = None

# --- Catégories et aide ---
CATEGORIES = [
    "Synonymes (Intitulés proches)",
    "Mission globale",
    "Tâches/Missions",
    "Connaissances/Diplômes/Certifs",
    "Compétences/Outils",
    "Case libre"
]

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

# --- Fonctions pour l'avant-brief ---
def _tokenize(txt: str):
    return [t.strip().lower() for t in re.split(r"[,\n;/•\-–]+", (txt or "")) if t.strip()]

def suggest_groups_from_sources(df: pd.DataFrame, source_cols) -> dict:
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

def init_avant_brief_state_v4():
    st.session_state.setdefault("avant_brief_method", "🧠 Complète (1 h)")
    st.session_state.setdefault("source_cols", ["Source 1", "Source 2", "Source 3"])
    if "sources_df" not in st.session_state:
        data = {"Catégorie": CATEGORIES, "Mes infos (Demande interne)": [""] * len(CATEGORIES)}
        for s in st.session_state.source_cols:
            data[s] = [""] * len(CATEGORIES)
        data["Classement"] = [""] * len(CATEGORIES)
        st.session_state.sources_df = pd.DataFrame(data)
    st.session_state.setdefault("help_open", {cat: False for cat in CATEGORIES})

def align_sources_df_columns_v4():
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
    if list(df["Catégorie"]) != CATEGORIES:
        df = pd.DataFrame({"Catégorie": CATEGORIES}).merge(
            df.set_index("Catégorie"), left_on="Catégorie", right_index=True, how="left"
        ).fillna("")
    st.session_state.sources_df = df

def manage_sources_ui_v4():
    st.markdown("#### ⚙️ Colonnes de **sources** (ajouter / supprimer / renommer)")
    if st.button("➕ Ajouter une source", key="btn_add_src"):
        base = "Source"
        idx = 1
        existing = set(st.session_state.source_cols)
        while f"{base} {idx}" in existing:
            idx += 1
        new_col = f"{base} {idx}"
        st.session_state.source_cols.append(new_col)
        st.session_state.sources_df[new_col] = ""
        st.rerun()

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
                st.rerun()
            else:
                st.warning("Au moins une colonne Source est requise.")

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

# --- Fonctions pour les différents onglets ---
def render_gestion_onglet():
    st.header("📁 Gestion des briefs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Créer un nouveau brief")
        new_brief_name = st.text_input("Nom du nouveau brief", key="new_brief_name")
        if st.button("Créer le brief", key="create_brief_btn"):
            if new_brief_name:
                if new_brief_name in st.session_state.saved_briefs:
                    st.error("Un brief avec ce nom existe déjà")
                else:
                    st.session_state.saved_briefs[new_brief_name] = {
                        "created_at": datetime.now().isoformat(),
                        "poste_intitule": "",
                        "sources_df": pd.DataFrame({
                            "Catégorie": CATEGORIES,
                            "Mes infos (Demande interne)": [""] * len(CATEGORIES),
                            "Source 1": [""] * len(CATEGORIES),
                            "Source 2": [""] * len(CATEGORIES),
                            "Source 3": [""] * len(CATEGORIES),
                            "Classement": [""] * len(CATEGORIES)
                        }).to_dict("records"),
                        "source_cols": ["Source 1", "Source 2", "Source 3"],
                        "g_suggestions": {},
                        "liens_profils": "",
                        "commentaire_libre": "",
                        "points_a_discuter": "",
                        "raison_ouverture": "",
                        "rattachement": "",
                        "defis_principaux": "",
                        "entreprises_profil": "",
                        "canaux_profil": "",
                        "budget": "",
                        "localisation": "",
                        "annees_experience": 0,
                        "commentaires": ""
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
                index=0,
                key="load_brief_select"
            )
            if st.button("Charger le brief", key="load_brief_btn"):
                st.session_state.current_brief_name = brief_to_load
                brief_data = st.session_state.saved_briefs[brief_to_load]
                
                # Charger toutes les données
                for key, value in brief_data.items():
                    if key == "sources_df" and value:
                        st.session_state.sources_df = pd.DataFrame(value)
                    elif key == "source_cols":
                        st.session_state.source_cols = value
                    else:
                        st.session_state[key] = value
                
                st.success(f"Brief '{brief_to_load}' chargé avec succès!")
                st.rerun()
        else:
            st.info("Aucun brief sauvegardé")
    
    st.subheader("Briefs sauvegardés")
    if st.session_state.saved_briefs:
        for brief_name, brief_data in st.session_state.saved_briefs.items():
            with st.expander(f"{brief_name} - Créé le {brief_data.get('created_at', 'N/A')}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.json(brief_data)
                with col2:
                    if st.button(f"Supprimer {brief_name}", key=f"del_{brief_name}"):
                        del st.session_state.saved_briefs[brief_name]
                        if st.session_state.current_brief_name == brief_name:
                            st.session_state.current_brief_name = ""
                        save_briefs()
                        st.success(f"Brief '{brief_name}' supprimé")
                        st.rerun()
    else:
        st.info("Aucun brief sauvegardé pour le moment")

def render_avant_brief_onglet():
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.stop()
    
    init_avant_brief_state_v4()
    
    st.subheader(f"🧠 Avant‑brief — Méthode complète (1 h) — {st.session_state.get('poste_intitule','')}")
    st.caption("Remplis 3–5 sources puis classe en **G1/G2/G3** pour préparer le brief (LEDR).")

    # Champ pour l'intitulé du poste
    st.session_state.poste_intitule = st.text_input(
        "Intitulé du poste à briefER",
        value=st.session_state.get("poste_intitule", ""),
        placeholder="ex: Data Analyst, Développeur Fullstack..."
    )

    with st.expander("⚙️ Colonnes de sources", expanded=False):
        manage_sources_ui_v4()

    with st.expander("💡 Aide rapide par ligne", expanded=False):
        render_help_panel_v4()

    align_sources_df_columns_v4()
    
    # Configuration des colonnes pour permettre le retour à la ligne
    column_config = {
        "Classement": st.column_config.SelectboxColumn(
            "Classement", 
            options=["", "G1 Incontournable", "G2 Fréquent", "G3 Atout"],
            width="small"
        ),
        "Catégorie": st.column_config.TextColumn("Catégorie", disabled=True, width="medium"),
    }
    
    # Configuration pour permettre le retour à la ligne dans les autres colonnes
    for col in st.session_state.sources_df.columns:
        if col not in ["Classement", "Catégorie"]:
            column_config[col] = st.column_config.TextColumn(
                col, 
                width="large",
                validate=r"^.*$"  # Permet les retours à ligne
            )
    
    edited_df = st.data_editor(
        st.session_state.sources_df,
        num_rows="fixed",
        use_container_width=True,
        column_config=column_config,
        hide_index=True
    )
    
    st.session_state.sources_df = edited_df

    # -------- Cases supplémentaires en bas du tableau --------
    st.markdown("### 🔗 Profils pertinents et commentaires")
    
    st.text_area("Lien de profils pertinents", 
                 value=st.session_state.get("liens_profils", ""),
                 key="liens_profils",
                 height=100, 
                 placeholder="Coller ici les liens vers des profils intéressants...")
    
    st.text_area("Espace commentaire libre", 
                 value=st.session_state.get("commentaire_libre", ""),
                 key="commentaire_libre",
                 height=100, 
                 placeholder="Notes, observations, remarques...")
    
    st.text_area("Points à discuter ou à clarifier avec le manager", 
                 value=st.session_state.get("points_a_discuter", ""),
                 key="points_a_discuter",
                 height=100, 
                 placeholder="Liste des points à aborder avec le manager...")

    # -------- Partie Contexte & options --------
    st.markdown("### 📌 Contexte & options")
    colA, colB = st.columns(2)
    with colA:
        st.text_area("Raison ouverture", 
                     value=st.session_state.get("raison_ouverture", ""),
                     key="raison_ouverture", 
                     height=80,
                     placeholder="Remplacer / Création / Évolution interne...")
        st.text_area("Rattachement hiérarchique", 
                     value=st.session_state.get("rattachement", ""),
                     key="rattachement", 
                     height=80,
                     placeholder="Responsable direct, département / service...")
        st.text_area("Défis principaux", 
                     value=st.session_state.get("defis_principaux", ""),
                     key="defis_principaux", 
                     height=80,
                     placeholder="Ex: gestion de projet complexe, coordination multi-sites...")
        st.text_area("Entreprises où trouver ce profil", 
                     value=st.session_state.get("entreprises_profil", ""),
                     key="entreprises_profil", 
                     height=80,
                     placeholder="Concurrents, secteurs similaires...")
    with colB:
        st.text_area("Canaux à utiliser", 
                     value=st.session_state.get("canaux_profil", ""),
                     key="canaux_profil", 
                     height=80,
                     placeholder="LinkedIn, jobboards, cabinet, cooptation...")
        st.text_input("Budget", 
                      value=st.session_state.get("budget", ""),
                      key="budget",
                      placeholder="Salaire indicatif, avantages, primes...")
        st.text_input("Localisation", 
                      value=st.session_state.get("localisation", ""),
                      key="localisation",
                      placeholder="Site principal, télétravail, déplacements...")
        st.number_input("Nombre d'années d'expérience", 
                        value=st.session_state.get("annees_experience", 0),
                        min_value=0, max_value=40, step=1, key="annees_experience")
        st.text_area("Commentaires libres", 
                     value=st.session_state.get("commentaires", ""),
                     key="commentaires", 
                     height=80,
                     placeholder="Autres informations importantes...")

    # -------- Actions --------
    c1, c2, c3, c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("💡 Pré-classer (G1/G2/G3)", key="preclasser_btn"):
            st.session_state.g_suggestions = suggest_groups_from_sources(
                st.session_state.sources_df, st.session_state.source_cols
            )
            st.success("Suggestions générées (révisables manuellement).")
    with c2:
        if st.button("💾 Sauvegarder", key="save_btn"):
            if st.session_state.current_brief_name in st.session_state.saved_briefs:
                name = st.session_state.current_brief_name
                st.session_state.saved_briefs[name].update({
                    "poste_intitule": st.session_state.poste_intitule,
                    "sources_df": st.session_state.sources_df.to_dict("records"),
                    "source_cols": st.session_state.source_cols,
                    "g_suggestions": st.session_state.get("g_suggestions", {}),
                    "liens_profils": st.session_state.get("liens_profils", ""),
                    "commentaire_libre": st.session_state.get("commentaire_libre", ""),
                    "points_a_discuter": st.session_state.get("points_a_discuter", ""),
                    "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                    "rattachement": st.session_state.get("rattachement", ""),
                    "defis_principaux": st.session_state.get("defis_principaux", ""),
                    "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                    "canaux_profil": st.session_state.get("canaux_profil", ""),
                    "budget": st.session_state.get("budget", ""),
                    "localisation": st.session_state.get("localisation", ""),
                    "annees_experience": st.session_state.get("annees_experience", 0),
                    "commentaires": st.session_state.get("commentaires", ""),
                })
                save_briefs()
                st.success("✅ Avant‑brief sauvegardé.")
            else:
                st.error("❌ Brief non trouvé. Créez d'abord un brief.")
    with c3:
        if st.button("📋 Exporter Excel", key="export_btn"):
            if st.session_state.current_brief_name:
                # Créer un DataFrame complet pour l'export
                export_data = []
                for _, row in st.session_state.sources_df.iterrows():
                    export_data.append({
                        "Catégorie": row["Catégorie"],
                        "Mes infos (Demande interne)": row["Mes infos (Demande interne)"],
                        **{col: row[col] for col in st.session_state.source_cols},
                        "Classement": row["Classement"]
                    })
                
                export_df = pd.DataFrame(export_data)
                st.markdown(get_table_download_link(export_df, st.session_state.current_brief_name), unsafe_allow_html=True)
            else:
                st.error("❌ Aucun brief à exporter")
    with c4:
        if st.session_state.get("g_suggestions"):
            st.info("Suggestions de tri disponibles")

def render_reunion_brief_onglet():
    st.header("🤝 Réunion de brief")
    
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("Veuillez d'abord créer ou charger un brief")
        return
    
    st.subheader("Tableau de validation avec le manager")
    
    # Données par défaut pour la réunion
    if st.session_state.reunion_brief_status is None:
        reunion_data = {
            "Point à valider": [
                "1️⃣ Contexte du poste",
                "1.1 Raison de l'ouverture",
                "1.2 Mission globale",
                "1.3 Défis principaux",
                "2️⃣ Organisation et hiérarchie",
                "2.1 Rattachement hiérarchique",
                "2.2 Équipe",
                "3️⃣ Profil recherché",
                "3.1 Expérience",
                "3.2 Connaissances / Diplômes / Certifications",
                "3.3 Compétences / Outils",
                "3.4 Soft skills / aptitudes comportementales",
                "4️⃣ Sourcing et marché",
                "4.1 Entreprises où trouver ce profil",
                "4.2 Synonymes / intitulés proches",
                "4.3 Canaux à utiliser",
                "5️⃣ Conditions et contraintes",
                "5.1 Localisation",
                "5.2 Budget recrutement",
                "6️⃣ Missions / Tâches",
                "6.1 Tâches principales",
                "6.2 Autres responsabilités"
            ],
            "Statut": ["À valider"] * 21,
            "Commentaires": [""] * 21
        }
        st.session_state.reunion_brief_status = pd.DataFrame(reunion_data)
    
    # Éditeur de données avec sélection de statut
    edited_df = st.data_editor(
        st.session_state.reunion_brief_status,
        column_config={
            "Statut": st.column_config.SelectboxColumn(
                "Statut",
                options=["À valider", "Validé", "À modifier", "Reporté"],
                width="medium"
            ),
            "Commentaires": st.column_config.TextColumn(
                "Commentaires",
                width="large"
            ),
            "Point à valider": st.column_config.TextColumn(
                "Point à valider",
                width="large",
                disabled=True
            )
        },
        use_container_width=True,
        hide_index=True,
        key="reunion_editor"
    )
    
    st.session_state.reunion_brief_status = edited_df
    
    # Boutons d'action
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Sauvegarder l'état", key="save_reunion_btn"):
            if st.session_state.current_brief_name in st.session_state.saved_briefs:
                st.session_state.saved_briefs[st.session_state.current_brief_name]["reunion_status"] = st.session_state.reunion_brief_status.to_dict("records")
                save_briefs()
                st.success("État de validation sauvegardé")
    
    with col2:
        if st.button("📊 Générer le compte-rendu", key="generate_report_btn"):
            st.info("Fonctionnalité en cours de développement")
    
    with col3:
        if st.button("🔄 Réinitialiser", key="reset_reunion_btn"):
            st.session_state.reunion_brief_status = None
            st.rerun()
    
    with col4:
        if st.button("➡️ Passer à la synthèse", key="next_step_btn"):
            st.session_state.current_wizard_step = 4
            st.rerun()

def render_synthese_onglet():
    st.header("📊 Synthèse du brief")
    
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("Veuillez d'abord créer ou charger un brief")
        return
    
    # Affichage des données principales
    if st.session_state.get("sources_df") is not None:
        st.subheader("Données collectées")
        
        # Statistiques basiques
        col1, col2, col3 = st.columns(3)
        with col1:
            total_items = sum([len(str(row["Mes infos (Demande interne)"]).split(',')) for _, row in st.session_state.sources_df.iterrows()])
            st.metric("Total éléments", total_items)
        with col2:
            g1_count = sum([1 for _, row in st.session_state.sources_df.iterrows() if "G1" in str(row["Classement"])])
            st.metric("G1 Incontournable", g1_count)
        with col3:
            completed_categories = sum([1 for _, row in st.session_state.sources_df.iterrows() if row["Mes infos (Demande interne)"] != ""])
            st.metric("Catégories complétées", f"{completed_categories}/{len(CATEGORIES)}")
        
        # Affichage des données
        st.dataframe(st.session_state.sources_df, use_container_width=True)
    
    # Affichage des suggestions de classement
    if st.session_state.get("g_suggestions"):
        st.subheader("Suggestions de classement")
        with st.expander("Voir les suggestions détaillées"):
            for category, items in st.session_state.g_suggestions.items():
                st.write(f"**{category}**")
                for item, classification in items.items():
                    st.write(f"- {item}: {classification}")
    
    # Affichage des informations contextuelles
    st.subheader("Informations contextuelles")
    context_col1, context_col2 = st.columns(2)
    
    with context_col1:
        st.write("**Poste**")
        st.info(st.session_state.get("poste_intitule", "Non spécifié"))
        
        st.write("**Raison d'ouverture**")
        st.info(st.session_state.get("raison_ouverture", "Non spécifié"))
        
        st.write("**Rattachement hiérarchique**")
        st.info(st.session_state.get("rattachement", "Non spécifié"))
        
        st.write("**Défis principaux**")
        st.info(st.session_state.get("defis_principaux", "Non spécifié"))
    
    with context_col2:
        st.write("**Localisation**")
        st.info(st.session_state.get("localisation", "Non spécifié"))
        
        st.write("**Budget**")
        st.info(st.session_state.get("budget", "Non spécifié"))
        
        st.write("**Expérience requise**")
        st.info(f"{st.session_state.get('annees_experience', 0)} ans")
        
        st.write("**Canaux à utiliser**")
        st.info(st.session_state.get("canaux_profil", "Non spécifié"))
    
    # Boutons d'action pour la synthèse
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Exporter la synthèse complète", key="export_full_btn"):
            st.info("Fonctionnalité d'export complète en cours de développement")
    
    with col2:
        if st.button("🔄 Retour à l'édition", key="back_to_edit_btn"):
            st.session_state.current_wizard_step = 2
            st.rerun()

# --- Interface principale ---
st.title("📋 BriefTool Pro")
st.markdown("Outil de préparation et gestion de briefs recrutement")

# Barre de progression du wizard
if st.session_state.current_wizard_step > 1:
    steps = ["Gestion", "Avant-brief", "Réunion", "Synthèse"]
    current_step = st.session_state.current_wizard_step - 1
    st.progress(current_step / 3, text=f"Étape {current_step}/3: {steps[current_step]}")

# Onglets
tab1, tab2, tab3, tab4 = st.tabs(["📁 Gestion", "🧠 Avant‑brief", "🤝 Réunion brief", "📊 Synthèse"])

with tab1:
    render_gestion_onglet()

with tab2:
    render_avant_brief_onglet()

with tab3:
    render_reunion_brief_onglet()

with tab4:
    render_synthese_onglet()

# Footer
st.markdown("---")
st.caption("BriefTool Pro v2.0 - © 2024 - Outil de gestion de briefs recrutement")