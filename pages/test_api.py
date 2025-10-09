import streamlit as st
import pandas as pd
import io
import json 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os

# Configuration de la page
st.set_page_config(
    page_title="Suivi des Dossiers RH - TGCC",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #1e88e5;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .complete-status {
        background-color: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .incomplete-status {
        background-color: #f8d7da;
        color: #721c24;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 4px;
        padding: 10px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #e3f2fd;
        border-bottom: 2px solid #1e88e5;
    }
</style>
""", unsafe_allow_html=True)

# Définition des documents RH standard
DOCUMENTS_RH = [
    "Copie CIN",
    "Attestation de travail précédente", 
    "Diplôme/Certificat de formation",
    "RIB (Relevé d'Identité Bancaire)",
    "Certificat médical d'aptitude",
    "Photo d'identité",
    "Contrat de travail signé",
    "Attestation de sécurité sociale",
    "Certificat de résidence",
    "Références professionnelles"
]

# Initialisation des données en session
if 'hr_database' not in st.session_state:
    # Base de données initiale avec quelques exemples
    st.session_state.hr_database = pd.DataFrame({
        'Nom': ['ALAMI', 'BENALI', 'CHERKAOUI'],
        'Prénom': ['Ahmed', 'Fatima', 'Mohamed'],
        'Poste': ['Ingénieur IT', 'Comptable', 'Technicien'],
        'Service': ['IT', 'Finance', 'Production'],
        'Email': ['ahmed.alami@tgcc.ma', 'fatima.benali@tgcc.ma', 'mohamed.cherkaoui@tgcc.ma'],
        'Date_integration': ['2024-01-15', '2024-02-01', '2024-01-30'],
        'Documents_manquants': [
            json.dumps(['Certificat médical d\'aptitude', 'Photo d\'identité']),
            json.dumps(['RIB (Relevé d\'Identité Bancaire)']),
            json.dumps([])
        ],
        'Statut': ['En cours', 'En cours', 'Complet'],
        'Derniere_relance': ['2024-01-20', '2024-02-05', ''],
        'Nombre_relances': [1, 2, 0]
    })

if 'relance_history' not in st.session_state:
    st.session_state.relance_history = pd.DataFrame(columns=[
        'Date', 'Collaborateur', 'Email', 'Documents_relances', 'Statut_envoi'
    ])

# Fonctions utilitaires
def save_data():
    """Sauvegarde les données dans un fichier CSV"""
    try:
        st.session_state.hr_database.to_csv('hr_dossiers.csv', index=False)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde: {e}")
        return False

def load_data():
    """Charge les données depuis un fichier CSV si il existe"""
    try:
        if Path('hr_dossiers.csv').exists():
            st.session_state.hr_database = pd.read_csv('hr_dossiers.csv')
            return True
    except Exception as e:
        st.error(f"Erreur lors du chargement: {e}")
    return False

def calculate_completion_percentage():
    """Calcule le pourcentage de dossiers complets"""
    if len(st.session_state.hr_database) == 0:
        return 0
    complete_count = len(st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'Complet'])
    return (complete_count / len(st.session_state.hr_database)) * 100

def get_missing_documents_count(documents_json):
    """Compte le nombre de documents manquants"""
    try:
        docs = json.loads(documents_json)
        return len(docs)
    except:
        return 0

def send_email_reminder(recipient_email, recipient_name, missing_docs, sender_email, sender_password):
    """Envoie un email de relance"""
    try:
        # Configuration SMTP Gmail
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Créer le message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Rappel - Documents manquants pour votre dossier RH"
        
        # Corps du message
        body = f"""
Bonjour {recipient_name},

J'espère que vous allez bien.

Je me permets de vous rappeler qu'il manque encore quelques documents pour compléter votre dossier RH :

{chr(10).join([f"• {doc}" for doc in missing_docs])}

Merci de bien vouloir nous transmettre ces documents dans les plus brefs délais pour finaliser votre intégration.

Si vous avez des questions, n'hésitez pas à me contacter.

Cordialement,
Service RH - TGCC
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Envoyer l'email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'envoi de l'email: {e}")
        return False

# Titre principal
st.markdown('<h1 class="main-header">📋 Suivi des Dossiers RH</h1>', unsafe_allow_html=True)
st.markdown("---")

# Créer les onglets
tab1, tab2, tab3 = st.tabs([
    "📊 Suivi Global",
    "👤 Gestion Collaborateur", 
    "📧 Relances Automatiques"
])

# ============================
# ONGLET 1: SUIVI GLOBAL
# ============================
with tab1:
    st.header("📊 Vue d'ensemble des dossiers RH")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_collaborateurs = len(st.session_state.hr_database)
        st.metric("👥 Total Collaborateurs", total_collaborateurs)
    
    with col2:
        complete_count = len(st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'Complet'])
        st.metric("✅ Dossiers Complets", complete_count)
    
    with col3:
        incomplete_count = total_collaborateurs - complete_count
        st.metric("⏳ Dossiers En Cours", incomplete_count)
    
    with col4:
        completion_rate = calculate_completion_percentage()
        st.metric("📈 Taux de Complétude", f"{completion_rate:.1f}%")
    
    # Barre de progression globale
    st.subheader("🎯 Progression Globale")
    progress_bar = st.progress(completion_rate / 100)
    st.write(f"**{completion_rate:.1f}%** des dossiers sont complets")
    
    # Graphiques
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Graphique en secteurs - Répartition des statuts
        status_counts = st.session_state.hr_database['Statut'].value_counts()
        fig_pie = px.pie(
            values=status_counts.values, 
            names=status_counts.index,
            title="Répartition des Statuts",
            color_discrete_map={'Complet': '#28a745', 'En cours': '#ffc107'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_chart2:
        # Graphique en barres - Par service
        service_stats = st.session_state.hr_database.groupby(['Service', 'Statut']).size().unstack(fill_value=0)
        fig_bar = px.bar(
            service_stats.reset_index(), 
            x='Service', 
            y=['Complet', 'En cours'] if 'En cours' in service_stats.columns else ['Complet'],
            title="Statuts par Service",
            color_discrete_map={'Complet': '#28a745', 'En cours': '#ffc107'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # Filtres
    st.subheader("🔍 Filtres")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        status_filter = st.selectbox("Filtrer par Statut", ["Tous", "Complet", "En cours"])
    
    with col_filter2:
        services = ["Tous"] + list(st.session_state.hr_database['Service'].unique())
        service_filter = st.selectbox("Filtrer par Service", services)
    
    with col_filter3:
        sort_by = st.selectbox("Trier par", [
            "Nom", "Date d'intégration", "Nombre de documents manquants", "Dernière relance"
        ])
    
    # Application des filtres
    filtered_df = st.session_state.hr_database.copy()
    
    if status_filter != "Tous":
        filtered_df = filtered_df[filtered_df['Statut'] == status_filter]
    
    if service_filter != "Tous":
        filtered_df = filtered_df[filtered_df['Service'] == service_filter]
    
    # Ajouter le nombre de documents manquants pour l'affichage
    filtered_df['Nb_docs_manquants'] = filtered_df['Documents_manquants'].apply(get_missing_documents_count)
    
    # Tableau principal
    st.subheader("📋 Liste des Collaborateurs")
    
    if len(filtered_df) > 0:
        # Préparer les données pour l'affichage
        display_df = filtered_df[['Nom', 'Prénom', 'Poste', 'Service', 'Email', 
                                 'Date_integration', 'Statut', 'Nb_docs_manquants', 
                                 'Derniere_relance', 'Nombre_relances']].copy()
        
        display_df.columns = ['Nom', 'Prénom', 'Poste', 'Service', 'Email', 
                             'Date Intégration', 'Statut', 'Docs Manquants', 
                             'Dernière Relance', 'Nb Relances']
        
        # Affichage avec formatage conditionnel
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Détails des documents manquants
        with st.expander("📄 Détail des documents manquants"):
            for idx, row in filtered_df.iterrows():
                if row['Statut'] == 'En cours':
                    try:
                        missing_docs = json.loads(row['Documents_manquants'])
                        if missing_docs:
                            st.write(f"**{row['Prénom']} {row['Nom']}** ({row['Poste']}):")
                            for doc in missing_docs:
                                st.write(f"  • {doc}")
                            st.write("")
                    except:
                        pass
    else:
        st.info("Aucun collaborateur ne correspond aux filtres sélectionnés.")
    
    # Boutons d'action
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        if st.button("💾 Sauvegarder les données", use_container_width=True):
            if save_data():
                st.success("✅ Données sauvegardées avec succès!")
    
    with col_action2:
        if st.button("📁 Charger les données", use_container_width=True):
            if load_data():
                st.success("✅ Données chargées avec succès!")
                st.rerun()

# ============================
# ONGLET 2: GESTION COLLABORATEUR
# ============================
with tab2:
    st.header("👤 Ajout / Mise à jour d'un Collaborateur")
    
    # Choix: Nouveau collaborateur ou mise à jour
    action_type = st.radio(
        "Que souhaitez-vous faire ?",
        ["➕ Ajouter un nouveau collaborateur", "✏️ Mettre à jour un collaborateur existant"],
        horizontal=True
    )
    
    if action_type == "➕ Ajouter un nouveau collaborateur":
        # Formulaire pour nouveau collaborateur
        with st.form("nouveau_collaborateur"):
            st.subheader("📝 Informations du nouveau collaborateur")
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                nom = st.text_input("Nom *", placeholder="Ex: ALAMI")
                prenom = st.text_input("Prénom *", placeholder="Ex: Ahmed")
                email = st.text_input("Email *", placeholder="Ex: ahmed.alami@tgcc.ma")
            
            with col_info2:
                poste = st.text_input("Poste *", placeholder="Ex: Ingénieur IT")
                service = st.selectbox("Service *", ["IT", "Finance", "Production", "RH", "Marketing", "Ventes", "Autre"])
                date_integration = st.date_input("Date d'intégration prévue")
            
            st.subheader("📋 Documents RH - Cochez les documents MANQUANTS")
            st.info("ℹ️ Cochez uniquement les documents que le collaborateur n'a PAS encore fournis")
            
            # Checklist des documents
            missing_docs = []
            for i, doc in enumerate(DOCUMENTS_RH):
                if st.checkbox(f"❌ {doc}", key=f"new_{i}"):
                    missing_docs.append(doc)
            
            # Bouton de soumission
            submitted = st.form_submit_button("➕ Ajouter le collaborateur", type="primary", use_container_width=True)
            
            if submitted:
                if nom and prenom and email and poste and service:
                    # Déterminer le statut
                    statut = "Complet" if len(missing_docs) == 0 else "En cours"
                    
                    # Créer la nouvelle entrée
                    nouvelle_ligne = pd.DataFrame({
                        'Nom': [nom.upper()],
                        'Prénom': [prenom.title()],
                        'Poste': [poste],
                        'Service': [service],
                        'Email': [email.lower()],
                        'Date_integration': [str(date_integration)],
                        'Documents_manquants': [json.dumps(missing_docs)],
                        'Statut': [statut],
                        'Derniere_relance': [''],
                        'Nombre_relances': [0]
                    })
                    
                    # Ajouter à la base de données
                    st.session_state.hr_database = pd.concat([st.session_state.hr_database, nouvelle_ligne], ignore_index=True)
                    
                    st.success(f"✅ {prenom} {nom} a été ajouté(e) avec succès!")
                    st.success(f"📊 Statut: **{statut}** ({len(missing_docs)} documents manquants)")
                    
                    if len(missing_docs) > 0:
                        st.info("📄 Documents manquants:")
                        for doc in missing_docs:
                            st.write(f"  • {doc}")
                    
                    st.rerun()
                else:
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
    
    else:
        # Mise à jour d'un collaborateur existant
        st.subheader("✏️ Mise à jour d'un collaborateur")
        
        if len(st.session_state.hr_database) > 0:
            # Sélection du collaborateur
            collaborateurs = st.session_state.hr_database.apply(lambda x: f"{x['Prénom']} {x['Nom']} ({x['Poste']})", axis=1).tolist()
            selected_collab = st.selectbox("Choisir le collaborateur à mettre à jour:", collaborateurs)
            
            if selected_collab:
                # Trouver l'index du collaborateur sélectionné
                selected_idx = collaborateurs.index(selected_collab)
                collab_data = st.session_state.hr_database.iloc[selected_idx]
                
                st.info(f"📊 Statut actuel: **{collab_data['Statut']}**")
                
                # Afficher les documents actuellement manquants
                try:
                    current_missing = json.loads(collab_data['Documents_manquants'])
                except:
                    current_missing = []
                
                if current_missing:
                    st.warning(f"📄 Documents actuellement manquants ({len(current_missing)}):")
                    for doc in current_missing:
                        st.write(f"  • {doc}")
                else:
                    st.success("✅ Dossier complet - Aucun document manquant!")
                
                # Formulaire de mise à jour
                with st.form("mise_a_jour"):
                    st.subheader("📋 Mise à jour des documents manquants")
                    st.info("ℹ️ Cochez les documents qui sont ENCORE manquants")
                    
                    # Checklist avec état actuel
                    new_missing_docs = []
                    for i, doc in enumerate(DOCUMENTS_RH):
                        is_currently_missing = doc in current_missing
                        if st.checkbox(f"❌ {doc}", value=is_currently_missing, key=f"update_{i}"):
                            new_missing_docs.append(doc)
                    
                    # Bouton de mise à jour
                    update_submitted = st.form_submit_button("🔄 Mettre à jour", type="primary", use_container_width=True)
                    
                    if update_submitted:
                        # Déterminer le nouveau statut
                        nouveau_statut = "Complet" if len(new_missing_docs) == 0 else "En cours"
                        
                        # Mettre à jour la base de données
                        st.session_state.hr_database.loc[selected_idx, 'Documents_manquants'] = json.dumps(new_missing_docs)
                        st.session_state.hr_database.loc[selected_idx, 'Statut'] = nouveau_statut
                        
                        # Afficher le résultat
                        if nouveau_statut == "Complet":
                            st.success(f"🎉 Félicitations! Le dossier de {collab_data['Prénom']} {collab_data['Nom']} est maintenant COMPLET!")
                        else:
                            st.info(f"📊 Dossier mis à jour. Statut: **{nouveau_statut}** ({len(new_missing_docs)} documents encore manquants)")
                            if new_missing_docs:
                                st.write("📄 Documents encore manquants:")
                                for doc in new_missing_docs:
                                    st.write(f"  • {doc}")
                        
                        st.rerun()
        else:
            st.info("📭 Aucun collaborateur dans la base de données. Ajoutez d'abord un collaborateur.")

# ============================
# ONGLET 3: RELANCES AUTOMATIQUES
# ============================
with tab3:
    st.header("📧 Système de Relances Automatiques")
    
    # Configuration Gmail
    with st.expander("⚙️ Configuration Gmail", expanded=False):
        st.info("🔐 Configuration sécurisée de votre compte Gmail pour l'envoi automatique")
        
        col_gmail1, col_gmail2 = st.columns(2)
        
        with col_gmail1:
            sender_email = st.text_input("📧 Votre email Gmail", placeholder="votre.email@gmail.com")
        
        with col_gmail2:
            sender_password = st.text_input("🔑 Mot de passe d'application", type="password", 
                                          help="Utilisez un mot de passe d'application Gmail (pas votre mot de passe principal)")
        
        st.warning("⚠️ **Important**: Utilisez un 'Mot de passe d'application' Gmail, pas votre mot de passe principal. "
                  "Allez dans votre compte Google > Sécurité > Mots de passe d'application pour en créer un.")
    
    # Sélection des collaborateurs à relancer
    st.subheader("👥 Collaborateurs avec documents manquants")
    
    # Filtrer les collaborateurs avec des documents manquants
    incomplete_collabs = st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'En cours'].copy()
    
    if len(incomplete_collabs) > 0:
        # Tableau des collaborateurs à relancer
        display_incomplete = incomplete_collabs[['Nom', 'Prénom', 'Poste', 'Email', 'Date_integration', 'Derniere_relance', 'Nombre_relances']].copy()
        display_incomplete['Nb_docs_manquants'] = incomplete_collabs['Documents_manquants'].apply(get_missing_documents_count)
        
        display_incomplete.columns = ['Nom', 'Prénom', 'Poste', 'Email', 'Date Intégration', 'Dernière Relance', 'Nb Relances', 'Docs Manquants']
        
        st.dataframe(display_incomplete, use_container_width=True, hide_index=True)
        
        # Formulaire de relance
        st.subheader("📨 Envoyer une relance")
        
        with st.form("relance_form"):
            # Sélection du collaborateur
            collab_options = incomplete_collabs.apply(lambda x: f"{x['Prénom']} {x['Nom']} ({x['Email']})", axis=1).tolist()
            selected_collab_relance = st.selectbox("Choisir le collaborateur:", collab_options)
            
            if selected_collab_relance:
                # Trouver les données du collaborateur sélectionné
                selected_idx_relance = collab_options.index(selected_collab_relance)
                collab_relance_data = incomplete_collabs.iloc[selected_idx_relance]
                
                # Afficher les documents manquants
                try:
                    missing_docs_relance = json.loads(collab_relance_data['Documents_manquants'])
                except:
                    missing_docs_relance = []
                
                st.info(f"📄 Documents manquants pour {collab_relance_data['Prénom']} {collab_relance_data['Nom']}:")
                for doc in missing_docs_relance:
                    st.write(f"  • {doc}")
                
                # Template de message (modifiable)
                default_message = f"""Bonjour {collab_relance_data['Prénom']},

J'espère que vous allez bien.

Je me permets de vous rappeler qu'il manque encore quelques documents pour compléter votre dossier RH :

{chr(10).join([f"• {doc}" for doc in missing_docs_relance])}

Merci de bien vouloir nous transmettre ces documents dans les plus brefs délais pour finaliser votre intégration.

Si vous avez des questions, n'hésitez pas à me contacter.

Cordialement,
Service RH - TGCC"""
                
                message_body = st.text_area("✏️ Message de relance (modifiable):", value=default_message, height=300)
                
                # Bouton d'envoi
                send_button = st.form_submit_button("📧 Envoyer la relance", type="primary", use_container_width=True)
                
                if send_button:
                    if sender_email and sender_password:
                        with st.spinner("📤 Envoi de l'email en cours..."):
                            success = send_email_reminder(
                                collab_relance_data['Email'],
                                collab_relance_data['Prénom'],
                                missing_docs_relance,
                                sender_email,
                                sender_password
                            )
                            
                            if success:
                                # Mettre à jour les données de relance
                                original_idx = st.session_state.hr_database[
                                    (st.session_state.hr_database['Nom'] == collab_relance_data['Nom']) &
                                    (st.session_state.hr_database['Prénom'] == collab_relance_data['Prénom'])
                                ].index[0]
                                
                                st.session_state.hr_database.loc[original_idx, 'Derniere_relance'] = datetime.now().strftime('%Y-%m-%d')
                                st.session_state.hr_database.loc[original_idx, 'Nombre_relances'] += 1
                                
                                # Ajouter à l'historique
                                nouvelle_relance = pd.DataFrame({
                                    'Date': [datetime.now().strftime('%Y-%m-%d %H:%M')],
                                    'Collaborateur': [f"{collab_relance_data['Prénom']} {collab_relance_data['Nom']}"],
                                    'Email': [collab_relance_data['Email']],
                                    'Documents_relances': [json.dumps(missing_docs_relance)],
                                    'Statut_envoi': ['Envoyé']
                                })
                                
                                st.session_state.relance_history = pd.concat([st.session_state.relance_history, nouvelle_relance], ignore_index=True)
                                
                                st.success(f"✅ Email envoyé avec succès à {collab_relance_data['Prénom']} {collab_relance_data['Nom']}!")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de l'envoi de l'email. Vérifiez vos paramètres Gmail.")
                    else:
                        st.error("❌ Veuillez configurer vos paramètres Gmail d'abord.")
    
    else:
        st.success("🎉 Aucune relance nécessaire! Tous les dossiers sont complets.")
    
    # Historique des relances
    st.markdown("---")
    st.subheader("📈 Historique des Relances")
    
    if len(st.session_state.relance_history) > 0:
        # Affichage de l'historique
        history_display = st.session_state.relance_history.copy()
        history_display = history_display.sort_values('Date', ascending=False)
        
        st.dataframe(history_display, use_container_width=True, hide_index=True)
        
        # Statistiques des relances
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            total_relances = len(st.session_state.relance_history)
            st.metric("📧 Total Relances", total_relances)
        
        with col_stat2:
            relances_today = len(st.session_state.relance_history[
                st.session_state.relance_history['Date'].str.startswith(datetime.now().strftime('%Y-%m-%d'))
            ])
            st.metric("📅 Relances Aujourd'hui", relances_today)
        
        with col_stat3:
            avg_relances = st.session_state.hr_database[st.session_state.hr_database['Nombre_relances'] > 0]['Nombre_relances'].mean()
            if pd.notna(avg_relances):
                st.metric("📊 Moyenne Relances/Collab", f"{avg_relances:.1f}")
            else:
                st.metric("📊 Moyenne Relances/Collab", "0")
    
    else:
        st.info("📭 Aucune relance envoyée pour le moment.")

# Footer
st.markdown("---")
st.markdown("**💼 Système de Suivi des Dossiers RH - TGCC** | Version 1.0")
