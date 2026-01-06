import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import re
import os

# --- 1. CONFIGURATION ---
# ⚠️ REMETS TA CLÉ ICI !
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = "AIzaSyDNVt-OwOKHWji-2MoCw7YMPcEWYiFad8w"

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="NutrIA", page_icon="🥗", layout="wide")

# --- 2. GESTION DE LA MÉMOIRE ---
if 'total_calories' not in st.session_state:
    st.session_state['total_calories'] = 0
if 'current_analysis' not in st.session_state:
    st.session_state['current_analysis'] = None

# --- 3. SIDEBAR (PROFIL) ---
with st.sidebar:
    st.title("👤 Mon Profil")
    # On garde simple pour l'exemple
    poids = st.number_input("Poids (kg)", 30, 200, 70)
    taille = st.number_input("Taille (cm)", 100, 250, 175)
    age = st.number_input("Age", 10, 100, 25)
    genre = st.radio("Sexe", ["Homme", "Femme"])
    objectif_str = st.selectbox("Objectif", ["Perdre", "Maintenir", "Prendre"])

    # Calcul rapide BMR
    base = (10 * poids) + (6.25 * taille) - (5 * age)
    bmr = base + 5 if genre == "Homme" else base - 161
    target = bmr * 1.55 # Activité modérée par défaut

    if objectif_str == "Perdre": target -= 500
    elif objectif_str == "Prendre": target += 300

    st.divider()
    st.metric("🎯 Objectif", f"{int(target)} kcal")

    if st.button("🗑️ Reset Journée"):
        st.session_state['total_calories'] = 0
        st.session_state['current_analysis'] = None
        st.rerun()

# --- 4. DASHBOARD ---
st.title("🥗 NutrIA : Le Coach")

col1, col2, col3 = st.columns(3)
with col1: st.metric("Mangé", f"{int(st.session_state['total_calories'])} kcal")
with col2: st.metric("Restant", f"{int(target - st.session_state['total_calories'])} kcal")
with col3:
    prog = min(st.session_state['total_calories'] / target, 1.0)
    st.progress(prog)

st.divider()

# --- 5. FONCTION INTELLIGENTE ---
def clean_json(text):
    # Parfois l'IA met des ```json ... ``` autour, on les vire
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

def analyser_repas(prompt_user, image_data=None):
    with st.spinner("🕵️‍♂️ NutrIA scanne ton assiette..."):
        try:
            # On force l'IA à répondre en JSON strict
            sys_prompt = """
            Tu es un expert nutrition. Analyse le plat.
            Réponds UNIQUEMENT au format JSON comme ça :
            {
                "nom_plat": "Nom du plat",
                "calories": 500,
                "proteines": "30g",
                "analyse": "Ton analyse courte et fun ici",
                "conseil": "Ton conseil de coach"
            }
            Ne mets rien d'autre que le JSON. merci fro
            """

            inputs = [sys_prompt, prompt_user]
            if image_data: inputs.append(image_data)

            response = model.generate_content(inputs)

            # On nettoie et on charge le JSON
            json_str = clean_json(response.text)
            data = json.loads(json_str)

            # On stocke le résultat en mémoire tampon
            st.session_state['current_analysis'] = data

        except Exception as e:
            st.error(f"L'IA a bégayé : {e}")

# --- 6. INTERFACE D'ANALYSE ---
tab1, tab2 = st.tabs(["📸 Photo", "📝 Texte"])

with tab1:
    img_file = st.file_uploader("Une photo ?", type=["jpg", "png", "jpeg"])
    if img_file and st.button("🚀 Analyser Photo"):
        img = PIL.Image.open(img_file).convert("RGB")
        st.image(img, width=200)
        analyser_repas("Analyse cette image", img)

with tab2:
    txt = st.text_input("Qu'as-tu mangé ?")
    if st.button("🚀 Analyser Texte") and txt:
        analyser_repas(txt)

# --- 7. ZONE DE VALIDATION (Le truc magique) ---
if st.session_state['current_analysis']:
    data = st.session_state['current_analysis']

    st.info(f"### 🍽️ {data['nom_plat']}")
    st.write(f"**Analyse :** {data['analyse']}")
    st.write(f"💡 *Conseil du coach : {data['conseil']}*")

    # Affichage des macros
    c1, c2 = st.columns(2)
    c1.metric("🔥 Calories détectées", data['calories'])
    c2.metric("🥩 Protéines", data['proteines'])

    # LE BOUTON MAGIQUE
    if st.button(f"✅ VALIDER ET MANGER (+{data['calories']} kcal)"):
        st.session_state['total_calories'] += data['calories']
        st.session_state['current_analysis'] = None # On vide l'analyse
        st.success("Miam ! C'est noté !")
        st.rerun()
