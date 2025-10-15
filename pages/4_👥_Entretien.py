import streamlit as st
import pandas as pd
import os
import datetime

# --- Configuration de la page principale ---
st.set_page_config(page_title="HR Eval Pro", layout="wide", page_icon="🚀")

# --- Fonctions de base ---

def load_data(file_path):
    """Charge les données depuis un fichier CSV. Retourne un DataFrame vide si le fichier n'existe pas."""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

def save_data(df, file_path):
    """Sauvegarde le DataFrame dans un fichier CSV."""
    df.to_csv(file_path, index=False)

# --- Définition des Pages de l'Application ---

def page_evaluation():
    """Page pour saisir l'évaluation d'un nouveau candidat."""

    st.title("📝 Évaluation du Candidat")
    st.markdown("Remplissez ce formulaire structuré pour évaluer le candidat sur les compétences clés du poste.")

    # --- Section 1: Informations Générales ---
    st.header("1. Informations sur le Candidat")
    col1, col2 = st.columns(2)
    with col1:
        nom_candidat = st.text_input("Nom du candidat")
    with col2:
        prenom_candidat = st.text_input("Prénom du candidat")

    st.markdown("---")

    # --- Utilisation des onglets pour une meilleure organisation ---
    tab1, tab2, tab3 = st.tabs(["**Entretien Structuré (40%)**", "**Test Cognitif (20%)**", "**Échantillon de Travail (40%)**"])

    with tab1:
        st.subheader("Question 1 : Orientation Résultat")
        st.markdown("> *Parlez-moi d'un objectif de recrutement difficile que vous avez eu. Quelle était votre stratégie pour l'atteindre et quel a été le résultat ?*")
        notes_q1 = st.text_area("Notes Q1 :", height=100, key="notes_q1")
        note_q1 = st.slider("Note Q1", 1, 5, 3, key="note_q1")

        st.subheader("Question 2 : Sens Critique et Analyse")
        st.markdown("> *Décrivez une situation où un manager opérationnel n'était pas d'accord avec votre sélection. Comment avez-vous argumenté et géré la situation ?*")
        notes_q2 = st.text_area("Notes Q2 :", height=100, key="notes_q2")
        note_q2 = st.slider("Note Q2", 1, 5, 3, key="note_q2")

        st.subheader("Question 3 : Gestion du Stress (Situationnelle)")
        st.markdown("> *Imaginez : 3 postes urgents à pourvoir pour 3 managers différents qui attendent un retour rapide. Comment organisez-vous votre semaine ?*")
        notes_q3 = st.text_area("Notes Q3 :", height=100, key="notes_q3")
        note_q3 = st.slider("Note Q3", 1, 5, 3, key="note_q3")

    with tab2:
        st.subheader("Exercice : Analyse et Synthèse (5 min)")
        st.info("Consigne : Vous recevez 5 CV pour un poste de 'Chef de Projet'. Classez-les du plus pertinent au moins pertinent, en justifiant chaque choix en une phrase.")
        reponse_cognitif = st.text_area("Réponse et classement du candidat :", height=150, key="reponse_cognitif")
        note_cognitif = st.slider("Note Test Cognitif", 1, 5, 3, key="note_cognitif")

    with tab3:
        st.subheader("Tâche 1 : Communication Écrite (5 min)")
        st.info("Consigne : Rédigez un court e-mail d'approche directe sur LinkedIn pour un candidat passif.")
        reponse_tache1 = st.text_area("Email rédigé par le candidat :", height=150, key="reponse_tache1")
        note_tache1 = st.slider("Note Tâche 1", 1, 5, 3, key="note_tache1")

        st.subheader("Tâche 2 : Sourcing (3 min)")
        st.info("Consigne : Donnez la requête booléenne pour trouver un 'Développeur Python' avec 'Django' mais sans 'PHP'.")
        reponse_tache2 = st.text_input("Requête booléenne du candidat :", key="reponse_tache2")
        note_tache2 = st.slider("Note Tâche 2", 1, 5, 3, key="note_tache2")

    st.markdown("---")

    # --- Section de Synthèse et Décision ---
    st.header("Synthèse et Décision Finale")

    # Calcul des scores
    score_entretien = (note_q1 + note_q2 + note_q3) / 3
    score_cognitif = float(note_cognitif)
    score_echantillon = (note_tache1 + note_tache2) / 2
    score_final = (score_entretien * 0.4) + (score_cognitif * 0.2) + (score_echantillon * 0.4)

    st.subheader(f"Score Final Pondéré : {score_final:.2f} / 5.0")
    st.progress(score_final / 5)

    points_forts = st.text_area("Points forts observés", height=100)
    axes_amelioration = st.text_area("Axes d'amélioration potentiels", height=100)
    decision = st.selectbox("Décision", ["", "À recruter", "À recruter (avec réserves)", "Ne pas recruter"])

    if st.button("💾 Enregistrer l'évaluation", type="primary"):
        if nom_candidat and prenom_candidat and decision:
            file_path = 'evaluations_candidats.csv'
            df_existing = load_data(file_path)

            new_data = {
                'Date': [datetime.date.today().strftime("%Y-%m-%d")],
                'Nom': [nom_candidat], 'Prénom': [prenom_candidat],
                'Score Final': [round(score_final, 2)], 'Décision': [decision],
                'Score Entretien': [round(score_entretien, 2)],
                'Score Cognitif': [round(score_cognitif, 2)],
                'Score Échantillon': [round(score_echantillon, 2)],
                'Points Forts': [points_forts], 'Axes Amélioration': [axes_amelioration]
            }
            df_new = pd.DataFrame(new_data)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

            save_data(df_combined, file_path)
            st.success(f"Évaluation pour {prenom_candidat} {nom_candidat} enregistrée !")
            st.balloons()
        else:
            st.error("Veuillez renseigner le nom, le prénom et la décision avant d'enregistrer.")

