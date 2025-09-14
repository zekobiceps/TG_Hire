import streamlit as st
import fitz
import requests
import json
import io
from docx import Document
import pandas as pd
import json5

# -------------------- FONCTIONS DE NETTOYAGE & API --------------------

def clean_json_string(text):
    """
    Supprime les backticks et le mot 'json' qui entourent un bloc de code JSON.
    """
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()

def get_deepseek_response(prompt):
    """Obtient une réponse du modèle DeepSeek AI."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ Clé API DeepSeek non trouvée dans st.secrets.")
        return "Erreur: Clé API manquante."

    url = "[https://api.deepseek.com/v1/chat/completions](https://api.deepseek.com/v1/chat/completions)"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    system_prompt = "Vous êtes un assistant d'analyse de documents RH. Votre objectif est d'analyser le contenu de documents (CV, fiches de poste, etc.), d'en extraire les informations clés, et de fournir une synthèse claire et structurée. Vos réponses doivent être professionnelles, précises et directement applicables au contexte du recrutement. Pour l'évaluation de CV, votre réponse doit être un objet JSON valide, sans fioritures."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": "deepseek-coder",
        "messages": messages,
        "stream": False,
        "max_tokens": 2000,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erreur API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erreur lors de l'appel API: {e}"

# -------------------- FONCTIONS DE MATCHING CORRIGÉES --------------------

def match_cv_to_job(cv_text, job_offer_text):
    prompt_for_json = f"""
    Compare the following CV and job offer. Extract all relevant information in a single JSON object.

    CV:
    {cv_text}

    Job Offer:
    {job_offer_text}

    Provide the JSON object with the following structure:
    {{
        "cv_summary": "A brief summary of the candidate's profile.",
        "job_summary": "A brief summary of the job offer.",
        "skills_match": {{
            "matched_skills": ["skill1", "skill2"],
            "missing_skills": ["skill3"]
        }},
        "experience_match": {{
            "matched_experience": "A description of how the candidate's experience matches the job requirements.",
            "unmatched_experience": "Any gaps or irrelevant experience."
        }},
        "overall_score": "An overall match score between 1 and 100."
    }}

    The response must contain ONLY the JSON object, no other text or explanation.
    """
    try:
        # Utiliser la fonction DeepSeek
        response_text = get_deepseek_response(prompt_for_json)
        
        # VÉRIFICATION: Si la réponse est une chaîne d'erreur, ne pas tenter de la décoder
        if response_text.startswith("Erreur"):
            st.error(f"❌ Erreur de l'API : {response_text}")
            return None
        
        # Nettoyer la réponse de l'IA et analyser la chaîne JSON propre
        cleaned_response = clean_json_string(response_text)
        match_result = json5.loads(cleaned_response)
        
        return match_result
    except json.JSONDecodeError as e:
        st.error(f"❌ Erreur lors de l'analyse du JSON : {e}")
        st.error("❌ L'évaluation de correspondance a échoué.")
        return None
    except Exception as e:
        st.error(f"❌ Une erreur inattendue est survenue : {e}")
        st.error("❌ L'évaluation de correspondance a échoué.")
        return None

# -------------------- LOGIQUE DE LA PAGE STREAMLIT --------------------

def render_pdf_analysis_page():
    """Affiche l'interface utilisateur pour l'analyse de PDF."""
    
    st.markdown(
        """
        <style>
        .st-emotion-cache-18j2gai { text-align: center; }
        .main-header { font-size: 2.5em; font-weight: bold; color: #1a1a1a; text-align: center; margin-bottom: 0; padding-bottom: 0; }
        .sub-header { font-size: 1.2em; color: #7f8c8d; text-align: center; margin-top: 0; }
        .upload-container { padding: 20px; border-radius: 10px; border: 2px dashed #bdc3c7; text-align: center; margin-bottom: 20px; }
        .stButton>button { color: white; background-color: #e74c3c; border-radius: 5px; padding: 10px 20px; font-size: 1em; border: none; cursor: pointer; width: 100%; }
        .stButton>button:hover { background-color: #c0392b; }
        .st-emotion-cache-1l8943x p { font-size: 1.1em; text-align: center; }
        .st-emotion-cache-1l8943x { border: none; }
        .st-emotion-cache-e8t53b { background-color: #ecf0f1; padding: 20px; border-radius: 10px; }
        .analysis-box { padding: 20px; background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); color: black; }
        </style>
        <h1 class="main-header">📄 Analyse de Document IA</h1>
        <p class="sub-header">
            Transforme instantanément n'importe quel PDF en un brief de recrutement structuré ou en une analyse de CV.
        </p>
        <hr/>
        """,
        unsafe_allow_html=True
    )
    
    with st.form(key="pdf_analysis_form"):
        st.subheader("1. Uploader votre document")
        uploaded_file = st.file_uploader(
            "Glissez & déposez votre fichier ici ou cliquez pour le parcourir",
            type=["pdf", "docx"],
            accept_multiple_files=False,
            key="uploaded_file"
        )
        
        st.subheader("2. Coller l'offre d'emploi (optionnel)")
        job_offer_text = st.text_area(
            "Coller le texte de l'offre d'emploi pour évaluer le matching du CV",
            height=250,
            key="job_offer_text"
        )

        submit_button = st.form_submit_button("🚀 Lancer l'analyse du document", type="primary")

    if uploaded_file is not None:
        st.success(f"✅ Fichier chargé : **{uploaded_file.name}**")

    if submit_button:
        if uploaded_file is not None:
            file_type = uploaded_file.type
            
            with st.spinner('⏳ Extraction du texte du document...'):
                text_content = ""
                if file_type == "application/pdf":
                    try:
                        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                            for page in doc:
                                text_content += page.get_text()
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction du PDF : {e}")
                        text_content = ""
                elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    try:
                        doc = Document(uploaded_file)
                        text_content = " ".join([p.text for p in doc.paragraphs])
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction du DOCX : {e}")
                        text_content = ""
            
            if text_content.strip():
                if job_offer_text.strip():
                    # --- FONCTIONNALITÉ: Matching CV ---
                    st.subheader("🎯 Analyse de Correspondance CV vs Offre d'Emploi")
                    with st.spinner('✨ Évaluation du matching en cours par l\'IA...'):
                        match_result = match_cv_to_job(text_content, job_offer_text)

                    if match_result:
                        overall_score = match_result.get("overall_score")
                        if overall_score is not None:
                            try:
                                # Tenter de convertir le score en int pour un affichage plus propre
                                score_int = int(overall_score)
                                st.markdown(
                                    f"""
                                    <h2 style='text-align: center;'>Score de Matching :</h2>
                                    <h1 style='text-align: center; color: #e74c3c; font-size: 4em;'>{score_int} %</h1>
                                    <hr/>
                                    """, 
                                    unsafe_allow_html=True
                                )
                            except ValueError:
                                # Si la conversion échoue, afficher la valeur brute
                                st.markdown(
                                    f"""
                                    <h2 style='text-align: center;'>Score de Matching :</h2>
                                    <h1 style='text-align: center; color: #e74c3c; font-size: 4em;'>{overall_score}</h1>
                                    <hr/>
                                    """, 
                                    unsafe_allow_html=True
                                )
                        
                        # Afficher le résumé et les correspondances
                        if match_result.get("cv_summary"):
                            st.markdown(f"**Résumé du CV :** {match_result['cv_summary']}")
                        if match_result.get("job_summary"):
                            st.markdown(f"**Résumé de l'offre :** {match_result['job_summary']}")
                        
                        st.markdown("### Compétences et Expérience")
                        
                        if match_result.get("skills_match"):
                            skills = match_result['skills_match']
                            if skills.get("matched_skills"):
                                st.success(f"✅ Compétences correspondantes : {', '.join(skills['matched_skills'])}")
                            if skills.get("missing_skills"):
                                st.warning(f"⚠️ Compétences manquantes : {', '.join(skills['missing_skills'])}")
                        
                        if match_result.get("experience_match"):
                            exp = match_result['experience_match']
                            if exp.get("matched_experience"):
                                st.success(f"✅ Expérience correspondante : {exp['matched_experience']}")
                            if exp.get("unmatched_experience"):
                                st.warning(f"⚠️ Expérience à améliorer : {exp['unmatched_experience']}")
                                
                        else:
                            st.warning("⚠️ L'IA n'a pas pu fournir de score. Veuillez vérifier les textes fournis.")
                    
                    else:
                        st.error("❌ L'évaluation de correspondance a échoué.")
                    
                else:
                    # --- ANCIENNE FONCTIONNALITÉ: Analyse simple de CV ---
                    st.subheader("💡 Résultat de l'analyse IA")
                    with st.spinner('✨ Analyse en cours par l\'IA...'):
                        analysis_prompt = f"Analyse le texte suivant extrait d'un document. Extrait les informations clés pour un brief de recrutement : l'intitulé du poste, les tâches principales, les compétences techniques requises, les soft skills, et l'expérience demandée. Présente les informations dans une liste structurée. Le texte est : {text_content}"
                        full_response = get_deepseek_response(analysis_prompt)
                    
                    st.markdown(f'<div class="analysis-box">{full_response}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ Le document est vide ou l'extraction a échoué.")
        else:
            st.warning("⚠️ Veuillez uploader un fichier pour lancer l'analyse.")

# Appel de la fonction pour afficher la page si ce fichier est le point d'entrée
if __name__ == "__main__":
    render_pdf_analysis_page()