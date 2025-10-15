import streamlit as st
import pandas as pd
import os
import datetime
import json
from utils import generate_ai_question

# Configuration de la page
st.set_page_config(page_title="HR Eval Pro - Système d'Évaluation", layout="wide", page_icon="🚀")

# Fonctions de base
def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

def save_data(df, file_path):
    df.to_csv(file_path, index=False)

def load_test_templates():
    template_file = 'test_templates.json'
    if os.path.exists(template_file):
        with open(template_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_test_templates(templates):
    template_file = 'test_templates.json'
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)

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

# Initialisation des variables de session
if 'current_test_template' not in st.session_state:
    st.session_state.current_test_template = None
if 'evaluation_step' not in st.session_state:
    st.session_state.evaluation_step = 0
if 'evaluation_data' not in st.session_state:
    st.session_state.evaluation_data = {}

# Titre principal
st.title("👥 Système d'Évaluation des Candidats - HR Eval Pro")

# Navigation par onglets principaux
main_tabs = st.tabs([
    "📁 Gestion",
    "⚙️ Configuration", 
    "📝 Évaluation",
    "📚 Bibliothèque",
    "📊 Dashboard"
])

# Onglet Gestion
with main_tabs[0]:
    st.header("📁 Gestion des Tests d'Évaluation")

    col_left, col_right = st.columns([2, 2])

    # Bloc "Créer un test"
    with col_left:
        st.subheader("🆕 Créer un Nouveau Test")

        # Informations de base du test
        col1, col2 = st.columns(2)
        with col1:
            test_name = st.text_input("Nom du test", key="test_name")
        with col2:
            test_category = st.selectbox("Catégorie", ["Technique", "Commercial", "Management", "Support", "Autre"], key="test_category")

        col3, col4 = st.columns(2)
        with col3:
            test_poste = st.text_input("Poste associé", key="test_poste")

        if st.button("💾 Créer le test", type="primary"):
            if test_name:
                templates = load_test_templates()
                templates[test_name] = {
                                   "nom": test_name,
                    "categorie": test_category,
                    "poste": test_poste,
                    "date_creation": datetime.date.today().strftime("%Y-%m-%d"),
                    "questions_entretien": [],
                    "questions_cognitif": [],
                    "taches_echantillon": []
                }
                save_test_templates(templates)
                st.success(f"✅ Test '{test_name}' créé avec succès !")
                st.session_state.current_test_template = test_name
            else:
                st.error("Veuillez saisir un nom pour le test.")

    # Bloc "Chercher un test"
    with col_right:
        st.subheader("🔍 Chercher un Test Existants")

        templates = load_test_templates()

        if templates:
            # Recherche par nom
            search_term = st.text_input("Rechercher par nom", key="search_test")

            # Filtrage par catégorie
            categories = ["Toutes"] + list(set([t.get("categorie", "Autre") for t in templates.values()]))
            filter_category = st.selectbox("Filtrer par catégorie", categories, key="filter_category")

            # Affichage des tests filtrés
            filtered_tests = {}
            for name, template in templates.items():
                if search_term.lower() in name.lower():
                    if filter_category == "Toutes" or template.get("categorie", "Autre") == filter_category:
                        filtered_tests[name] = template

            if filtered_tests:
                st.subheader("Tests trouvés :")
                for name, template in filtered_tests.items():
                    with st.expander(f"📋 {name} - {template.get('categorie', 'Autre')}"):
                        # affiche uniquement les informations essentielles
                        st.write(f"**Poste :** {template.get('poste', 'N/A')}")
                        st.write(f"**Créé le :** {template.get('date_creation', 'N/A')}")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"✏️ Modifier", key=f"edit_{name}"):
                                st.session_state.current_test_template = name
                                st.rerun()
                        with col_b:
                            if st.button(f"🗑️ Supprimer", key=f"delete_{name}"):
                                del templates[name]
                                save_test_templates(templates)
                                st.success(f"Test '{name}' supprimé !")
                                st.rerun()
            else:
                st.info("Aucun test trouvé avec ces critères.")
        else:
            st.info("Aucun test n'a encore été créé. Créez votre premier test dans la colonne de gauche.")

