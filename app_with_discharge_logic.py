
import streamlit as st
import requests

# === Discharge Color Logic ===
def evaluate_discharge_color(color):
    if color == "Thick white (curd-like)":
        return "Candidiasis"
    elif color == "Yellow or green (pus-like)":
        return "Gonorrhea or Trichomoniasis"
    elif color == "Gray (with odor)":
        return "Bacterial vaginosis (non-STI)"
    elif color == "Bloody or brownish":
        return "Consider cervicitis or malignancy – refer"
    elif color == "Clear or watery":
        return "May be normal or non-specific"
    return None

# === Page Setup ===
st.set_page_config(page_title="Elomi STI Care", layout="centered")
st.title("Elomi STI Care – AI-Based Syndromic STI Diagnostic Pipeline")

# === Symptom Selection ===
st.subheader("Symptoms")
selected_symptoms = st.multiselect("Select observed symptoms:", [
    "Vaginal discharge", "Urethral discharge", "Genital ulcer",
    "Lower abdominal pain", "Pain during urination", "Genital itching",
    "Pain during sex", "Anal symptoms"
])
other_symptom = st.text_input("Other symptoms (if any)")

# === Additional logic for discharge color ===
has_discharge = any(symptom for symptom in selected_symptoms if 'discharge' in symptom.lower())

discharge_color = None
discharge_comment = None

if has_discharge:
    discharge_color = st.selectbox(
        "If discharge is present, what is the color or appearance?",
        [
            "— Select —",
            "Thick white (curd-like)",
            "Yellow or green (pus-like)",
            "Gray (with odor)",
            "Bloody or brownish",
            "Clear or watery"
        ]
    )
    if discharge_color and discharge_color != "— Select —":
        discharge_comment = evaluate_discharge_color(discharge_color)
        st.info(f"Discharge Assessment: {discharge_comment}")
