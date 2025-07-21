import streamlit as st

st.set_page_config(page_title="Elomi STI Care", layout="centered")

st.title("🧬 Elomi STI Care – STI Diagnostic Assistant")
st.markdown("This tool provides syndromic diagnosis support for sexually transmitted infections (STIs) in low-resource settings.")

symptoms = st.text_area("📝 Enter symptoms", placeholder="e.g., discharge, pelvic pain, rash...")

def diagnose(symptoms):
    s = symptoms.lower()
    if "discharge" in s and "pain" in s:
        return "🔎 Possible Gonorrhea or Chlamydia"
    elif "ulcer" in s or "sore" in s:
        return "🔎 Possible Syphilis"
    elif "warts" in s:
        return "🔎 Possible HPV"
    elif "fever" in s and "rash" in s:
        return "🔎 Possible Acute HIV"
    elif "itching" in s or "irritation" in s:
        return "🔎 Possible Trichomoniasis or Candidiasis"
    else:
        return "❓ No clear match – recommend further clinical evaluation"

if st.button("🧠 Diagnose"):
    if symptoms.strip() == "":
        st.warning("Please enter symptoms.")
    else:
        diagnosis = diagnose(symptoms)
        st.success(diagnosis)
