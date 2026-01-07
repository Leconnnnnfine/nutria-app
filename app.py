import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import re
import datetime
import os

# --- 1. SÉCURITÉ & CONFIG ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "TA_VRAIE_CLE_ICI"

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="NutrIA", page_icon="🥗", layout="wide")

# --- 2. SYSTÈME DE SAUVEGARDE (PERSISTANCE JSON) 💾 ---
DB_FILE = "nutria_data.json"

def load_data():
    # Si le fichier existe, on charge les données
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    # Sinon, on retourne les valeurs par défaut
    return {
        "total_calories": 0,
        "streak": 0,
        "last_streak_date": "1970-01-01", # Date bidon pour commencer
        "repas_du_jour": [],
        "last_visit_date": str(datetime.date.today())
    }

def save_data():
    # On sauvegarde les infos importantes dans le fichier
    data = {
        "total_calories": st.session_state['total_calories'],
        "streak": st.session_state['streak'],
        "last_streak_date": str(st.session_state['last_streak_date']),
        "repas_du_jour": st.session_state['repas_du_jour'],
        "last_visit_date": str(st.session_state['last_date'])
    }
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# --- 3. CHARGEMENT AU DÉMARRAGE ---
if 'data_loaded' not in st.session_state:
    saved_data = load_data()
    st.session_state['total_calories'] = saved_data["total_calories"]
    st.session_state['streak'] = saved_data["streak"]
    st.session_state['last_streak_date'] = datetime.datetime.strptime(saved_data["last_streak_date"], "%Y-%m-%d").date()
    st.session_state['repas_du_jour'] = saved_data["repas_du_jour"]
    # On gère la date de visite pour le reset calorique
    last_visit = datetime.datetime.strptime(saved_data["last_visit_date"], "%Y-%m-%d").date()
    st.session_state['last_date'] = last_visit
    
    st.session_state['chat_history'] = [] # Le chat on le garde pas pour l'instant (trop lourd)
    st.session_state['data_loaded'] = True

# --- 4. CHECK RESET MINUIT 🕛 ---
today = datetime.date.today()
if st.session_state['last_date'] != today:
    st.session_state['total_calories'] = 0
    st.session_state['repas_du_jour'] = []
    st.session_state['last_date'] = today
    save_data() # On sauvegarde le reset
    st.toast("📅 Nouveau jour ! Compteur calories remis à zéro.", icon="🌅")

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🔥 NutrIA")
    
    # FLAMMES (Logique corrigée plus bas)
    if st.session_state['streak'] > 0:
        st.metric("Série en cours", f"{st.session_state['streak']} Jours 🔥")
        # On vérifie si la flamme a été validée aujourd'hui
        if st.session_state['last_streak_date'] == today:
            st.caption("✅ Flamme validée pour aujourd'hui !")
        else:
            st.caption("⚠️ Mange un truc pour garder la flamme !")
    else:
        st.info("Valide un repas pour allumer la flamme ! 🔥")
    
    st.divider()
    
    # PROFIL
    st.subheader("👤 Mon Profil")
    genre = st.radio("Sexe", ["Homme", "Femme"], horizontal=True)
    age = st.number_input("Age", 10, 100, 25)
    poids = st.number_input("Poids (kg)", 30, 200, 70)
    taille = st.number_input("Taille (cm)", 100, 250, 175)
    activite = st.select_slider("Activité", options=["Sédentaire", "Léger", "Modéré", "Intense", "Athlète"])
    objectif = st.selectbox("Objectif", ["Perdre du poids", "Maintenir", "Prendre de la masse"])

    if genre == "Homme": bmr = (10 * poids) + (6.25 * taille) - (5 * age) + 5
    else: bmr = (10 * poids) + (6.25 * taille) - (5 * age) - 161
    facteurs = {"Sédentaire": 1.2, "Léger": 1.375, "Modéré": 1.55, "Intense": 1.725, "Athlète": 1.9}
    tdee = bmr * facteurs[activite]

    if objectif == "Perdre du poids": target = tdee - 500
    elif objectif == "Prendre de la masse": target = tdee + 300
    else: target = tdee

    st.divider()
    st.metric("🎯 Objectif Journalier", f"{int(target)} kcal")
    prog = min(st.session_state['total_calories'] / target, 1.0)
    st.progress(prog)
    st.write(f"Mangé : {st.session_state['total_calories']} kcal")
    
    if st.button("🗑️ Reset Manuel"):
        st.session_state['total_calories'] = 0
        st.session_state['repas_du_jour'] = []
        save_data()
        st.rerun()

