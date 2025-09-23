import streamlit as st
from utils import *
from datetime import datetime

# Initialisation de l'état de session
init_session_state()

# Stockage temporaire des utilisateurs (à remplacer par une base sécurisée)
USERS = {
    "user1@example.com": "password123",
    "user2@example.com": "securepass"
}

# Vérification de l'état de connexion
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Initialisation des fonctionnalités dans session_state
if "features" not in st.session_state:
    st.session_state.features = {
        "À développer": [
            {"id": 1, "title": "Intégration avec LinkedIn API", "description": "Connexion API LinkedIn pour sourcing automatique", "priority": "Haute", "date_ajout": "2024-01-15"},
            {"id": 2, "title": "Système de notifications en temps réel", "description": "Notifications push pour les nouveaux candidats", "priority": "Moyenne", "date_ajout": "2024-01-10"},
            {"id": 3, "title": "Analyse de sentiment des entretiens", "description": "IA d'analyse des retours d'entretiens", "priority": "Basse", "date_ajout": "2024-01-08"},
            {"id": 4, "title": "Tableau de bord analytics avancé", "description": "Statistiques détaillées et rapports", "priority": "Moyenne", "date_ajout": "2024-01-12"},
            {"id": 5, "title": "Export automatique vers ATS", "description": "Intégration avec les systèmes ATS externes", "priority": "Haute", "date_ajout": "2024-01-05"}
        ],
        "En cours": [
            {"id": 6, "title": "Optimisation de l'IA de matching", "description": "Amélioration des algorithmes de matching", "priority": "Haute", "date_ajout": "2024-01-20"},
            {"id": 7, "title": "Interface mobile responsive", "description": "Adaptation pour mobile et tablette", "priority": "Moyenne", "date_ajout": "2024-01-18"},
            {"id": 8, "title": "Synchronisation cloud", "description": "Sauvegarde et sync cloud", "priority": "Haute", "date_ajout": "2024-01-22"}
        ],
        "Réalisé": [
            {"id": 9, "title": "Système d'authentification", "description": "Login sécurisé avec gestion des utilisateurs", "priority": "Haute", "date_ajout": "2024-01-03"},
            {"id": 10, "title": "Analyse basique de CV", "description": "Extraction et analyse textuelle des CVs", "priority": "Haute", "date_ajout": "2024-01-02"},
            {"id": 11, "title": "Classement par similarité cosinus", "description": "Algorithme de matching par similarité", "priority": "Moyenne", "date_ajout": "2024-01-01"},
            {"id": 12, "title": "Export PDF/Word des briefs", "description": "Génération de documents exportables", "priority": "Moyenne", "date_ajout": "2023-12-28"},
            {"id": 13, "title": "Matrice KSA interactive", "description": "Interface interactive pour la matrice compétences", "priority": "Haute", "date_ajout": "2023-12-25"}
        ]
    }

