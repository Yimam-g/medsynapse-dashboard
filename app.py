import streamlit as st
import requests
from datetime import datetime

# === Translate to Amharic (Optional with Fallback) ===
def translate_to_amharic(text):
    try:
        if len(text) > 500:
            text = text[:497] + "..."
        response = requests.post(
            "https://translate.argosopentech.com/translate",
            json={
                "q": text,
                "source": "en",
                "target": "am",
                "format": "text"
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('translatedText', "\u12e8\u12cc\u120a\u1295\u12cd \u121b\u1320\u12aa\u120b \u1218\u1270\u122d\u130e\u121d \u12a0\u120d\u1270\u127b\u120d\u121d\u1361")
        else:
            return "\u12e8\u12cc\u120a\u1295\u12cd \u121b\u1320\u12aa\u120b \u1218\u1270\u122d\u130e\u121d \u12a0\u120d\u1270\u127b\u120d\u121d\u1361"
    except Exception:
        return "\u12e8\u12cc\u120a\u1295\u12cd \u121b\u1320\u12aa\u120b \u1218\u1270\u122d\u130e\u121d \u12a0\u120d\u1270\u127b\u120d\u121d\u1361"

# === Generate Patient-Friendly SMS ===
def generate_patient_sms(diagnosis):
    return (
        "Dear patient, your visit today suggests an infection that requires treatment. "
        "Please complete all medications as prescribed. Avoid sexual contact until your treatment is complete. "
        "You may also encourage your partner to get checked. Stay safe and follow up if symptoms continue."
    )

# === Simulated SMS Sending ===
def send_sms(phone, message):
    st.success(f"📤 Patient SMS sent to {phone}: {message[:50]}...")

# === Diagnosis Logic Based on WHO/CDC Syndromic Definitions ===
def get_probable_diagnosis(symptoms_list):
    symptoms_lower = [s.lower() for s in symptoms_list]

    if "genital ulcer" in symptoms_lower:
        return "Genital Ulcer Syndrome – Likely Syphilis or Herpes"
    elif "urethral discharge" in symptoms_lower:
        return "Urethral Discharge Syndrome – Likely Gonorrhea or Chlamydia"
    elif "vaginal discharge" in symptoms_lower:
        return "Vaginal Discharge Syndrome – Likely Bacterial Vaginosis or Trichomoniasis"
    elif "lower abdominal pain" in symptoms_lower and "pain during sex" in symptoms_lower:
        return "Pelvic Inflammatory Disease (PID)"
    elif "anal symptoms" in symptoms_lower:
        return "Proctitis – Suspect STI or HSV"
    else:
        return "Non-specific STI – Further Evaluation Needed"

# === Page Setup ===
st.set_page_config(page_title="Elomi STI Care", layout="centered")

# === App Branding ===
st.image("elomi_logo.png", width=160)
st.title("🧬 Elomi STI Care – AI-Based Syndromic STI Diagnostic Pipeline")

# === Intro Message ===
st.markdown("""
Welcome to **Elomi STI Care**, a digital tool designed to support clinicians in the syndromic diagnosis and management of sexually transmitted infections (STIs).

This app helps:
- 📝 Generate structured clinical summaries  
- 💬 Provide patient-safe SMS guidance  
- 🌍 Optionally translate summaries to Amharic  
- 🔒 Keep communication clear, confidential, and evidence-based  

Developed by **Elomi Health Research and Training LLC**
""")

# === Patient Form ===
with st.form("patient_form"):
    st.subheader("👤 Patient Registration")
    name = st.text_input("Full Name")
    age = st.number_input("Age", min_value=1, max_value=120)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
    occupation = st.selectbox("Occupation", [
        "Student", "Farmer", "Daily Laborer", "Housewife",
        "Government Worker", "Private Worker",
        "Commercial Sex Worker", "Merchant", "Driver", "Unemployed", "Other"
    ])
    facility = st.text_input("Health Facility")
    phone = st.text_input("Phone Number (e.g. +2519xxxxxxx)")

    st.subheader("🩺 STI Symptoms")
    symptoms_selected = st.multiselect("Select observed symptoms:", [
        "Vaginal discharge",
        "Urethral discharge",
        "Genital ulcer",
        "Lower abdominal pain",
        "Pain during urination",
        "Genital itching",
        "Pain during sex",
        "Anal symptoms"
    ])
    other_symptom = st.text_input("Other symptoms (if any)")
    symptoms = "; ".join(symptoms_selected)
    if other_symptom:
        symptoms += f"; {other_symptom}"

    submitted = st.form_submit_button("Submit and Diagnose")

# === On Submit ===
if submitted:
    probable_diagnosis = get_probable_diagnosis(symptoms_selected)
    urgency = "Urgent"

    # Clinical summary
    english_summary = (
        f"{name} is a {age}-year-old {gender.lower()} who presented with: {symptoms}. "
        f"Possible diagnosis: {probable_diagnosis}. Urgency level: {urgency}."
    )

    st.subheader("📝 English Clinical Summary (for clinician)")
    st.write(english_summary)

    # Optional Amharic summary
    st.subheader("🌍 Amharic Summary (optional)")
    amharic_summary = translate_to_amharic(english_summary)
    st.write(amharic_summary)

    # SMS to patient
    st.subheader("💬 Patient SMS Message (English)")
    patient_sms = generate_patient_sms(probable_diagnosis)
    st.write(patient_sms)

    if st.button("📤 Send Patient SMS"):
        send_sms(phone, patient_sms)

# === Footer: STI Advice ===
st.markdown("---")
st.markdown("### 📢 STI Prevention & Follow-Up Advice")
st.markdown("""
- Always complete your medications.
- Avoid sex until treatment is finished.
- Use condoms regularly.
- Encourage your partner(s) to get tested.
- Follow up if symptoms continue.

🧠 *This app assists clinicians in structured note generation, patient guidance, and STI care continuity.*
""")