# Onglet Configuration
with main_tabs[1]:
    st.header("⚙️ Configuration des Tests")

    # Chargement du test courant (soit via Gestion -> Modifier, soit créer)
    templates = load_test_templates()
    if not templates:
        st.warning("Aucun test n'existe encore. Créez d'abord un test dans l'onglet Gestion.")
        template = None
    else:
        if st.session_state.get('current_test_template'):
            sel_name = st.session_state.current_test_template
            template = templates.get(sel_name)
            if not template:
                st.error(f"Le test '{sel_name}' n'existe plus. Sélectionnez ou créez un autre test dans Gestion.")
                template = None
        else:
            st.info("Créez un test dans 'Gestion' ou utilisez la recherche puis '✏️ Modifier' pour charger un test ici.")
            template = None

    # Affiche les sous-onglets uniquement si un template est chargé
    if template:
        config_tabs = st.tabs(["⚙️ Entretien Structuré", "⚙️ Test Cognitif", "⚙️ Échantillon de Travail"])

        # --- Configuration Entretien Structuré ---
        with config_tabs[0]:
            st.subheader("Configuration de l'Entretien Structuré (40%)")

            # Nombre de questions
            nb_questions = st.number_input("Nombre de questions", min_value=1, max_value=10,
                                         value=len(template.get("questions_entretien", [])) or 3,
                                         key="nb_questions_config")

            questions_entretien = []
            for i in range(nb_questions):
                # layout: main column + small AI chat column on right
                c_main, c_ai = st.columns([4,1])
                with c_main:
                    with st.expander(f"Question {i+1}", expanded=(i==0)):
                        existing_question = template.get("questions_entretien", []) if template else []
                        question_data = existing_question[i] if i < len(existing_question) else {"texte": get_default_question_entretien(i), "poids": 3}

                        q_col, s_col = st.columns([4,1])
                        with q_col:
                            question_text = st.text_area(f"Texte de la question {i+1}", height=80,
                                                       value=st.session_state.get(f"q_entretien_config_{i}", question_data["texte"]),
                                                       key=f"q_entretien_config_{i}")
                        with s_col:
                            poids_question = st.slider(f"Poids", 1, 5,
                                                     value=st.session_state.get(f"poids_entretien_config_{i}", question_data["poids"]),
                                                     key=f"poids_entretien_config_{i}")
                        questions_entretien.append({"texte": st.session_state.get(f"q_entretien_config_{i}"), "poids": poids_question})

                        # AI prompt + generate button placed inside the expander (compact)
                        ai_col, ai_btn = st.columns([4,1])
                        with ai_col:
                            ai_prompt = st.text_input(f"Prompt IA {i+1}", key=f"ai_entretien_prompt_{i}", placeholder="Ex: question sourcing")
                        with ai_btn:
                            if st.button(f"💡 Générer", key=f"gen_entretien_ai_{i}"):
                                if ai_prompt:
                                    try:
                                        resp = generate_ai_question(ai_prompt, concise=True)
                                        if 'Question:' in resp:
                                            q = resp.split('Question:')[-1].split('\n')[0].strip()
                                        else:
                                            q = resp.split('\n')[0].strip()
                                        # injecte directement dans la zone de texte
                                        st.session_state[f"q_entretien_config_{i}"] = q
                                        st.session_state[f'ai_generated_entretien_{i}'] = q
                                        st.success("Question générée et insérée")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erreur IA: {e}")

            if st.button("💾 Sauvegarder Configuration Entretien", key="save_entretien_config"):
                template["questions_entretien"] = questions_entretien
                save_test_templates(templates)
                st.success("Configuration de l'entretien sauvegardée !")

        # --- Configuration Test Cognitif ---
        with config_tabs[1]:
            st.subheader("Configuration du Test Cognitif (20%)")

            # possibilité d'ajouter plusieurs questions cognitives
            nb_cog = st.number_input("Nombre de questions cognitives", min_value=1, max_value=10,
                                     value=len(template.get("questions_cognitif", [])) or 1,
                                     key="nb_cognitif_config")

            questions_cognitif = []
            for i in range(nb_cog):
                c_main, c_ai = st.columns([4,1])
                with c_main:
                    with st.expander(f"Question cognitive {i+1}", expanded=(i==0)):
                        existing = template.get("questions_cognitif", []) if template else []
                        qdata = existing[i] if i < len(existing) else {"consigne": "", "poids": 3}
                        q_col, s_col = st.columns([4,1])
                        with q_col:
                            consigne = st.text_area(f"Consigne {i+1}", height=80, value=st.session_state.get(f"q_cog_{i}", qdata.get("consigne","")), key=f"q_cog_{i}")
                        with s_col:
                            poids = st.slider(f"Évaluation (1-5)", 1,5, value=st.session_state.get(f"poids_cog_{i}", qdata.get("poids",3)), key=f"poids_cog_{i}")
                        questions_cognitif.append({"consigne": st.session_state.get(f"q_cog_{i}"), "poids": poids})

                        # AI prompt + generate button inside the expander (match Entretien layout)
                        ai_col, ai_btn = st.columns([4,1])
                        with ai_col:
                            ai_prompt = st.text_input(f"Prompt IA Cog {i+1}", key=f"ai_cog_prompt_{i}", placeholder="Ex: générer un cas logique")
                        with ai_btn:
                            if st.button(f"💡 Générer", key=f"gen_cog_ai_{i}"):
                                if ai_prompt:
                                    try:
                                        resp = generate_ai_question(ai_prompt, concise=True)
                                        if 'Question:' in resp:
                                            q = resp.split('Question:')[-1].split('\n')[0].strip()
                                        else:
                                            q = resp.split('\n')[0].strip()
                                        # insère directement dans la case de la consigne
                                        st.session_state[f"q_cog_{i}"] = q
                                        st.session_state[f'ai_generated_cog_{i}'] = q
                                        st.success("Question cognitive générée et insérée")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erreur IA: {e}")

            if st.button("💾 Sauvegarder Configuration Cognitif", key="save_cognitif_config"):
                template["questions_cognitif"] = questions_cognitif
                save_test_templates(templates)
                st.success("Configuration du test cognitif sauvegardée !")

        # --- Configuration Échantillon de Travail ---
        with config_tabs[2]:
            st.subheader("Configuration de l'Échantillon de Travail (40%)")

            # Nombre de tâches
            nb_taches = st.number_input("Nombre de tâches", min_value=1, max_value=5,
                                      value=len(template.get("taches_echantillon", [])) or 2,
                                      key="nb_taches_config")

            taches_echantillon = []
            for i in range(nb_taches):
                c_main, c_ai = st.columns([4,1])
                with c_main:
                    with st.expander(f"Tâche {i+1}", expanded=(i==0)):
                        existing_tache = template.get("taches_echantillon", [])
                        tache_data = existing_tache[i] if i < len(existing_tache) else {"texte": get_default_tache(i), "poids": 3}

                        tache_text = st.text_area(f"Consigne de la tâche {i+1}", height=80,
                                                value=tache_data["texte"],
                                                key=f"tache_config_{i}")
                        poids_tache = st.slider(f"Poids (1-5) tâche {i+1}", 1, 5,
                                              value=tache_data["poids"],
                                              key=f"poids_tache_config_{i}")
                        taches_echantillon.append({"texte": tache_text, "poids": poids_tache})

                        # AI prompt + generate button inside the expander
                        ai_col, ai_btn = st.columns([4,1])
                        with ai_col:
                            ai_prompt = st.text_input(f"Prompt IA Tâche {i+1}", key=f"ai_task_prompt_{i}", placeholder="Ex: tâche sourcing")
                        with ai_btn:
                            if st.button(f"💡 Générer", key=f"gen_task_ai_{i}"):
                                if ai_prompt:
                                    try:
                                        resp = generate_ai_question(ai_prompt, concise=True)
                                        if 'Question:' in resp:
                                            q = resp.split('Question:')[-1].split('\n')[0].strip()
                                        else:
                                            q = resp.split('\n')[0].strip()
                                        st.session_state[f"tache_config_{i}"] = q
                                        st.session_state[f'ai_generated_task_{i}'] = q
                                        st.success("Tâche générée et insérée")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erreur IA: {e}")

            if st.button("💾 Sauvegarder Configuration Échantillon", key="save_echantillon_config"):
                template["taches_echantillon"] = taches_echantillon
                save_test_templates(templates)
                st.success("Configuration de l'échantillon de travail sauvegardée !")
    else:
        st.warning("Aucun test n'existe encore. Créez d'abord un test dans l'onglet Gestion.")

