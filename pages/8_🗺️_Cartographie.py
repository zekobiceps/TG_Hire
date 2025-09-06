import streamlit as st
from utils import *
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🗺️ Cartographie de Sourcing")

st.title("🗺️ Cartographie de Sourcing")

with st.expander("📋 Définition et Utilité"):
    st.markdown("""
    **Définition**
    
    La cartographie du sourcing est un outil d'aide à la décision qui permet de classer les postes à pourvoir selon deux critères :
    
    1. **La disponibilité du marché** (abondant ou pénurique)
    2. **La criticité du poste** pour nous (non vital ou vital)
    
    Ce croisement donne une matrice 2×2 qui oriente immédiatement la stratégie de recrutement la plus adaptée.
    
    **Utilité principale**
    
    - Structurer le recrutement : adapter la stratégie selon le contexte marché/criticité
    - Gagner du temps : savoir s'il faut privilégier le volume ou la précision
    - Optimiser les ressources : allouer l'effort et les bons canaux au bon type de poste
    - Aider à la priorisation : identifier les postes stratégiques
    - Améliorer la qualité du pipeline : mieux cibler les candidats
    
    **Exemple concret**
    
    - Animateur HSE (non vital / marché abondant) → annonces et ATS, objectif = volume
    - Directeur projets (vital / marché pénurique) → chasse et réseau, objectif = qualité et patience
    """)

st.header("Matrice 2×2 de Sourcing")

# Interface pour modifier la matrice
col1, col2 = st.columns(2)

with col1:
    st.subheader("Axes de la matrice")
    st.info("Modifiez les intitulés des axes si nécessaire")
    
    axe_vertical_haut = st.text_input("Axe vertical (haut):", value="Postes non vitaux")
    axe_vertical_bas = st.text_input("Axe vertical (bas):", value="Postes vitaux")
    axe_horizontal_gauche = st.text_input("Axe horizontal (gauche):", value="Marché abondant")
    axe_horizontal_droite = st.text_input("Axe horizontal (droite):", value="Marché pénurique")

with col2:
    st.subheader("Ajouter un poste")
    nouveau_poste = st.text_input("Nouveau poste:", placeholder="Ex: Data Analyst")
    quadrant_choisi = st.selectbox("Quadrant:", list(SOURCING_MATRIX_DATA.keys()))
    
    if st.button("➕ Ajouter ce poste") and nouveau_poste:
        if quadrant_choisi in st.session_state.sourcing_matrix_data:
            st.session_state.sourcing_matrix_data[quadrant_choisi]["exemples"].append(nouveau_poste)
            st.success(f"Poste ajouté au quadrant: {quadrant_choisi}")
            st.rerun()

# Affichage de la matrice
st.markdown("---")
st.subheader("Matrice de Sourcing")

quadrants = list(st.session_state.sourcing_matrix_data.keys())
cols = st.columns(2)

for i, quadrant in enumerate(quadrants):
    with cols[i % 2]:
        with st.expander(f"**{quadrant}**", expanded=True):
            data = st.session_state.sourcing_matrix_data[quadrant]
            
            st.markdown("**Exemples de postes:**")
            for j, poste in enumerate(data["exemples"]):
                col_post, col_del = st.columns([4, 1])
                with col_post:
                    st.write(f"- {poste}")
                with col_del:
                    if st.button("🗑️", key=f"del_{quadrant}_{j}"):
                        st.session_state.sourcing_matrix_data[quadrant]["exemples"].pop(j)
                        st.rerun()
            
            st.markdown(f"**Canaux de sourcing:** {data['canaux']}")
            st.markdown(f"**Objectif prioritaire:** {data['objectif']}")

# Option pour réinitialiser la matrice
if st.button("🔄 Réinitialiser la matrice aux valeurs par défaut"):
    st.session_state.sourcing_matrix_data = SOURCING_MATRIX_DATA
    st.success("Matrice réinitialisée!")
    st.rerun()