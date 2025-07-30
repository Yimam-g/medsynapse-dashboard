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
            return response.json().get('translatedText', "Translation unavailable.")
        else:
            return "Translation unavailable."
    except Exception:
        return "Translation unavailable."

# === Generate Patient-Friendly SMS ===
def generate_patient_sms(diagnosis, recommendation):
    return (
        f"Dear patient, your diagnosis suggests: {diagnosis}. {recommendation} "
        "Please complete all medications as prescribed. Avoid sexual contact until your treatment is complete. "
        "Encourage your partner(s) to get checked. Stay safe and follow up in 7 days or sooner if symptoms worsen."
    )

# === Simulated SMS Sending ===
def send_sms(phone, message):
    st.success(f"Patient SMS sent to {phone}: {message[:50]}...")

# === Syndrome Mapping Based on Conditions ===
def map_condition_to_syndrome(condition):
    if condition in ["Gonorrhea", "Chlamydia"]:
        return "Urethral Discharge Syndrome"
    elif condition in ["Trichomoniasis", "BV"]:
        return "Vaginal Discharge Syndrome"
    elif condition in ["Syphilis", "Herpes"]:
        return "Genital Ulcer Syndrome"
    elif condition == "PID":
        return "Pelvic Inflammatory Disease"
    elif condition == "Proctitis":
        return "Proctitis"
    else:
        return "Non-specific STI"

# === Treatment and Referral Logic with Primary Care Context ===
def get_recommendation(syndrome):
    if syndrome == "Genital Ulcer Syndrome":
        return (
            "Treat with Benzathine Penicillin 2.4 million units IM single dose for Syphilis, and/or Acyclovir 400 mg orally three times daily for 7 days for Herpes. Re-evaluate in 7 days if no improvement.",
            "Referral only if no improvement or HIV unknown",
            "Moderate"
        )
    elif syndrome == "Urethral Discharge Syndrome":
        return (
            "Treat with Ceftriaxone 500 mg IM once + Azithromycin 1 g orally once.",
            "Referral only if symptoms persist after treatment",
            "Routine"
        )
    elif syndrome == "Vaginal Discharge Syndrome":
        return (
            "Treat with Metronidazole 2 g orally single dose or 500 mg twice daily for 7 days. Re-evaluate in 1 week.",
            "Referral if persistent or recurrent symptoms",
            "Routine"
        )
    elif syndrome == "Pelvic Inflammatory Disease":
        return (
            "Treat with Ceftriaxone 500 mg IM once + Doxycycline 100 mg orally twice daily for 14 days + Metronidazole 500 mg orally twice daily for 14 days. Urgent re-evaluation in 3–5 days recommended.",
            "Referral strongly recommended",
            "Urgent"
        )
    elif syndrome == "Proctitis":
        return (
            "Treat with Ceftriaxone 500 mg IM once + Doxycycline 100 mg orally twice daily for 7 days.",
            "Refer for anorectal exam and HIV testing",
            "Urgent"
        )
    elif syndrome == "Non-specific STI":
        return (
            "Provide symptomatic care and observe. Consider UTI, vaginitis, or non-STI causes. Re-evaluate in 1 week if no improvement.",
            "Referral if symptoms worsen or persist",
            "Routine"
        )
    else:
        return (
            "Unable to recommend treatment without more information. Consider referral for diagnostic evaluation.",
            "Referral Required",
            "Moderate"
        )

# === Page Setup ===
st.set_page_config(page_title="Elomi STI Care", layout="centered")

# === App Branding ===
st.image("elomi_logo.png", width=160)
st.title("Elomi STI Care – AI-Based Syndromic STI Diagnostic Pipeline")

# === Intro Message ===
st.markdown("""
Welcome to **Elomi STI Care**, a digital tool designed to support clinicians in the syndromic diagnosis and management of sexually transmitted infections (STIs).

This app helps:
- Generate structured clinical summaries  
- Provide patient-safe SMS guidance  
- Optionally translate summaries to Amharic  
- Keep communication clear, confidential, and evidence-based  

Developed by **Elomi Health Research and Training LLC**
""")

# === Symptom Scoring Dictionary ===
symptom_weights = {
    "Vaginal discharge": {"Chlamydia": 2, "Trichomoniasis": 3, "BV": 3},
    "Urethral discharge": {"Gonorrhea": 3, "Chlamydia": 2},
    "Genital ulcer": {"Syphilis": 3, "Herpes": 3},
    "Lower abdominal pain": {"PID": 3},
    "Pain during urination": {"Gonorrhea": 2},
    "Genital itching": {"Trichomoniasis": 2, "BV": 1},
    "Pain during sex": {"PID": 2},
    "Anal symptoms": {"Proctitis": 3}
}

# === Patient Form ===
with st.form("patient_form"):
    st.subheader("Patient Registration")
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

    st.subheader("STI Symptoms")
    symptoms_selected = st.multiselect("Select observed symptoms:", list(symptom_weights.keys()))
    other_symptom = st.text_input("Other symptoms (if any)")
    symptoms = "; ".join(symptoms_selected)
    if other_symptom:
        symptoms += f"; {other_symptom}"

    submitted = st.form_submit_button("Submit and Diagnose")

# === AI Diagnosis Engine Based on Weighted Scoring ===
def smart_diagnosis(symptoms_list):
    diagnosis_scores = {}
    for symptom in symptoms_list:
        weights = symptom_weights.get(symptom, {})
        for condition, score in weights.items():
            diagnosis_scores[condition] = diagnosis_scores.get(condition, 0) + score

    if not diagnosis_scores:
        return "Non-specific STI"

    sorted_conditions = sorted(diagnosis_scores.items(), key=lambda x: x[1], reverse=True)
    top_diagnosis = sorted_conditions[0][0]
    return top_diagnosis

# === On Submit ===
if submitted:
    top_condition = smart_diagnosis(symptoms_selected)
    syndrome = map_condition_to_syndrome(top_condition)
    probable_diagnosis = f"{syndrome} (most likely {top_condition})"
    recommendation, referral, urgency = get_recommendation(syndrome)

    # Clinical summary
    english_summary = (
        f"{name} is a {age}-year-old {gender.lower()} who presented with: {symptoms}. "
        f"Probable diagnosis: {probable_diagnosis}. Treatment: {recommendation} "
        f"Referral advice: {referral}. Urgency: {urgency}."
    )

    st.subheader("English Clinical Summary (for clinician)")
    st.write(english_summary)

    # Optional Amharic summary
    st.subheader("Amharic Summary (optional)")
    amharic_summary = translate_to_amharic(english_summary)
    st.write(amharic_summary)

    # SMS to patient
    st.subheader("Patient SMS Message (English)")
    patient_sms = generate_patient_sms(probable_diagnosis, recommendation)
    st.write(patient_sms)

    if st.button("Send Patient SMS"):
        send_sms(phone, patient_sms)

# === Footer: STI Advice ===
st.markdown("---")
st.markdown("### STI Prevention & Follow-Up Advice")
st.markdown("""
- Complete all your prescribed medications even if symptoms improve.
- Refrain from sexual contact during treatment.
- Use condoms consistently and correctly.
- Inform and encourage your partner(s) to get tested and treated.
- Return to the clinic if symptoms persist, worsen, or recur.
- Maintain regular STI screening if you're at increased risk.

*This app supports clinicians and patients in STI diagnosis, management, and education.*
""")

