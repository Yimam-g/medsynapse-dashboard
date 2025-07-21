import streamlit as st

st.set_page_config(page_title="Elomi STI Care", layout="centered")

st.title("🧬 Elomi STI Care – AI-Based Syndromic STI Diagnostic Pipeline")
st.markdown("""
This AI-powered clinical support system is developed by **Elomi Health Research and Training LLC**. It assists clinicians and health workers 
in low-resource settings to identify likely **sexually transmitted infections (STIs)** based on syndromic inputs and patient risk factors.

""")

# -----------------------------------
# 📌 Patient Registration Details
# -----------------------------------
st.header("🗂️ Patient Registration")

col1, col2 = st.columns(2)
with col1:
    patient_name = st.text_input("Patient Full Name")
    patient_id = st.text_input("Patient ID")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    age = st.number_input("Age", min_value=0, max_value=120, step=1)
with col2:
    facility_name = st.text_input("Health Facility Name")
    marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed", "Other"])
    occupation = st.selectbox(
        "Occupation", 
        ["FSW (Female Sex Worker)", "Truck Driver", "Government Worker", "Merchant", "Self-employed", "Student", "Unemployed", "Other"]
    )

# -----------------------------------
# ⚠️ STI Risk Factors
# -----------------------------------
st.subheader("⚠️ Risk Behaviors")
risk_factors = st.multiselect(
    "Select all that apply",
    ["Unprotected sex", "Multiple sexual partners", "New sexual partner", 
     "Substance use before sex", "Partner with STI", "HIV-positive", 
     "Previous STI history", "Commercial sex work"]
)

# -----------------------------------
# 📝 Symptom Input
# -----------------------------------
st.subheader("📝 Symptom Description")
symptom_mode = st.radio("Choose how to enter symptoms", ["Select from list", "Free text entry"])

selected_symptoms = []
free_text = ""

if symptom_mode == "Select from list":
    selected_symptoms = st.multiselect(
        "Select symptoms observed or reported:",
        ["Discharge", "Pelvic pain", "Genital ulcer", "Rash", "Fever", "Genital warts", 
         "Itching", "Irritation", "Burning during urination", "Swollen lymph nodes", 
         "Pain during sex", "Vaginal bleeding", "Scrotal swelling"]
    )
else:
    free_text = st.text_area("Describe symptoms", placeholder="e.g., discharge, ulcers, fever, warts...")

# -----------------------------------
# 🔬 Diagnostic Logic
# -----------------------------------
def diagnose(symptoms):
    s = " ".join(symptoms).lower() if isinstance(symptoms, list) else symptoms.lower()
    result = {"probable": None, "possible": None}

    if "discharge" in s and "pain" in s:
        result["probable"] = "Gonorrhea"
        result["possible"] = "Chlamydia"
    elif "ulcer" in s or "sore" in s:
        result["probable"] = "Syphilis"
        result["possible"] = "Herpes"
    elif "warts" in s:
        result["probable"] = "HPV"
        result["possible"] = "Molluscum contagiosum"
    elif "fever" in s and "rash" in s:
        result["probable"] = "Acute HIV"
        result["possible"] = "Secondary Syphilis"
    elif "itching" in s or "irritation" in s:
        result["probable"] = "Trichomoniasis"
        result["possible"] = "Candidiasis"
    elif "burning" in s and "urination" in s:
        result["probable"] = "Urethritis"
        result["possible"] = "Cystitis"
    else:
        result["probable"] = "Undetermined"
        result["possible"] = "Needs clinical evaluation"

    return result

# -----------------------------------
# 🧠 Trigger Diagnosis
# -----------------------------------
if st.button("Run Diagnosis"):
    if symptom_mode == "Free text entry" and free_text.strip() == "":
        st.warning("Please enter symptoms.")
    elif symptom_mode == "Select from list" and not selected_symptoms:
        st.warning("Please select at least one symptom.")
    else:
        symptoms_input = free_text if symptom_mode == "Free text entry" else selected_symptoms
        diagnosis = diagnose(symptoms_input)

        st.success(f"✅ Probable Diagnosis: **{diagnosis['probable']}**")
        st.info(f"ℹ️ Possible Alternative: **{diagnosis['possible']}**")

        st.subheader("📌 Clinical Recommendations")
        if diagnosis["probable"] == "Undetermined":
            st.warning("Refer to clinician for comprehensive STI evaluation.")
        else:
            st.markdown("""
            - Consider **empirical treatment** as per national guidelines.
            - Offer **partner treatment and counseling**.
            - Provide **HIV testing**, hepatitis B vaccination, and condom education.
            - Schedule **follow-up or referral** to appropriate STI/HIV clinic.
            """)

# -----------------------------------
# Footer
# -----------------------------------
st.markdown("---")
st.caption("Developed by Elomi Health Research and Training LLC | AI STI Diagnostic Assistant | Version 1.1 | © 2025")