def page_dashboard():
    """Page pour visualiser l'historique et les statistiques des évaluations."""

    st.title("📊 Tableau de Bord & Historique")
    st.markdown("Analysez les données de toutes les évaluations de candidats passées.")

    file_path = 'evaluations_candidats.csv'
    df = load_data(file_path)

    if df.empty:
        st.warning("Aucune donnée d'évaluation n'a été trouvée. Veuillez d'abord évaluer un candidat.")
        return

    # --- KPIs ---
    st.header("Indicateurs Clés")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nombre de Candidats Évalués", len(df))
    col2.metric("Score Final Moyen", f"{df['Score Final'].mean():.2f} / 5")

    # Pourcentage de décisions "À recruter"
    try:
        decision_counts = df['Décision'].value_counts(normalize=True)
        pct_a_recruter = decision_counts.get('À recruter', 0) * 100
    except KeyError:
        pct_a_recruter = 0
    col3.metric("Taux d'embauche", f"{pct_a_recruter:.1f}%")

    st.markdown("---")

    # --- Visualisations ---
    st.header("Analyse des Scores")

    # Graphique de comparaison des scores
    entretien_moy = df['Score Entretien'].mean()
    cognitif_moy = df['Score Cognitif'].mean()
    echantillon_moy = df['Score Échantillon'].mean()

    avg_scores_df = pd.DataFrame({
        'Catégorie': ['Score Entretien', 'Score Cognitif', 'Score Échantillon'],
        'Score Moyen': [entretien_moy, cognitif_moy, echantillon_moy]
    })
    st.bar_chart(avg_scores_df.set_index('Catégorie'))
    st.caption("Comparaison des scores moyens par catégorie d'évaluation.")

    st.markdown("---")

    # --- Historique des Données ---
    st.header("Historique des Évaluations")
    st.dataframe(df, use_container_width=True)
    st.caption("Vous pouvez trier et explorer les données en cliquant sur les en-têtes de colonnes.")

# --- Structure de Navigation Principale ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Choisissez une page", ["📝 Évaluation du Candidat", "📊 Tableau de Bord & Historique"])

if page == "📝 Évaluation du Candidat":
    page_evaluation()
elif page == "📊 Tableau de Bord & Historique":
    page_dashboard()