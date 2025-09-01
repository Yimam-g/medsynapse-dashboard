import streamlit as st
from datetime import datetime
import openai
import os

# === SETUP ===
st.set_page_config(page_title="Elomi AI Diagnostic App", page_icon="🧬", layout="wide")

# Optional: Set your OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY", "sk-...")  # Replace with your actual key or use env variable

def gpt_diagnosis(symptoms):
    prompt = f"""
    Patient reports the following symptoms: {symptoms}
    Based on WHO guidelines and global syndromic diagnosis, suggest the most likely infection (STI, Febrile illness, or TB), probable co-infections, and recommended initial management.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ GPT Error: {str(e)}"

# === AI Rule-Based Scoring ===
def ai_score(symptom_dict):
    score = 0
    weights = {
        "urethral_discharge": 3,
        "genital_ulcer": 4,
        "fever": 2,
        "night_sweats": 3,
        "weight_loss": 3,
        "chronic_cough": 4,
        "headache": 1,
        "jaundice": 2,
        "diarrhea": 1,
        "vaginal_discharge": 2
    }
    for symptom, present in symptom_dict.items():
        if present:
            score += weights.get(symptom, 0)
    return score

# === Sidebar Navigation ===
section = st.sidebar.radio("📁 Navigation", ["🏠 Home", "🧬 STI Diagnosis", "🌡️ Febrile Illness", "🫁 Tuberculosis", "💬 SMS Generator"])

# === WHO-Based Header ===
st.image("elomi_logo.png", width=140)
st.title("🧠 Elomi AI Diagnostic Platform")

# === Common Symptoms Form ===
def collect_symptoms():
    st.subheader("📝 Symptom Input")
    st.markdown("_Select observed symptoms for AI scoring and GPT triage_ ✅")
    return {
        "urethral_discharge": st.checkbox("Urethral Discharge"),
        "vaginal_discharge": st.checkbox("Vaginal Discharge"),
        "genital_ulcer": st.checkbox("Genital Ulcer"),
        "fever": st.checkbox("Fever"),
        "headache": st.checkbox("Headache"),
        "night_sweats": st.checkbox("Night Sweats"),
        "weight_loss": st.checkbox("Weight Loss"),
        "chronic_cough": st.checkbox("Cough >2 Weeks"),
        "jaundice": st.checkbox("Jaundice"),
        "diarrhea": st.checkbox("Diarrhea")
    }

# === Diagnosis Output Section ===
def show_diagnosis(name, symptom_dict):
    score = ai_score(symptom_dict)
    symptoms_text = ", ".join([k.replace("_", " ") for k, v in symptom_dict.items() if v])

    st.success(f"📊 AI Score for {name}: **{score}/25**")
    st.info("🤖 GPT Interpretation:")
    st.markdown(gpt_diagnosis(symptoms_text))

    if score > 8:
        st.warning("⚠️ Possible severe infection or co-infection. Recommend urgent referral.")
    elif score > 4:
        st.success("👍 Moderate concern. Consider syndromic treatment based on findings.")
    else:
        st.info("✔️ Low-risk symptoms. Monitor or provide preventive advice.")

# === Prevention + Treatment Advice ===
def clinical_guidance():
    st.subheader("📘 WHO-Based Case Definition & Management")
    st.markdown("""
    - **STI (Discharge)**: Treat with Azithromycin + Cefixime. Avoid unprotected sex.
    - **Febrile Illness (e.g. Malaria, Dengue, Typhoid)**: Rule out based on region & exposure. Use RDTs.
    - **TB Suspect**: Sputum microscopy / GeneXpert, consider referral for DOTS.
    """)
    st.link_button("📄 WHO STI Guidelines", "https://www.who.int/publications/i/item/9789240057416")

# === SMS Generator ===
def sms_form():
    st.subheader("📤 Generate SMS to patient")
    name = st.text_input("Patient Name")
    result = st.text_area("Diagnosis Summary")
    st.markdown(f"""
    **📨 SMS Message:**

    Hello {name}, your recent health check suggests: _{result}_. Please follow the recommended treatment and visit your clinic if symptoms worsen. – Elomi Health Team
    """)
    st.caption("✔️ You can copy this and send via your clinic SMS system.")

# === Main Section Routing ===
if section == "🏠 Home":
    st.markdown("Welcome to the **Elomi AI Diagnostic App** – supporting clinicians and patients with decision-making tools for common infections in Africa.")
    st.markdown("Use the sidebar to begin diagnosis or generate SMS.")

elif section == "🧬 STI Diagnosis":
    st.header("🧬 STI Syndromic Diagnosis")
    symptoms = collect_symptoms()
    if st.button("🔍 Diagnose STI"):
        show_diagnosis("STI", symptoms)
        clinical_guidance()

elif section == "🌡️ Febrile Illness":
    st.header("🌡️ Febrile Illness Diagnosis")
    symptoms = collect_symptoms()
    if st.button("🧪 Diagnose Febrile Illness"):
        show_diagnosis("Febrile Illness", symptoms)
        clinical_guidance()

elif section == "🫁 Tuberculosis":
    st.header("🫁 Tuberculosis Screening")
    symptoms = collect_symptoms()
    if st.button("📋 Assess TB Risk"):
        show_diagnosis("Tuberculosis", symptoms)
        clinical_guidance()

elif section == "💬 SMS Generator":
    sms_form()