# Onglet Évaluation
with main_tabs[2]:
    st.header("📝 Évaluation du Candidat")

    # Sélection du test à utiliser (on utilise le template chargé depuis Gestion)
    template = load_test_templates().get(st.session_state.get('current_test_template')) if st.session_state.get('current_test_template') else None
    if template:
        # Informations du candidat
        st.subheader("Informations du Candidat")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            nom_prenom = st.text_input("Nom et Prénom du candidat", key="nom_prenom_eval")
        with col2:
            poste_candidat = st.text_input("Poste candidaté", key="poste_candidat_eval")
        with col3:
            affectation = st.text_input("Affectation", key="affectation_eval")
        with col4:
            date_entretien = st.date_input("Date de l'entretien", datetime.date.today(), key="date_entretien_eval")

        # separation line between candidate info and evaluation steps
        st.markdown("---")

        # Étapes d'évaluation
        evaluation_steps = ["1️⃣ Entretien Structuré", "2️⃣ Test Cognitif", "3️⃣ Échantillon de Travail", "4️⃣ Synthèse & Décision"]

        # Navigation entre étapes (full width)
        col_prev, col_current, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.session_state.evaluation_step > 0:
                if st.button("⬅️ Précédent", key="prev_step"):
                    st.session_state.evaluation_step -= 1
                    st.rerun()

        with col_current:
            current_step_name = evaluation_steps[st.session_state.evaluation_step]
            st.markdown(f"### {current_step_name}")

        with col_next:
            if st.session_state.evaluation_step < len(evaluation_steps) - 1:
                if st.button("Suivant ➡️", key="next_step"):
                    st.session_state.evaluation_step += 1
                    st.rerun()

        # Contenu selon l'étape
        if st.session_state.evaluation_step == 0:  # Entretien Structuré
            st.subheader("Entretien Structuré")
            questions_entretien = template.get("questions_entretien", [])

            if questions_entretien:
                for i, question in enumerate(questions_entretien):
                    st.markdown(f"**Question {i+1} :** {question['texte']}")
                    notes_q = st.text_area(f"Notes Question {i+1} :", height=100, key=f"notes_q_eval_{i}")
                    note_q = st.slider(f"Note Question {i+1}", 1, 5, 3, key=f"note_q_eval_{i}")
                    st.session_state.evaluation_data[f"entretien_q{i}"] = {"notes": notes_q, "note": note_q}
            else:
                st.warning("Aucune question d'entretien configurée pour ce test.")

        elif st.session_state.evaluation_step == 1:  # Test Cognitif
            st.subheader("Test Cognitif")
            questions_cognitif = template.get("questions_cognitif", [])
            if questions_cognitif:
                for i, q in enumerate(questions_cognitif):
                    st.markdown(f"**Question cognitive {i+1} :** {q.get('consigne','')}")
                    col_q, col_s = st.columns([4,1])
                    with col_q:
                        reponse = st.text_area(f"Réponse {i+1}", height=120, key=f"reponse_cog_{i}")
                    with col_s:
                        note = st.slider(f"Éval (1-5)", 1,5,3, key=f"note_cog_{i}")
                    st.session_state.evaluation_data[f"cognitif_q{i}"] = {"reponse": reponse, "note": note}
            else:
                st.warning("Aucune question cognitive configurée pour ce test.")

        elif st.session_state.evaluation_step == 2:  # Échantillon de Travail
            st.subheader("Échantillon de Travail")
            taches_echantillon = template.get("taches_echantillon", [])

            if taches_echantillon:
                for i, tache in enumerate(taches_echantillon):
                    st.markdown(f"**Tâche {i+1} :** {tache['texte']}")
                    reponse_tache = st.text_area(f"Réponse du candidat à la tâche {i+1} :", height=100, key=f"reponse_tache_eval_{i}")
                    note_tache = st.slider(f"Note Tâche {i+1}", 1, 5, 3, key=f"note_tache_eval_{i}")
                    st.session_state.evaluation_data[f"echantillon_t{i}"] = {"reponse": reponse_tache, "note": note_tache}
            else:
                st.warning("Aucune tâche d'échantillon configurée pour ce test.")

        elif st.session_state.evaluation_step == 3:  # Synthèse & Décision
            st.subheader("Synthèse et Décision Finale")

            # Calcul des scores
            questions_entretien = template.get("questions_entretien", [])
            taches_echantillon = template.get("taches_echantillon", [])

            # --- Normalisation des poids (échelle 1-5 en pourcentage) ---
            def normalize_weights(items):
                # items is list of dicts with 'poids' keys
                poids = [it.get('poids', 3) for it in items]
                total = sum(poids) if sum(poids) > 0 else len(poids)
                return [p / total for p in poids]

            # Score entretien (moyenne pondérée, les poids sont normalisés)
            score_entretien = 0
            if questions_entretien:
                normalized = normalize_weights(questions_entretien)
                for i, question in enumerate(questions_entretien):
                    eval_data = st.session_state.evaluation_data.get(f"entretien_q{i}", {"note": 3})
                    score_entretien += eval_data["note"] * normalized[i]

            # Score cognitif (moyenne pondérée si plusieurs questions)
            score_cognitif = 0
            questions_cognitif = template.get("questions_cognitif", [])
            if questions_cognitif:
                normalized_c = normalize_weights(questions_cognitif)
                for i, _ in enumerate(questions_cognitif):
                    eval_data = st.session_state.evaluation_data.get(f"cognitif_q{i}", {"note": 3})
                    score_cognitif += eval_data["note"] * normalized_c[i]
            else:
                score_cognitif = 3

            # Score échantillon (moyenne pondérée)
            score_echantillon = 0
            if taches_echantillon:
                normalized_t = normalize_weights(taches_echantillon)
                for i, tache in enumerate(taches_echantillon):
                    eval_data = st.session_state.evaluation_data.get(f"echantillon_t{i}", {"note": 3})
                    score_echantillon += eval_data["note"] * normalized_t[i]

            # Score final pondéré: entretien 40%, cognitif 20%, échantillon 40%
            score_final = (score_entretien * 0.4) + (score_cognitif * 0.2) + (score_echantillon * 0.4)

            st.subheader(f"Score Final Pondéré : {score_final:.2f} / 5.0")
            st.progress(score_final / 5)

            # Avis du manager et du recruteur
            col_manager, col_recruteur = st.columns(2)
            with col_manager:
                st.subheader("👔 Avis du Manager")
                avis_manager = st.text_area("Commentaires du manager", height=100, key="avis_manager")
                decision_manager = st.selectbox("Décision du manager",
                                              ["", "À recruter", "À recruter (avec réserves)", "Ne pas recruter"],
                                              key="decision_manager")

            with col_recruteur:
                st.subheader("🎯 Avis du Recruteur")
                avis_recruteur = st.text_area("Commentaires du recruteur", height=100, key="avis_recruteur")
                decision_recruteur = st.selectbox("Décision du recruteur",
                                                ["", "À recruter", "À recruter (avec réserves)", "Ne pas recruter"],
                                                key="decision_recruteur")

            points_forts = st.text_area("Points forts observés", height=100, key="points_forts_final")
            axes_amelioration = st.text_area("Axes d'amélioration potentiels", height=100, key="axes_amelioration_final")

            if st.button("💾 Finaliser l'évaluation", type="primary"):
                if nom_prenom and poste_candidat and decision_manager and decision_recruteur:
                    file_path = 'evaluations_candidats.csv'
                    df_existing = load_data(file_path)

                    new_data = {
                        'Date': [date_entretien.strftime("%Y-%m-%d")],
                        'Nom et Prénom': [nom_prenom],
                        'Poste': [poste_candidat],
                        'Affectation': [affectation],
                        'Test Utilisé': [st.session_state.get('current_test_template')],
                        'Score Final': [round(score_final, 2)],
                        'Score Entretien': [round(score_entretien, 2)],
                        'Score Cognitif': [round(score_cognitif, 2)],
                        'Score Échantillon': [round(score_echantillon, 2)],
                        'Décision Manager': [decision_manager],
                        'Décision Recruteur': [decision_recruteur],
                        'Avis Manager': [avis_manager],
                        'Avis Recruteur': [avis_recruteur],
                        'Points Forts': [points_forts],
                        'Axes Amélioration': [axes_amelioration]
                    }
                    df_new = pd.DataFrame(new_data)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)

                    save_data(df_combined, file_path)
                    st.success(f"Évaluation de {nom_prenom} finalisée et sauvegardée !")
                    st.balloons()

                    # Reset pour nouvelle évaluation
                    st.session_state.evaluation_step = 0
                    st.session_state.evaluation_data = {}
                else:
                    st.error("Veuillez renseigner toutes les informations obligatoires et les décisions.")
    else:
        st.warning("Aucun test n'existe encore. Créez d'abord un test dans l'onglet Gestion.")

