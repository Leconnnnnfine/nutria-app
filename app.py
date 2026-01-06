import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import re
import os

# --- 1. SÉCURITÉ & CONFIG ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "TA_VRAIE_CLE_ICI" # Seulement pour tes tests locaux !

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="NutrIA", page_icon="🥗", layout="wide")

# --- 2. MÉMOIRE ET GAMIFICATION 🔥 ---
if 'total_calories' not in st.session_state:
    st.session_state['total_calories'] = 0
if 'streak' not in st.session_state:
    st.session_state['streak'] = 0 # Le compteur de flammes !
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [] # Pour le coach

# --- 3. SIDEBAR (PROFIL + FLAMMES) ---
with st.sidebar:
    st.title("🔥 NutrIA")
    
    # --- ZONE DES FLAMMES ---
    if st.session_state['streak'] > 0:
        st.metric("Série en cours", f"{st.session_state['streak']} Jours 🔥")
        st.caption("Continue comme ça champion ! 🏆")
    else:
        st.info("Valide un repas pour allumer la flamme ! 🔥")
    
    st.divider()
    
    # Profil Rapide
    st.subheader("👤 Mon Profil")
    poids = st.number_input("Poids (kg)", 40, 150, 70)
    objectif = st.selectbox("Objectif", ["Perdre", "Maintenir", "Prendre"])
    
    # Calcul simple target
    target = 2000 # Valeur par défaut
    if objectif == "Perdre": target = 1800
    elif objectif == "Prendre": target = 2500
    
    st.metric("🎯 Objectif du jour", f"{target} kcal")
    
    # Barre de progression du jour
    prog = min(st.session_state['total_calories'] / target, 1.0)
    st.progress(prog)
    st.write(f"Mangé : {st.session_state['total_calories']} kcal")
    
    if st.button("🗑️ Reset Journée"):
        st.session_state['total_calories'] = 0
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
                "nom_plat": "Nom court",
                "calories": 0,
                "proteines": "0g",
                "analyse": "Phrase courte fun",
                "conseil": "Conseil pro"
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

# Onglets : Scanner VS Discuter
tab1, tab2 = st.tabs(["📸 Scanner un Repas", "💬 Discuter avec le Coach"])

# --- ONGLET 1 : SCANNER ---
with tab1:
    col_cam, col_txt = st.columns(2)
    
    with col_cam:
        st.subheader("📸 La Photo")
        img_file = st.file_uploader("Prends une photo", type=["jpg", "png", "jpeg"])
        if img_file:
            img = PIL.Image.open(img_file).convert("RGB")
            st.image(img, use_container_width=True)
            if st.button("🚀 ANALYSER LA PHOTO", use_container_width=True):
                analyser_repas("Analyse ce plat", img)

    with col_txt:
        st.subheader("📝 Ou décris-le")
        txt = st.text_input("Ex: Un grec salade tomate oignon")
        if st.button("🚀 ANALYSER LE TEXTE", use_container_width=True) and txt:
            analyser_repas(txt)

    # RÉSULTAT DE L'ANALYSE
    if 'current_analysis' in st.session_state and st.session_state['current_analysis']:
        data = st.session_state['current_analysis']
        st.success(f"🍽️ {data['nom_plat']}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Calories", f"{data['calories']} kcal")
        c2.metric("Protéines", data['proteines'])
        c3.info(f"💡 {data['conseil']}")
        
        # LE BOUTON QUI DÉCLENCHE LES FLAMMES 🔥
        if st.button(f"✅ VALIDER ET MANGER (+{data['calories']} kcal)", use_container_width=True):
            st.session_state['total_calories'] += data['calories']
            
            # GESTION DES FLAMMES SNAP
            if st.session_state['streak'] == 0:
                st.session_state['streak'] = 1
                st.balloons() # LÂCHER DE BALLONS !!! 🎉
                st.toast("🔥 PREMIÈRE FLAMME ALLUMÉE !!!", icon="🔥")
            else:
                st.session_state['streak'] += 1 # On augmente juste pour la démo
                st.snow() # LÂCHER DE NEIGE POUR VARIER
                st.toast("🔥 SÉRIE PROLONGÉE !!!", icon="🔥")

            st.session_state['current_analysis'] = None
            st.rerun()

# --- ONGLET 2 : LE COACH (CHAT) ---
with tab2:
    st.subheader("💬 Coach NutrIA")
    
    # Afficher l'historique
    for role, message in st.session_state['chat_history']:
        with st.chat_message(role):
            st.write(message)
    
    # Zone de saisie
    user_input = st.chat_input("Pose une question (ex: Je peux manger une pizza ce soir ?)")
    
    if user_input:
        # 1. On affiche le message user
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state['chat_history'].append(("user", user_input))
        
        # 2. L'IA réfléchit
        with st.chat_message("assistant"):
            with st.spinner("Le coach réfléchit..."):
                chat_prompt = f"Tu es un coach sportif et nutrition drôle et motivant. L'utilisateur te demande : {user_input}"
                response = model.generate_content(chat_prompt)
                st.write(response.text)
        st.session_state['chat_history'].append(("assistant", response.text))