# Page de login
if not st.session_state.logged_in:
    st.set_page_config(
        page_title="TG-Hire IA - Roadmap Fonctionnelle",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("📊 TG-Hire IA - Roadmap Fonctionnelle")
    st.write("Veuillez vous connecter pour accéder à l'outil.")
    
    email = st.text_input("Adresse Email", key="login_email")
    password = st.text_input("Mot de Passe", type="password", key="login_password")
    
    if st.button("Se Connecter"):
        if email in USERS and USERS[email] == password:
            st.session_state.logged_in = True
            st.success("Connexion réussie !")
            st.rerun()
        else:
            st.error("Email ou mot de passe incorrect.")
else:
    # Page d'accueil après connexion
    st.set_page_config(
        page_title="TG-Hire IA - Roadmap Fonctionnelle",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📊 Roadmap Fonctionnelle")
    st.write("Suivi du développement des fonctionnalités TG-Hire IA")

    st.sidebar.success("Choisissez une page ci-dessus.")

    # --- GESTION DES FONCTIONNALITÉS ---
    st.markdown("---")
    
    # Formulaire pour ajouter/modifier une fonctionnalité
    with st.expander("➕ Ajouter une nouvelle fonctionnalité", expanded=False):
        with st.form(key="feature_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                feature_title = st.text_input("Titre de la fonctionnalité *", placeholder="Ex: Intégration API LinkedIn")
                feature_description = st.text_area("Description détaillée *", placeholder="Décrivez la fonctionnalité...", height=100)
            
            with col2:
                feature_status = st.selectbox("Statut *", ["À développer", "En cours", "Réalisé"])
                feature_priority = st.selectbox("Priorité *", ["Haute", "Moyenne", "Basse"])
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_feature = st.form_submit_button("💾 Enregistrer la fonctionnalité", type="primary")
            with col_btn2:
                cancel_feature = st.form_submit_button("🗑️ Annuler")
            
            if submit_feature:
                if feature_title and feature_description:
                    # Générer un ID unique
                    new_id = max([max([f["id"] for f in features]) for features in st.session_state.features.values()]) + 1
                    
                    new_feature = {
                        "id": new_id,
                        "title": feature_title,
                        "description": feature_description,
                        "priority": feature_priority,
                        "date_ajout": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    st.session_state.features[feature_status].append(new_feature)
                    st.success(f"✅ Fonctionnalité '{feature_title}' ajoutée avec succès !")
                    st.rerun()
                else:
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*)")

    # --- TABLEAU KANBAN DES FONCTIONNALITÉS ---
    st.markdown("## 📋 Tableau Kanban des Fonctionnalités")
    
    # Création des colonnes Kanban
    col1, col2, col3 = st.columns(3)
    
    # Colonne "À développer"
    with col1:
        st.markdown("### 📋 À développer")
        st.markdown("---")
        for feature in st.session_state.features["À développer"]:
            with st.container():
                priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
                st.markdown(f"""
                <div style="
                    background: #ffebee; 
                    padding: 12px; 
                    border-radius: 8px; 
                    margin: 8px 0; 
                    border-left: 4px solid {priority_color[feature['priority']]};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                <div style="font-weight: bold; font-size: 14px;">📌 {feature['title']}</div>
                <div style="font-size: 12px; color: #666; margin: 5px 0;">{feature['description']}</div>
                <div style="font-size: 11px; color: #888;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Boutons d'action pour chaque fonctionnalité
                col_act1, col_act2, col_act3 = st.columns(3)
                with col_act1:
                    if st.button("✏️", key=f"edit_{feature['id']}", help="Modifier"):
                        st.session_state.editing_feature = feature
                with col_act2:
                    if st.button("➡️", key=f"move_{feature['id']}", help="Déplacer vers En cours"):
                        st.session_state.features["À développer"].remove(feature)
                        st.session_state.features["En cours"].append(feature)
                        st.rerun()
                with col_act3:
                    if st.button("🗑️", key=f"delete_{feature['id']}", help="Supprimer"):
                        st.session_state.features["À développer"].remove(feature)
                        st.rerun()
                st.markdown("---")
    
    # Colonne "En cours"
    with col2:
        st.markdown("### 🔄 En cours")
        st.markdown("---")
        for feature in st.session_state.features["En cours"]:
            with st.container():
                priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
                st.markdown(f"""
                <div style="
                    background: #fff3e0; 
                    padding: 12px; 
                    border-radius: 8px; 
                    margin: 8px 0; 
                    border-left: 4px solid {priority_color[feature['priority']]};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                <div style="font-weight: bold; font-size: 14px;">⚡ {feature['title']}</div>
                <div style="font-size: 12px; color: #666; margin: 5px 0;">{feature['description']}</div>
                <div style="font-size: 11px; color: #888;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                col_act1, col_act2, col_act3, col_act4 = st.columns(4)
                with col_act1:
                    if st.button("✏️", key=f"edit_e_{feature['id']}", help="Modifier"):
                        st.session_state.editing_feature = feature
                with col_act2:
                    if st.button("⬅️", key=f"move_back_{feature['id']}", help="Déplacer vers À développer"):
                        st.session_state.features["En cours"].remove(feature)
                        st.session_state.features["À développer"].append(feature)
                        st.rerun()
                with col_act3:
                    if st.button("➡️", key=f"move_next_{feature['id']}", help="Déplacer vers Réalisé"):
                        st.session_state.features["En cours"].remove(feature)
                        st.session_state.features["Réalisé"].append(feature)
                        st.rerun()
                with col_act4:
                    if st.button("🗑️", key=f"delete_e_{feature['id']}", help="Supprimer"):
                        st.session_state.features["En cours"].remove(feature)
                        st.rerun()
                st.markdown("---")
    
    # Colonne "Réalisé"
    with col3:
        st.markdown("### ✅ Réalisé")
        st.markdown("---")
        for feature in st.session_state.features["Réalisé"]:
            with st.container():
                priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
                st.markdown(f"""
                <div style="
                    background: #e8f5e8; 
                    padding: 12px; 
                    border-radius: 8px; 
                    margin: 8px 0; 
                    border-left: 4px solid {priority_color[feature['priority']]};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                <div style="font-weight: bold; font-size: 14px;">✅ {feature['title']}</div>
                <div style="font-size: 12px; color: #666; margin: 5px 0;">{feature['description']}</div>
                <div style="font-size: 11px; color: #888;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                col_act1, col_act2, col_act3 = st.columns(3)
                with col_act1:
                    if st.button("✏️", key=f"edit_r_{feature['id']}", help="Modifier"):
                        st.session_state.editing_feature = feature
                with col_act2:
                    if st.button("⬅️", key=f"move_back_r_{feature['id']}", help="Déplacer vers En cours"):
                        st.session_state.features["Réalisé"].remove(feature)
                        st.session_state.features["En cours"].append(feature)
                        st.rerun()
                with col_act3:
                    if st.button("🗑️", key=f"delete_r_{feature['id']}", help="Supprimer"):
                        st.session_state.features["Réalisé"].remove(feature)
                        st.rerun()
                st.markdown("---")
    
    # --- STATISTIQUES ---
    st.markdown("---")
    st.markdown("## 📈 Statistiques de Progression")
    
    total_features = sum(len(features) for features in st.session_state.features.values())
    completed_features = len(st.session_state.features["Réalisé"])
    in_progress_features = len(st.session_state.features["En cours"])
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    
    with col_stats1:
        st.metric("Fonctionnalités totales", total_features)
    
    with col_stats2:
        completion_rate = (completed_features / total_features * 100) if total_features > 0 else 0
        st.metric("Taux de réalisation", f"{completion_rate:.1f}%")
    
    with col_stats3:
        st.metric("En développement", in_progress_features)
    
    with col_stats4:
        st.metric("En attente", len(st.session_state.features["À développer"]))
    
    # Barre de progression
    progress = completed_features / total_features if total_features > 0 else 0
    st.progress(progress)
    st.caption(f"Progression générale: {completed_features}/{total_features} fonctionnalités ({completion_rate:.1f}%)")

    # --- EXPORT DES DONNÉES ---
    st.markdown("---")
    st.markdown("## 💾 Export des Données")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📥 Exporter la roadmap (CSV)", use_container_width=True):
            # Créer un DataFrame pour l'export
            export_data = []
            for status, features in st.session_state.features.items():
                for feature in features:
                    export_data.append({
                        "Statut": status,
                        "Titre": feature["title"],
                        "Description": feature["description"],
                        "Priorité": feature["priority"],
                        "Date d'ajout": feature["date_ajout"]
                    })
            
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Télécharger CSV",
                csv,
                "roadmap_tghire.csv",
                "text/csv",
                use_container_width=True
            )
    
    with col_export2:
        if st.button("🔄 Réinitialiser la roadmap", use_container_width=True):
            if st.checkbox("Confirmer la réinitialisation (cette action est irréversible)"):
                st.session_state.features = {
                    "À développer": [],
                    "En cours": [],
                    "Réalisé": []
                }
                st.success("Roadmap réinitialisée !")
                st.rerun()

    st.divider()
    st.caption("📊 TG-Hire IA - Roadmap Fonctionnelle | Made with ❤️")

    # Bouton de déconnexion dans la sidebar
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.rerun()

    # Protéger les pages dans pages/ (arrête l'exécution si non connecté)
    if not st.session_state.logged_in:
        st.stop()