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

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="glass-card">
        <h3>⚡ Vitesse Absolue</h3>
        <p>Analyse de CV en quelques millisecondes. Matching intelligent ultra-précis.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="glass-card">
        <h3>🧠 Intelligence Pure</h3>
        <p>Compréhension sémantique profonde des compétences et du potentiel des candidats.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="glass-card">
        <h3>✨ Expérience Premium</h3>
        <p>Interface intuitive conçue pour les recruteurs modernes et visionnaires.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Interactive Section
st.subheader("💡 Explorez les Possibilités")
option = st.selectbox("Quelle fonctionnalité souhaitez-vous tester ?", ["Analyse Prédictive", "Optimisation de Pipeline", "Génération de Fiches de Poste"])

if st.button("Lancer la Simulation"):
    with st.status("Initialisation des protocoles Antigravity...", expanded=True) as status:
        st.write("Connexion au noyau IA...")
        time.sleep(1)
        st.write("Analyse des vecteurs de performance...")
        time.sleep(1)
        st.write("Génération des insights stratégiques...")
        time.sleep(1)
        status.update(label="Simulation terminée avec succès !", state="complete", expanded=False)
    
    st.balloons()
    st.success(f"Simulation {option} réussie. Les résultats sont optimisés pour votre environnement.")

st.markdown("""
<div style="margin-top: 5rem; text-align: center; opacity: 0.5; font-size: 0.8rem;">
    Powered by Antigravity AI Engine v2.0 • TG-Hire Ecosystem
</div>
""", unsafe_allow_html=True)
