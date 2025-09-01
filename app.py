import streamlit as st
from datetime import datetime

# === Page Config ===
st.set_page_config(
    page_title="Elomi Care – Syndromic Infection Diagnosis",
    page_icon="🧬",
    layout="wide"
)

# === Sidebar Navigation ===
page = st.sidebar.radio("📁 Navigation", [
    "STI Diagnosis",
    "Febrile Illness Tool",
    "TB Screening",
    "Model Summary",
    "Patient Demographics",
    "Treatment & SMS"
])

# === App Branding ===
st.image("elomi_logo.png", width=140)
st.title("🧬 Elomi Care – Syndromic Infection Diagnosis Suite")
st.markdown("Developed by **Elomi Health Research and Training LLC**")

# === STI Diagnosis Page ===
if page == "STI Diagnosis":
    st.subheader("🔍 STI Diagnosis")
    st.markdown("Enter patient symptoms and risk factors to get a probable STI diagnosis.")

    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0, max_value=120)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
    symptoms = st.multiselect("Symptoms", [
        "Urethral discharge", "Genital ulcer", "Vaginal discharge", "Pelvic pain",
        "Lower abdominal pain", "Dysuria", "Pain during intercourse", "Anal discharge",
        "Genital warts", "Swollen lymph nodes", "Rash", "Fever", "Joint pain"
    ])
    duration = st.selectbox("Duration of symptoms", ["<1 week", "1–2 weeks", ">2 weeks"])
    risk_factors = st.multiselect("Risk factors", [
        "Multiple sexual partners", "Unprotected sex", "New sexual partner",
        "Previous STI", "Sex work", "Partner with STI", "HIV positive"
    ])

    if st.button("Get STI Diagnosis"):
        if "Genital ulcer" in symptoms or "Genital warts" in symptoms:
            probable = "Herpes or HPV"
            possible = "Syphilis"
        elif "Urethral discharge" in symptoms or "Vaginal discharge" in symptoms:
            probable = "Gonorrhea"
            possible = "Chlamydia or Trichomoniasis"
        else:
            probable = "Non-specific STI"
            possible = "Further testing recommended"

        st.success(f"**Probable Diagnosis:** {probable}")
        st.info(f"**Possible Diagnosis:** {possible}")
        st.markdown("🩺 **Recommendation:** Refer to health facility for confirmation and syndromic treatment.")
        st.caption("⚠️ This is not a substitute for professional medical advice.")

# === Febrile Illness Tool Page ===
elif page == "Febrile Illness Tool":
    st.subheader("🌡️ Febrile Illness Triage Tool")
    st.markdown("Use this tool to assess febrile illnesses (Malaria, Typhoid, Dengue, etc.)")

    fever = st.checkbox("Fever >38°C")
    chills = st.checkbox("Chills or rigors")
    joint_pain = st.checkbox("Joint or muscle pain")
    headache = st.checkbox("Severe headache")
    rash = st.checkbox("Skin rash")
    travel = st.checkbox("Recent travel to endemic area")
    vomiting = st.checkbox("Vomiting or diarrhea")
    bleeding = st.checkbox("Bleeding or bruising")
    duration_fever = st.selectbox("Duration of fever", ["<3 days", "3–7 days", ">7 days"])

    if st.button("Evaluate Febrile Illness"):
        if fever and chills and travel and headache:
            probable = "Malaria"
        elif fever and rash and joint_pain:
            probable = "Dengue or Chikungunya"
        elif fever and vomiting and diarrhea:
            probable = "Typhoid Fever"
        else:
            probable = "Non-specific febrile illness"

        st.success(f"**Probable Cause:** {probable}")
        st.markdown("🩺 **Next Step:** Clinical confirmation and lab investigation required.")

# === TB Screening Page ===
elif page == "TB Screening":
    st.subheader("🫁 Tuberculosis Screening Tool")
    st.markdown("WHO-recommended symptom-based TB screening.")

    cough = st.checkbox("Persistent cough >2 weeks")
    weight_loss = st.checkbox("Unintentional weight loss")
    night_sweats = st.checkbox("Night sweats")
    fever_tb = st.checkbox("Fever")
    contact_tb = st.checkbox("Close contact with TB case")

    if st.button("Screen for TB"):
        symptom_score = sum([cough, weight_loss, night_sweats, fever_tb, contact_tb])
        if symptom_score >= 3 or (cough and weight_loss):
            st.warning("⚠️ **High suspicion of TB** – Refer for sputum test, X-ray, or GeneXpert.")
        elif symptom_score >= 1:
            st.info("🩺 **Possible TB symptoms present** – Monitor and reassess if symptoms persist.")
        else:
            st.success("✅ Low suspicion of TB – No immediate action required.")

# === Model Summary Page ===
elif page == "Model Summary":
    st.subheader("🧠 Model Summary")
    st.markdown("This page will summarize the logic and accuracy of the syndromic models used.")

# === Patient Demographics Page ===
elif page == "Patient Demographics":
    st.subheader("👥 Patient Demographics")
    st.markdown("View or analyze anonymized demographic trends (future implementation).")

# === Treatment and SMS Page ===
elif page == "Treatment & SMS":
    st.subheader("💊 Treatment Recommendation & SMS Generator")
    st.markdown("Auto-generate treatment and SMS for referral or partner notification (future implementation).")