# --- 6. FONCTIONS IA ---
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

# --- 7. INTERFACE ---
st.title("🥗 NutrIA : Ton Coach Nutrition")
tab1, tab2 = st.tabs(["📸 Scanner", "💬 Coach"])

with tab1:
    col_cam, col_txt = st.columns(2)
    with col_cam:
        img_file = st.file_uploader("📸 Photo", type=["jpg", "png", "jpeg"])
        if img_file:
            img = PIL.Image.open(img_file).convert("RGB")
            st.image(img, use_container_width=True)
            if st.button("🚀 ANALYSER PHOTO", use_container_width=True):
                analyser_repas("Analyse ce plat", img)
    with col_txt:
        txt = st.text_input("📝 Texte (Ex: Kebab complet)")
        if st.button("🚀 ANALYSER TEXTE", use_container_width=True) and txt:
            analyser_repas(txt)

    # RÉSULTAT
    if 'current_analysis' in st.session_state and st.session_state['current_analysis']:
        data = st.session_state['current_analysis']
        
        # Titre en BLEU, Conseil en VERT
        st.info(f"🍽️ **{data['nom_plat']}**")
        c1, c2 = st.columns(2)
        c1.metric("Calories", f"{data['calories']} kcal")
        c2.metric("Protéines", data['proteines'])
        st.success(f"💡 Conseil : {data['conseil']}")
        
        if st.button(f"✅ VALIDER (+{data['calories']} kcal)", use_container_width=True):
            # 1. Ajout Calories
            st.session_state['total_calories'] += data['calories']
            st.session_state['repas_du_jour'].append(f"{data['nom_plat']} ({data['calories']} kcal)")
            
            # 2. LOGIQUE FLAMMES CORRIGÉE 🔥
            # On ne donne le point QUE si la dernière fois c'était PAS aujourd'hui
            if st.session_state['last_streak_date'] != today:
                st.session_state['streak'] += 1
                st.session_state['last_streak_date'] = today
                st.balloons()
                st.toast("🔥 FLAMME ALLUMÉE POUR AUJOURD'HUI !", icon="🔥")
            else:
                # Déjà eu la flamme aujourd'hui
                st.toast("✅ Repas ajouté ! (Flamme déjà active aujourd'hui)", icon="🍽️")

            st.session_state['current_analysis'] = None
            save_data() # SAUVEGARDE IMMÉDIATE !
            st.rerun()

with tab2:
    st.subheader("💬 Coach NutrIA")
    for role, message in st.session_state['chat_history']:
        with st.chat_message(role): st.write(message)
    
    user_input = st.chat_input("Pose une question au coach...")
    if user_input:
        with st.chat_message("user"): st.write(user_input)
        st.session_state['chat_history'].append(("user", user_input))
        
        with st.chat_message("assistant"):
            with st.spinner("Le coach réfléchit..."):
                repas_str = ", ".join(st.session_state['repas_du_jour']) if st.session_state['repas_du_jour'] else "Rien"
                context_prompt = f"Tu es un coach. User a mangé: {repas_str} ({st.session_state['total_calories']} kcal). Obj: {int(target)}. Question: {user_input}"
                response = model.generate_content(context_prompt)
                st.write(response.text)
        st.session_state['chat_history'].append(("assistant", response.text))
