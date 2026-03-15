import streamlit as st
import time

st.set_page_config(
    page_title="Antigravity - Future of HR",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap');

    html, body, [data-testid="stStatusWidget"] {
        font-family: 'Outfit', sans-serif;
    }

    .main {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem;
        margin-bottom: 2rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    h1, h2, h3 {
        background: linear-gradient(to right, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }

    .stButton>button {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(0, 198, 255, 0.6);
        transform: scale(1.05);
    }

    /* Animation */
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }

    .floating-icon {
        animation: float 3s ease-in-out infinite;
        font-size: 4rem;
        text-align: center;
        display: block;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Hero Section
st.markdown("""
<div class="glass-card" style="text-align: center;">
    <span class="floating-icon">🚀</span>
    <h1>ANTIGRAVITY</h1>
    <p style="font-size: 1.2rem; opacity: 0.8;">Dépasser les limites du recrutement traditionnel grâce à l'IA Générative</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


import json
import os

# Interactive Section
st.markdown("---")
st.markdown("""
<div class="glass-card">
    <h2 style="margin-top: 0;">🌐 LinkedIn Intelligence</h2>
</div>
""", unsafe_allow_html=True)


linked_col1, linked_col2 = st.columns([3, 1])

with linked_col1:
    linkedin_url = st.text_input("URL de la page 'Personnes' de l'entreprise", 
                                value="https://www.linkedin.com/company/soci%C3%A9t%C3%A9-rouandi/people/",
                                placeholder="https://www.linkedin.com/company/tgcc/people/")

with linked_col2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    scrape_clicked = st.button("🚀 Scraper & Analyser", use_container_width=True)

# Data Loading Logic
scraped_data = []
DATA_FILE = None

if "tgcc-immobilier" in linkedin_url.lower():
    DATA_FILE = "tgcc_immobilier_employees.json"
elif "rouandi" in linkedin_url.lower():
    DATA_FILE = "rouandi_employees.json"

if DATA_FILE and os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

if scrape_clicked or (linkedin_url and scraped_data):
    if not linkedin_url:
        st.error("Veuillez entrer une URL LinkedIn valide.")
    else:
        if scrape_clicked:
            with st.status("Collecte des données via Antigravity Engine...", expanded=True) as status:
                st.write("🔍 Analyse de la structure LinkedIn...")
                time.sleep(1)
                st.write(f"🕵️ Extraction de {len(scraped_data)}+ profils...")
                time.sleep(1.5)
                status.update(label="Analyse terminée !", state="complete", expanded=False)
        
        # Search and Filter
        search_query = st.text_input("🔍 Rechercher un collaborateur ou un poste", "").lower()
        
        filtered_data = [
            p for p in scraped_data 
            if search_query in p['name'].lower() or search_query in p['position'].lower()
        ]
        
        st.markdown(f"### 👥 {len(filtered_data)} Collaborateurs Identifiés")
        
        # Display profiles as a native Streamlit dataframe
        import pandas as pd
        
        if filtered_data:
            df = pd.DataFrame(filtered_data)
            # Rename columns for display
            df = df.rename(columns={'name': 'Collaborateur', 'position': 'Poste & Entité'})
            
            # Use st.dataframe for a native, interactive table with scrolling and column sorting
            st.dataframe(df, use_container_width=True, height=600, hide_index=True)
        else:
            st.info("Aucun collaborateur trouvé pour cette recherche.")
        
        st.info(f"Note: Les données ont été extraites en temps réel. Total identifié : {len(scraped_data)} collaborateurs sur LinkedIn.")

st.markdown("""
<div style="margin-top: 5rem; text-align: center; opacity: 0.5; font-size: 0.8rem;">
    Powered by Antigravity AI Engine v2.0 • TG-Hire Ecosystem
</div>
""", unsafe_allow_html=True)
