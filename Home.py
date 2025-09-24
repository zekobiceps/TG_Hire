import streamlit as st
from utils import *
from datetime import datetime
import pandas as pd

# Initialisation de l'état de session
init_session_state()

# Stockage temporaire des utilisateurs avec nom complet
USERS = {
    "zakaria.fassih@tgcc.ma": {"password": "password123", "name": "Zakaria Fassih"},
    "user2@example.com": {"password": "securepass", "name": "Utilisateur Test"}
}

# Vérification de l'état de connexion
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""

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
        if email in USERS and USERS[email]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.current_user = USERS[email]["name"]
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

    # Afficher le nom d'utilisateur dans la sidebar
    st.sidebar.success(f"Connecté en tant que : {st.session_state.current_user}")

    # --- TABLEAU KANBAN DES FONCTIONNALITÉS ---
    
    # Création des colonnes Kanban
    col1, col2, col3 = st.columns(3)
    
    # Colonne "À développer"
    with col1:
        st.markdown("### 📋 À développer")
        st.markdown("---")
        for feature in st.session_state.features["À développer"]:
            priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
            
            # Conteneur de la carte avec boutons de déplacement
            st.markdown(f"""
            <div style="
                background: #ffebee; 
                padding: 12px; 
                border-radius: 8px; 
                margin: 8px 0; 
                border-left: 4px solid {priority_color[feature['priority']]};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                color: #000000;
                position: relative;
            ">
            <div style="font-weight: bold; font-size: 14px; color: #000000;">📌 {feature['title']}</div>
            <div style="font-size: 12px; color: #333333; margin: 5px 0;">{feature['description']}</div>
            <div style="font-size: 11px; color: #666666;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Boutons de déplacement
            col_move1, col_move2 = st.columns(2)
            with col_move1:
                if st.button("➡️ Déplacer →", key=f"move_right_{feature['id']}", use_container_width=True):
                    st.session_state.features["À développer"].remove(feature)
                    st.session_state.features["En cours"].append(feature)
                    st.rerun()
    
    # Colonne "En cours"
    with col2:
        st.markdown("### 🔄 En cours")
        st.markdown("---")
        for feature in st.session_state.features["En cours"]:
            priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
            
            st.markdown(f"""
            <div style="
                background: #fff3e0; 
                padding: 12px; 
                border-radius: 8px; 
                margin: 8px 0; 
                border-left: 4px solid {priority_color[feature['priority']]};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                color: #000000;
                position: relative;
            ">
            <div style="font-weight: bold; font-size: 14px; color: #000000;">⚡ {feature['title']}</div>
            <div style="font-size: 12px; color: #333333; margin: 5px 0;">{feature['description']}</div>
            <div style="font-size: 11px; color: #666666;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Boutons de déplacement
            col_move1, col_move2 = st.columns(2)
            with col_move1:
                if st.button("⬅️ ← Déplacer", key=f"move_left_{feature['id']}", use_container_width=True):
                    st.session_state.features["En cours"].remove(feature)
                    st.session_state.features["À développer"].append(feature)
                    st.rerun()
            with col_move2:
                if st.button("➡️ Déplacer →", key=f"move_right_e_{feature['id']}", use_container_width=True):
                    st.session_state.features["En cours"].remove(feature)
                    st.session_state.features["Réalisé"].append(feature)
                    st.rerun()
    
    # Colonne "Réalisé"
    with col3:
        st.markdown("### ✅ Réalisé")
        st.markdown("---")
        for feature in st.session_state.features["Réalisé"]:
            priority_color = {"Haute": "#f44336", "Moyenne": "#ff9800", "Basse": "#4caf50"}
            
            st.markdown(f"""
            <div style="
                background: #e8f5e8; 
                padding: 12px; 
                border-radius: 8px; 
                margin: 8px 0; 
                border-left: 4px solid {priority_color[feature['priority']]};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                color: #000000;
                position: relative;
            ">
            <div style="font-weight: bold; font-size: 14px; color: #000000;">✅ {feature['title']}</div>
            <div style="font-size: 12px; color: #333333; margin: 5px 0;">{feature['description']}</div>
            <div style="font-size: 11px; color: #666666;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Bouton de déplacement
            if st.button("⬅️ ← Déplacer", key=f"move_left_r_{feature['id']}", use_container_width=True):
                st.session_state.features["Réalisé"].remove(feature)
                st.session_state.features["En cours"].append(feature)
                st.rerun()
    
    # --- STATISTIQUES SIMPLES ---
    st.markdown("---")
    
    total_features = sum(len(features) for features in st.session_state.features.values())
    completed_features = len(st.session_state.features["Réalisé"])
    
    col_stats1, col_stats2 = st.columns(2)
    
    with col_stats1:
        st.metric("Fonctionnalités totales", total_features)
    
    with col_stats2:
        completion_rate = (completed_features / total_features * 100) if total_features > 0 else 0
        st.metric("Taux de réalisation", f"{completion_rate:.1f}%")

    # --- ONGLET DE GESTION ---
    st.markdown("---")
    with st.expander("🔧 Gestion avancée des fonctionnalités", expanded=False):
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])
        
        with tab1:
            st.subheader("Ajouter une nouvelle fonctionnalité")
            with st.form(key="add_feature_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_title = st.text_input("Titre de la fonctionnalité *")
                    new_description = st.text_area("Description *", height=100)
                
                with col2:
                    new_status = st.selectbox("Statut *", ["À développer", "En cours", "Réalisé"])
                    new_priority = st.selectbox("Priorité *", ["Haute", "Moyenne", "Basse"])
                
                if st.form_submit_button("💾 Ajouter la fonctionnalité"):
                    if new_title and new_description:
                        # Trouver le prochain ID disponible
                        all_ids = []
                        for status, features in st.session_state.features.items():
                            for feature in features:
                                all_ids.append(feature["id"])
                        new_id = max(all_ids) + 1 if all_ids else 1
                        
                        new_feature = {
                            "id": new_id,
                            "title": new_title,
                            "description": new_description,
                            "priority": new_priority,
                            "date_ajout": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.features[new_status].append(new_feature)
                        st.success("✅ Fonctionnalité ajoutée avec succès !")
                        st.rerun()
                    else:
                        st.error("❌ Veuillez remplir tous les champs obligatoires")
        
        with tab2:
            st.subheader("Modifier une fonctionnalité")
            if total_features > 0:
                # Liste des fonctionnalités pour modification
                all_features = []
                for status, features in st.session_state.features.items():
                    for feature in features:
                        all_features.append((feature["id"], f"{feature['title']} ({status})"))
                
                selected_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à modifier",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), "")
                )
                
                if selected_feature_id:
                    # Trouver la fonctionnalité sélectionnée
                    selected_feature = None
                    old_status = None
                    for status, features in st.session_state.features.items():
                        for feature in features:
                            if feature["id"] == selected_feature_id:
                                selected_feature = feature
                                old_status = status
                                break
                    
                    if selected_feature:
                        with st.form(key="edit_feature_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edit_title = st.text_input("Titre", value=selected_feature["title"])
                                edit_description = st.text_area("Description", value=selected_feature["description"], height=100)
                            
                            with col2:
                                edit_status = st.selectbox("Statut", ["À développer", "En cours", "Réalisé"], 
                                                         index=["À développer", "En cours", "Réalisé"].index(old_status))
                                edit_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"], 
                                                           index=["Haute", "Moyenne", "Basse"].index(selected_feature["priority"]))
                            
                            if st.form_submit_button("💾 Enregistrer les modifications"):
                                # Supprimer l'ancienne version
                                st.session_state.features[old_status] = [f for f in st.session_state.features[old_status] if f["id"] != selected_feature_id]
                                
                                # Ajouter la nouvelle version
                                updated_feature = {
                                    "id": selected_feature_id,
                                    "title": edit_title,
                                    "description": edit_description,
                                    "priority": edit_priority,
                                    "date_ajout": selected_feature["date_ajout"]
                                }
                                st.session_state.features[edit_status].append(updated_feature)
                                st.success("✅ Fonctionnalité modifiée avec succès !")
                                st.rerun()
            else:
                st.info("Aucune fonctionnalité à modifier.")
        
        with tab3:
            st.subheader("Supprimer une fonctionnalité")
            if total_features > 0:
                # Liste des fonctionnalités pour suppression
                all_features = []
                for status, features in st.session_state.features.items():
                    for feature in features:
                        all_features.append((feature["id"], f"{feature['title']} ({status})"))
                
                delete_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à supprimer",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), ""),
                    key="delete_select"
                )
                
                if delete_feature_id:
                    if st.button("🗑️ Supprimer définitivement", type="secondary"):
                        # Trouver et supprimer la fonctionnalité
                        for status, features in st.session_state.features.items():
                            st.session_state.features[status] = [f for f in features if f["id"] != delete_feature_id]
                        st.success("✅ Fonctionnalité supprimée avec succès !")
                        st.rerun()
            else:
                st.info("Aucune fonctionnalité à supprimer.")

    st.markdown("---")
    st.caption("📊 TG-Hire IA - Roadmap Fonctionnelle | Version 1.0")

    # Bouton de déconnexion dans la sidebar
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.rerun()

    # Protéger les pages dans pages/ (arrête l'exécution si non connecté)
    if not st.session_state.logged_in:
        st.stop()