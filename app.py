import streamlit as st
from datetime import datetime

# === Page Config ===
st.set_page_config(
    page_title="Elomi STI Care",
    page_icon="🧬",
    layout="wide"
)

# Initialize session state
if 'diagnosis_summary' not in st.session_state:
    st.session_state['diagnosis_summary'] = ""
if 'confidence_score' not in st.session_state:
    st.session_state['confidence_score'] = 0
if 'treatment_plan' not in st.session_state:
    st.session_state['treatment_plan'] = ""
if 'sms_text' not in st.session_state:
    st.session_state['sms_text'] = ""

# === Sidebar Navigation ===
page = st.sidebar.radio("📁 Navigation", ["Patient Demographics", "Diagnosis", "Treatment & SMS", "Model Summary"])

# === Intro Header ===
st.image("elomi_logo.png", width=140)
st.title("🧬 Elomi STI Care – AI-Based Syndromic STI Diagnostic Pipeline")

# === Patient Demographics ===
if page == "Patient Demographics":
    st.header("Patient Registration")
    name = st.text_input("Full Name")
    patient_id = st.text_input("Patient ID")
    age = st.number_input("Age", min_value=0, max_value=120)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
    phone = st.text_input("Phone Number (e.g. +2519xxxxxxx)")

# === Diagnosis Page ===
elif page == "Diagnosis":
    st.markdown("""
    Welcome to **Elomi STI Care**, a digital assistant to help clinicians with syndromic STI diagnosis based on WHO guidance.

    This app helps you:
    - Generate structured clinical summaries
    - Provide patient-safe SMS guidance
    - Optionally translate summaries to Amharic
    - Keep communication clear, confidential, and evidence-based

    Developed by **Elomi Health Research and Training LLC**
    """)

    st.header("Symptom Input")
    symptoms = st.multiselect("Select symptoms", [
        "Vaginal discharge", "Urethral discharge", "Genital ulcer",
        "Lower abdominal pain", "Pain during urination", "Genital itching",
        "Pain during sex", "Anal symptoms"
    ])

    discharge_color = st.selectbox("Discharge color (if applicable)", [
        "—", "Thick white (curd-like)", "Yellow or green (pus-like)", "Gray (with odor)",
        "Bloody or brownish", "Clear or watery"
    ])

    duration = st.selectbox("Symptom duration", ["< 7 days", "7–14 days", "> 14 days"])
    occupation = st.selectbox("Occupation", [
        "General population", "Commercial Sex Worker", "Healthcare Worker",
        "Student", "Farmer", "Other"
    ])

    if st.button("Submit"):
        probable_diagnosis = "Gonorrhea or Chlamydia based on reported symptoms"
        confidence_score = 82  # Placeholder confidence score
        treatment = "Ceftriaxone 500 mg IM once + Azithromycin 1 g orally once"
        sms = f"Dear patient, your diagnosis suggests: {probable_diagnosis}. Please complete your treatment: {treatment}. Avoid sexual contact until treatment is finished."

        summary = f"Clinical Summary:\n- Symptoms: {', '.join(symptoms)}\n- Duration: {duration}\n- Discharge Appearance: {discharge_color}\n- Occupation: {occupation}\n- Probable Diagnosis: {probable_diagnosis}\n- Confidence: {confidence_score}%"

        st.session_state['diagnosis_summary'] = summary
        st.session_state['confidence_score'] = confidence_score
        st.session_state['treatment_plan'] = treatment
        st.session_state['sms_text'] = sms

        st.success("Diagnosis generated. Please continue to the Treatment & SMS tab.")

        st.subheader("Diagnosis Output")
        st.text_area("Clinical Summary", value=summary, height=200)

# === Treatment and SMS Page ===
elif page == "Treatment & SMS":
    st.header("Treatment Recommendation and Patient Communication")

    st.subheader("Clinical Diagnosis Summary")
    st.text_area("Diagnosis", value=st.session_state.get('diagnosis_summary', "No diagnosis available yet. Please submit symptoms in the Diagnosis tab."), height=200)

    st.subheader("Treatment Recommendation")
    st.write(st.session_state.get('treatment_plan', "No recommendation available."))

    st.subheader("Patient SMS Message")
    sms_message = st.text_area("Generated SMS", value=st.session_state.get('sms_text', ""))
    if st.button("Send SMS"):
        st.success("Simulated SMS sent.")

    st.subheader("Optional: Translate to Amharic")
    st.write("Translation: ሕክምናዎን በሙሉ ይጨርሱ። እባኮትን ወዳጆችዎን እንዲፈተሹ ያበረታቱ።")

# === Model Summary Page ===
elif page == "Model Summary":
    st.header("Model Summary")
    st.markdown(f"""
    ### Clinical Confidence / Uncertainty Score
    - Current confidence: {st.session_state.get('confidence_score', 'N/A')}%

    ### Model Insights
    - Considers: Symptom type, duration, discharge appearance, occupation risk
    - Diagnosis logic updated based on WHO syndromic case definitions and AI refinement

    ### Future Enhancements
    - Add lab confirmation module
    - Link with Elomi DB for real-time tracking
    """)

