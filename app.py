import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import re
import datetime # Pour gérer le reset de minuit

# --- 1. SÉCURITÉ & CONFIG ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "TA_VRAIE_CLE_ICI"

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="NutrIA", page_icon="🥗", layout="wide")

# --- 2. GESTION DU TEMPS & MÉMOIRE ---
today = datetime.date.today()

# Initialisation des variables
if 'total_calories' not in st.session_state:
    st.session_state['total_calories'] = 0
if 'streak' not in st.session_state:
    st.session_state['streak'] = 0
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'last_date' not in st.session_state:
    st.session_state['last_date'] = today
if 'repas_du_jour' not in st.session_state:
    st.session_state['repas_du_jour'] = [] # On note les plats pour le coach

# 🔥 CHECK RESET DE MINUIT 🔥
# Si la date enregistrée est différente d'aujourd'hui, c'est un nouveau jour !
if st.session_state['last_date'] != today:
    st.session_state['total_calories'] = 0
    st.session_state['repas_du_jour'] = []
    st.session_state['chat_history'] = [] # Nouveau jour, nouvelle discussion
    st.session_state['last_date'] = today
    st.toast("📅 C'est un nouveau jour ! Compteur remis à zéro.", icon="🌅")

# --- 3. SIDEBAR (LE RETOUR DU PROFIL COMPLET) ---
with st.sidebar:
    st.title("🔥 NutrIA")
    
    # FLAMMES
    if st.session_state['streak'] > 0:
        st.metric("Série en cours", f"{st.session_state['streak']} Jours 🔥")
    else:
        st.info("Valide un repas pour allumer la flamme ! 🔥")
    
    st.divider()
    
    # PROFIL COMPLET (V2 Style)
    st.subheader("👤 Mon Profil")
    genre = st.radio("Sexe", ["Homme", "Femme"], horizontal=True)
    age = st.number_input("Age (ans)", 10, 100, 25)
    poids = st.number_input("Poids (kg)", 30, 200, 70)
    taille = st.number_input("Taille (cm)", 100, 250, 175)
    activite = st.select_slider("Activité", options=["Sédentaire", "Léger", "Modéré", "Intense", "Athlète"])
    objectif = st.selectbox("Objectif", ["Perdre du poids", "Maintenir", "Prendre de la masse"])

    # Calcul Savant (Mifflin-St Jeor)
    if genre == "Homme":
        bmr = (10 * poids) + (6.25 * taille) - (5 * age) + 5
    else:
        bmr = (10 * poids) + (6.25 * taille) - (5 * age) - 161

    facteurs = {"Sédentaire": 1.2, "Léger": 1.375, "Modéré": 1.55, "Intense": 1.725, "Athlète": 1.9}
    tdee = bmr * facteurs[activite]

    if objectif == "Perdre du poids": target = tdee - 500
    elif objectif == "Prendre de la masse": target = tdee + 300
    else: target = tdee

    st.divider()
    st.metric("🎯 Objectif Journalier", f"{int(target)} kcal")
    
    # Barre
    prog = min(st.session_state['total_calories'] / target, 1.0)
    st.progress(prog)
    st.write(f"Mangé : {st.session_state['total_calories']} kcal")
    
    if st.button("🗑️ Reset Manuel"):
        st.session_state['total_calories'] = 0
        st.session_state['repas_du_jour'] = []
        st.rerun()

# --- 4. FONCTIONS INTELLIGENTES ---
def clean_json(text):
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

def analyser_repas(prompt_user, image_data=None):
    with st.spinner("🕵️‍♂️ NutrIA scanne ton assiette..."):
        try:
            sys_prompt = """
            Tu es un expert nutrition. Réponds UNIQUEMENT au format JSON :
            {
                "nom_plat": "Nom court du plat",
                "calories": 0,
                "proteines": "0g",
                "analyse": "Phrase courte",
                "conseil": "Conseil santé"
            }
            """
            inputs = [sys_prompt, prompt_user]
            if image_data: inputs.append(image_data)
            response = model.generate_content(inputs)
            data = json.loads(clean_json(response.text))
            st.session_state['current_analysis'] = data
        except Exception as e:
            st.error(f"Erreur IA : {e}")

# --- 5. INTERFACE PRINCIPALE ---
st.title("🥗 NutrIA : Ton Coach Nutrition")

tab1, tab2 = st.tabs(["📸 Scanner", "💬 Coach"])

# --- ONGLET 1 : SCANNER ---
with tab1:
    col_cam, col_txt = st.columns(2)
    with col_cam:
        st.subheader("📸 Photo")
        img_file = st.file_uploader("Prends une photo", type=["jpg", "png", "jpeg"])
        if img_file:
            img = PIL.Image.open(img_file).convert("RGB")
            st.image(img, use_container_width=True)
            if st.button("🚀 ANALYSER LA PHOTO", use_container_width=True):
                analyser_repas("Analyse ce plat", img)

    with col_txt:
        st.subheader("📝 Texte")
        txt = st.text_input("Ex: 2 oeufs au plat et du pain")
        if st.button("🚀 ANALYSER LE TEXTE", use_container_width=True) and txt:
            analyser_repas(txt)

    # RÉSULTAT
    if 'current_analysis' in st.session_state and st.session_state['current_analysis']:
        data = st.session_state['current_analysis']
        
        # --- MODIFICATION COULEURS DEMANDÉE ---
        # Titre en BLEU (st.info)
        st.info(f"🍽️ **{data['nom_plat']}**")
        
        c1, c2 = st.columns(2)
        c1.metric("Calories", f"{data['calories']} kcal")
        c2.metric("Protéines", data['proteines'])
        
        # Conseil en VERT (st.success)
        st.success(f"💡 Conseil : {data['conseil']}")
        # --------------------------------------
        
        if st.button(f"✅ VALIDER (+{data['calories']} kcal)", use_container_width=True):
            st.session_state['total_calories'] += data['calories']
            st.session_state['repas_du_jour'].append(f"{data['nom_plat']} ({data['calories']} kcal)")
            
            if st.session_state['streak'] == 0:
                st.session_state['streak'] = 1
                st.balloons()
            else:
                st.session_state['streak'] += 1
                st.toast("🔥 +1 Flamme !", icon="🔥")

            st.session_state['current_analysis'] = None
            st.rerun()

# --- ONGLET 2 : LE COACH INTELLIGENT ---
with tab2:
    st.subheader("💬 Coach NutrIA")
    
    for role, message in st.session_state['chat_history']:
        with st.chat_message(role):
            st.write(message)
    
    user_input = st.chat_input("Pose une question au coach...")
    
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state['chat_history'].append(("user", user_input))
        
        with st.chat_message("assistant"):
            with st.spinner("Le coach analyse ta journée..."):
                # ON DONNE LE CONTEXTE AU COACH ICI
                repas_str = ", ".join(st.session_state['repas_du_jour']) if st.session_state['repas_du_jour'] else "Rien pour l'instant"
                
                context_prompt = f"""
                Tu es un coach nutrition fun et motivant.
                INFOS UTILISATEUR :
                - Objectif journalier : {int(target)} kcal
                - Calories mangées aujourd'hui : {st.session_state['total_calories']} kcal
                - Plats mangés : {repas_str}
                
                QUESTION DE L'UTILISATEUR : {user_input}
                
                Réponds en tenant compte de ce qu'il a déjà mangé ! Sois court et percutant.
                """
                
                response = model.generate_content(context_prompt)
                st.write(response.text)
        st.session_state['chat_history'].append(("assistant", response.text))
