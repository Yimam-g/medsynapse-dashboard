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