# Onglet Bibliothèque
with main_tabs[3]:
    st.header("📚 Bibliothèque des Tests - Historique")
    st.markdown("Consultez l'historique de toutes les évaluations de candidats enregistrées localement.")

    file_path = 'evaluations_candidats.csv'
    df = load_data(file_path)

    if df.empty:
        st.warning("Aucune donnée d'évaluation n'a été trouvée. Veuillez d'abord évaluer un candidat dans l'onglet Évaluation.")
    else:
        # --- KPIs ---
        st.header("Indicateurs Clés")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nombre de Candidats Évalués", len(df))
        col2.metric("Score Final Moyen", f"{df['Score Final'].mean():.2f} / 5")
        
        # Pourcentage de décisions "À recruter"
        try:
            decision_counts = df['Décision Manager'].value_counts(normalize=True)
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
            )

# Onglet Dashboard
with main_tabs[4]:
    st.header("📊 Dashboard & Statistiques Avancées")

    file_path = 'evaluations_candidats.csv'
    df = load_data(file_path)

    if df.empty:
        st.warning("Aucune donnée d'évaluation n'a été trouvée.")
    else:
        # KPIs principaux
        st.subheader("Indicateurs Clés de Performance")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Nombre de Candidats Évalués", len(df))
        col2.metric("Score Final Moyen", f"{df['Score Final'].mean():.2f} / 5" if 'Score Final' in df.columns else "N/A")
        col3.metric("Taux d'Embauche (Manager)", f"{(df['Décision Manager'] == 'À recruter').mean() * 100:.1f}%" if 'Décision Manager' in df.columns else "N/A")
        col4.metric("Taux d'Embauche (Recruteur)", f"{(df['Décision Recruteur'] == 'À recruter').mean() * 100:.1f}%" if 'Décision Recruteur' in df.columns else "N/A")

        st.markdown("---")

        # Graphiques avancés
        st.subheader("Analyse Détaillée des Performances")

        if len(df) > 0:
            # Graphique des scores moyens
            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Scores par Catégorie")
                if all(col in df.columns for col in ['Score Entretien', 'Score Cognitif', 'Score Échantillon']):
                    scores_df = pd.DataFrame({
                        'Catégorie': ['Entretien', 'Cognitif', 'Échantillon'],
                        'Score Moyen': [
                            df['Score Entretien'].mean(),
                            df['Score Cognitif'].mean(),
                            df['Score Échantillon'].mean()
                        ]
                    })
                    st.bar_chart(scores_df.set_index('Catégorie'))

            with col_b:
                st.subheader("Décisions par Évaluateur")
                if 'Décision Manager' in df.columns and 'Décision Recruteur' in df.columns:
                    decisions_df = pd.DataFrame({
                        'Décision': ['À Recruter', 'Réserves', 'Refuser'],
                        'Manager': [
                            (df['Décision Manager'] == 'À recruter').sum(),
                            (df['Décision Manager'] == 'À recruter (avec réserves)').sum(),
                            (df['Décision Manager'] == 'Ne pas recruter').sum()
                        ],
                        'Recruteur': [
                            (df['Décision Recruteur'] == 'À recruter').sum(),
                            (df['Décision Recruteur'] == 'À recruter (avec réserves)').sum(),
                            (df['Décision Recruteur'] == 'Ne pas recruter').sum()
                        ]
                    })
                    st.bar_chart(decisions_df.set_index('Décision'))

        # Statistiques détaillées
        st.subheader("Statistiques Détaillées")
        if len(df) > 0:
            st.dataframe(df.describe(), use_container_width=True)

        # Analyse par test utilisé
        if 'Test Utilisé' in df.columns:
            st.subheader("Analyse par Test Utilisé")
            test_stats = df.groupby('Test Utilisé').agg({
                'Score Final': ['count', 'mean'],
                'Score Entretien': 'mean',
                'Score Cognitif': 'mean',
                'Score Échantillon': 'mean'
            }).round(2)
            st.dataframe(test_stats, use_container_width=True)
