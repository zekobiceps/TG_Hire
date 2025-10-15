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

def get_default_question_entretien(index):
    """Retourne les questions par défaut pour l'entretien structuré."""
    questions = [
        "Parlez-moi d'un objectif de recrutement difficile que vous avez eu. Quelle était votre stratégie pour l'atteindre et quel a été le résultat ?",
        "Décrivez une situation où un manager opérationnel n'était pas d'accord avec votre sélection. Comment avez-vous argumenté et géré la situation ?",
        "Imaginez : 3 postes urgents à pourvoir pour 3 managers différents qui attendent un retour rapide. Comment organisez-vous votre semaine ?"
    ]
    return questions[index] if index < len(questions) else ""

def get_default_tache(index):
    """Retourne les tâches par défaut pour l'échantillon de travail."""
    taches = [
        "Rédigez un court e-mail d'approche directe sur LinkedIn pour un candidat passif.",
        "Donnez la requête booléenne pour trouver un 'Développeur Python' avec 'Django' mais sans 'PHP'."
    ]
    return taches[index] if index < len(taches) else ""

# --- Définition des Pages de l'Application ---

def page_evaluation():
    """Page pour saisir l'évaluation d'un nouveau candidat."""

    st.title("📝 Évaluation du Candidat")
    st.markdown("Remplissez ce formulaire structuré pour évaluer le candidat sur les compétences clés du poste.")

    # --- Section 1: Informations Générales ---
    st.header("1. Informations sur le Candidat")

    # Informations principales sur une ligne
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nom_prenom = st.text_input("Nom et Prénom du candidat")
    with col2:
        poste_candidat = st.text_input("Poste candidaté")
    with col3:
        affectation = st.text_input("Affectation souhaitée")
    with col4:
        date_entretien = st.date_input("Date de l'entretien", datetime.date.today())

    st.markdown("---")

    # --- Configuration des Questions (Paramétrage) ---
    st.header("2. Configuration des Questions")

    # Onglets pour paramétrer chaque section
    config_tab1, config_tab2, config_tab3 = st.tabs(["⚙️ Entretien Structuré", "⚙️ Test Cognitif", "⚙️ Échantillon de Travail"])

    # Variables pour stocker les questions configurées
    questions_entretien = []
    question_cognitif = ""
    taches_echantillon = []

    with config_tab1:
        st.subheader("Questions d'Entretien Structuré (40%)")
        st.markdown("Ajoutez et configurez les questions comportementales pour l'entretien.")

        # Nombre de questions
        nb_questions_entretien = st.number_input("Nombre de questions", min_value=1, max_value=10, value=3, key="nb_entretien")

        for i in range(nb_questions_entretien):
            with st.expander(f"Question {i+1}", expanded=(i==0)):
                question_text = st.text_area(f"Texte de la question {i+1}", height=80,
                                           value=get_default_question_entretien(i),
                                           key=f"q_entretien_{i}")
                poids_question = st.slider(f"Poids de la question {i+1} (%)", 0, 100, 33, key=f"poids_entretien_{i}")
                questions_entretien.append({"texte": question_text, "poids": poids_question})

    with config_tab2:
        st.subheader("Test Cognitif (20%)")
        st.markdown("Configurez l'exercice cognitif.")
        question_cognitif = st.text_area("Consigne du test cognitif", height=100,
                                       value="Consigne : Vous recevez 5 CV pour un poste de 'Chef de Projet'. Classez-les du plus pertinent au moins pertinent, en justifiant chaque choix en une phrase.",
                                       key="q_cognitif")

    with config_tab3:
        st.subheader("Échantillon de Travail (40%)")
        st.markdown("Ajoutez et configurez les tâches pratiques.")

        # Nombre de tâches
        nb_taches = st.number_input("Nombre de tâches", min_value=1, max_value=5, value=2, key="nb_taches")

        for i in range(nb_taches):
            with st.expander(f"Tâche {i+1}", expanded=(i==0)):
                tache_text = st.text_area(f"Consigne de la tâche {i+1}", height=80,
                                        value=get_default_tache(i),
                                        key=f"tache_{i}")
                poids_tache = st.slider(f"Poids de la tâche {i+1} (%)", 0, 100, 50, key=f"poids_tache_{i}")
                taches_echantillon.append({"texte": tache_text, "poids": poids_tache})

    st.markdown("---")

    # --- Utilisation des onglets pour l'évaluation ---
    st.header("3. Évaluation du Candidat")
    eval_tab1, eval_tab2, eval_tab3 = st.tabs(["**Entretien Structuré**", "**Test Cognitif**", "**Échantillon de Travail**"])

    # Scores pour chaque section
    scores_entretien = []
    score_cognitif = 3
    scores_echantillon = []

    with eval_tab1:
        st.subheader("Entretien Structuré")
        total_poids_entretien = sum(q["poids"] for q in questions_entretien) if questions_entretien else 100

        for i, question in enumerate(questions_entretien):
            st.markdown(f"**Question {i+1} :** {question['texte']}")
            notes_q = st.text_area(f"Notes Question {i+1} :", height=100, key=f"notes_q{i}")
            note_q = st.slider(f"Note Question {i+1}", 1, 5, 3, key=f"note_q{i}")
            scores_entretien.append(note_q * question["poids"] / 100)

    with eval_tab2:
        st.subheader("Test Cognitif")
        st.info(question_cognitif)
        reponse_cognitif = st.text_area("Réponse et analyse du candidat :", height=150, key="reponse_cognitif_eval")
        score_cognitif = st.slider("Note Test Cognitif", 1, 5, 3, key="note_cognitif_eval")

    with eval_tab3:
        st.subheader("Échantillon de Travail")
        for i, tache in enumerate(taches_echantillon):
            st.markdown(f"**Tâche {i+1} :** {tache['texte']}")
            reponse_tache = st.text_area(f"Réponse du candidat à la tâche {i+1} :", height=100, key=f"reponse_tache{i}")
            note_tache = st.slider(f"Note Tâche {i+1}", 1, 5, 3, key=f"note_tache{i}")
            scores_echantillon.append(note_tache * tache["poids"] / 100)

    st.markdown("---")

    # --- Section de Synthèse et Décision ---
    st.header("Synthèse et Décision Finale")

    # Calcul des scores
    score_entretien_final = sum(scores_entretien) if scores_entretien else 3
    score_echantillon_final = sum(scores_echantillon) if scores_echantillon else 3
    score_final = (score_entretien_final * 0.4) + (score_cognitif * 0.2) + (score_echantillon_final * 0.4)

    st.subheader(f"Score Final Pondéré : {score_final:.2f} / 5.0")
    st.progress(score_final / 5)

    points_forts = st.text_area("Points forts observés", height=100)
    axes_amelioration = st.text_area("Axes d'amélioration potentiels", height=100)
    decision = st.selectbox("Décision", ["", "À recruter", "À recruter (avec réserves)", "Ne pas recruter"])

    if st.button("💾 Enregistrer l'évaluation", type="primary"):
        if nom_prenom and poste_candidat and decision:
            file_path = 'evaluations_candidats.csv'
            df_existing = load_data(file_path)

            new_data = {
                'Date': [date_entretien.strftime("%Y-%m-%d")],
                'Nom et Prénom': [nom_prenom],
                'Poste': [poste_candidat],
                'Affectation': [affectation],
                'Score Final': [round(score_final, 2)],
                'Décision': [decision],
                'Score Entretien': [round(score_entretien_final, 2)],
                'Score Cognitif': [round(score_cognitif, 2)],
                'Score Échantillon': [round(score_echantillon_final, 2)],
                'Points Forts': [points_forts],
                'Axes Amélioration': [axes_amelioration]
            }
            df_new = pd.DataFrame(new_data)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

            save_data(df_combined, file_path)
            st.success(f"Évaluation pour {nom_prenom} enregistrée !")
            st.balloons()
        else:
            st.error("Veuillez renseigner le nom/prénom, le poste et la décision avant d'enregistrer.")

def page_dashboard():
    """Page pour visualiser l'historique et les statistiques des évaluations."""

    st.title("� Bibliothèque des Tests - Historique")
    st.markdown("Consultez l'historique de toutes les évaluations de candidats enregistrées localement.")

    file_path = 'evaluations_candidats.csv'
    df = load_data(file_path)

    if df.empty:
        st.warning("Aucune donnée d'évaluation n'a été trouvée. Veuillez d'abord évaluer un candidat dans l'onglet Évaluation.")
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

    # Option d'export
    if st.button("📥 Exporter les données (CSV)"):
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Télécharger le fichier CSV",
            data=csv_data,
            file_name="historique_evaluations_candidats.csv",
            mime="text/csv"
        )# --- Structure de Navigation Principale ---
st.title("👥 Système d'Évaluation des Candidats - HR Eval Pro")

# Navigation par onglets dans la page principale
tab_eval, tab_bibliotheque = st.tabs(["📝 Évaluation du Candidat", "� Bibliothèque des Tests"])

with tab_eval:
    page_evaluation()

with tab_bibliotheque:
    page_dashboard()