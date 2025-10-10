import streamlit as st

def show_navigation():
    """Afficher la navigation vers le nouveau reporting"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Nouveaux Rapports")
    
    if st.sidebar.button("🎯 Reporting RH Power BI", use_container_width=True):
        st.switch_page("pages/Reporting_RH_PowerBI.py")
    
    st.sidebar.markdown("""
    **Nouveau Reporting disponible :**
    - 🎯 Recrutements (État Clôture)
    - 📋 Demandes de Recrutement  
    - 📊 Suivi des Intégrations
    
    *Basé sur vos données Power BI*
    """)

if __name__ == "__main__":
    show_navigation()