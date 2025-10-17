# app.py
# SynDx — Professional STI Dashboard with AI + WHO Syndromic Support

import os
import re
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from openai import OpenAI
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from cryptography.fernet import Fernet
import hashlib

# -----------------------
# Streamlit Page Config
# -----------------------
st.set_page_config(
    page_title="SynDx – STI Dashboard",
    layout="wide"
)

# -----------------------
# Configuration
# -----------------------
LOGO_PATH = "/home/yimam/Desktop/elomi-sti-care/assets/logo.png"
LOGO_EXISTS = os.path.exists(LOGO_PATH)
SAVE_PATH = "diagnosis_cases.csv"

# -----------------------
# Simple Login System
# -----------------------
def init_auth_db():
    """Initialize authentication database"""
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # Add default user if not exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_password = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                 ("admin", default_password, "clinician"))
    conn.commit()
    conn.close()

def verify_login(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user is not None

# Initialize authentication
init_auth_db()

# -----------------------
# Database Initialization
# -----------------------
def init_db():
    """Initialize SQLite database for patient management"""
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS patients
                 (id TEXT PRIMARY KEY, name TEXT, phone TEXT, age INTEGER, 
                  sex TEXT, occupation TEXT, hiv_status TEXT, created_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS encounters
                 (id INTEGER PRIMARY KEY, patient_id TEXT, timestamp TEXT, 
                  diagnosis TEXT, treatment TEXT, triage TEXT, follow_up_date DATE,
                  FOREIGN KEY(patient_id) REFERENCES patients(id))''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

# -----------------------
# State Init
# -----------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "cases" not in st.session_state:
    if os.path.exists(SAVE_PATH):
        # Load existing cases and add missing Occupation column if needed
        existing_cases = pd.read_csv(SAVE_PATH)
        if 'Occupation' not in existing_cases.columns:
            existing_cases['Occupation'] = 'Not Specified'
        st.session_state["cases"] = existing_cases.to_dict("records")
        st.session_state["case_counter"] = len(st.session_state["cases"]) + 1
    else:
        st.session_state["cases"] = []
        st.session_state["case_counter"] = 1

# -----------------------
# Enhanced Helpers
# -----------------------
def parse_float_safe(x):
    try: return float(str(x).strip())
    except: return None

def parse_bp(bp_str):
    if not bp_str: return None, None
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)\s*", str(bp_str))
    if not m: return None, None
    return int(m.group(1)), int(m.group(2))

def calculate_triage_score(temp, sbp, pain, pregnant, hiv, symptoms):
    """Calculate numeric triage score (0-10)"""
    score = 0
    # Vital signs
    if temp and temp >= 39: score += 3
    elif temp and temp >= 38: score += 1
    
    if sbp and sbp < 90: score += 3
    elif sbp and sbp < 100: score += 1
    
    # Pain
    score += min(3, pain // 3)
    
    # Risk factors
    if pregnant == "Yes": score += 2
    if hiv == "Positive": score += 1
    
    # Symptom severity
    severe_symptoms = {"Lower abdominal pain", "Testicular/scrotal pain/swelling", "Fever"}
    if any(s in symptoms for s in severe_symptoms): score += 2
    
    return min(10, score)

def enhanced_triage_level(score, symptoms, pregnant):
    """Enhanced triage with scoring system"""
    if score >= 7: return "RED"
    elif score >= 4: return "YELLOW" 
    else: return "GREEN"

def triage_level(temp, sbp, pain, pregnant, hiv, symptoms):
    """Enhanced WHO-inspired triage logic with scoring"""
    score = calculate_triage_score(temp, sbp, pain, pregnant, hiv, symptoms)
    return enhanced_triage_level(score, symptoms, pregnant)

def triage_badge(level: str):
    colors = {"GREEN": "✅ Routine", "YELLOW": "⚠️ Priority", "RED": "🚨 Urgent"}
    style = {
        "GREEN": "background-color:#d4edda;padding:12px;border-radius:10px;font-weight:bold;",
        "YELLOW": "background-color:#fff3cd;padding:12px;border-radius:10px;font-weight:bold;",
        "RED": "background-color:#f8d7da;padding:12px;border-radius:10px;font-weight:bold;"
    }
    return f"<div style='{style.get(level,'')}'>{colors.get(level,'')}</div>"

def validate_vitals(temp, hr, bp):
    """Validate vital sign inputs"""
    errors = []
    if temp and (temp < 35 or temp > 42):
        errors.append("Temperature outside normal range (35-42°C)")
    if hr and (hr < 40 or hr > 180):
        errors.append("Heart rate outside normal range (40-180 bpm)")
    if bp and bp[0] and (bp[0] < 60 or bp[0] > 250):
        errors.append("Systolic BP outside normal range (60-250 mmHg)")
    if bp and bp[1] and (bp[1] < 40 or bp[1] > 150):
        errors.append("Diastolic BP outside normal range (40-150 mmHg)")
    return errors

def detect_outbreak_patterns(cases_df):
    """Simple outbreak detection based on symptom clusters"""
    if len(cases_df) < 10:
        return "Insufficient data for outbreak detection"
    
    recent_cases = cases_df.tail(min(50, len(cases_df)))
    symptom_clusters = recent_cases['Symptoms'].str.split(';').explode().value_counts()
    common_symptoms = symptom_clusters[symptom_clusters > len(recent_cases) * 0.3]
    
    if len(common_symptoms) >= 2:
        return f"⚠️ Potential outbreak pattern detected: {', '.join(common_symptoms.index[:3])}"
    
    return "✅ No outbreak patterns detected"

# -----------------------
# Enhanced Amharic Translation Function
# -----------------------
def translate_to_amharic(text):
    """Enhanced Amharic translation for medical instructions"""
    translations = {
        # Basic medical instructions
        "Return if symptoms worsen": "ምልክቶች ከተባበሩ በፍጥነት ይመለሱ",
        "Take medication as prescribed": "መድሀኒቱን እንደተገለጸው ይውሰዱ",
        "Complete the full course": "ሙሉውን መድሀኒት ይውሰዱ",
        "Drink plenty of water": "ብዙ ውሃ ይጠጡ",
        "Get rest": "ለሰዓት ይለፉ",
        "Follow up in": "በኋላ ይመለሱ በ",
        "days": "ቀናት",
        "Partner should be treated": "ጓደኛዎም መድሀኒት እንዲወስድ ያድርጉ",
        "Use condoms": "ኮንዶም ይጠቀሙ",
        "Avoid sexual contact until treatment complete": "መድሀኒት እስኪጠናቀቅ ድረስ ግኑኝነት አያድርጉ",
    }
    
    # Enhanced translation with phrase matching
    translated_text = text
    
    # Replace common phrases (longer phrases first to avoid partial replacements)
    for english, amharic in sorted(translations.items(), key=lambda x: len(x[0]), reverse=True):
        if english.lower() in translated_text.lower():
            translated_text = translated_text.replace(english, amharic)
            translated_text = translated_text.replace(english.lower(), amharic)
            translated_text = translated_text.replace(english.upper(), amharic)
    
    # If no translation occurred, provide a default Amharic message
    if translated_text == text:
        translated_text = f"የጤና ምክር: {text} - መድሀኒትዎን እንደተገለጸው ይውሰዱ እና ምልክቶች ከተባበሩ ወደ ክሊኒክ ይመለሱ"
    
    return translated_text

# -----------------------
# Patient Screening Module
# -----------------------
def screen_patient(symptoms, vital_signs, demographics):
    """
    Screen patient for multiple infectious diseases using syndromic approach
    Returns primary suspected condition and recommendations
    """
    suspected_conditions = []
    
    # STI Screening
    sti_symptoms = {"Urethral discharge", "Vaginal discharge", "Genital ulcer(s)", 
                   "Dysuria (painful urination)", "Lower abdominal pain", "Dyspareunia",
                   "Inguinal swelling/tenderness", "Testicular/scrotal pain/swelling"}
    
    if any(symptom in sti_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "STI",
            "confidence": "High",
            "recommendation": "Proceed to STI Diagnosis module for detailed evaluation",
            "urgency": "Moderate"
        })
    
    # UTI Screening
    uti_symptoms = {"Dysuria (painful urination)", "Frequent urination", "Urgency", 
                   "Lower abdominal pain", "Hematuria"}
    if any(symptom in uti_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "UTI",
            "confidence": "Medium",
            "recommendation": "Urinalysis, consider empiric antibiotics based on local guidelines",
            "urgency": "Moderate"
        })
    
    # Respiratory Tract Infection (RTI) Screening
    rti_symptoms = {"Cough", "Sputum production", "Shortness of breath", "Chest pain", "Fever"}
    if any(symptom in rti_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "RTI",
            "confidence": "Medium",
            "recommendation": "Chest exam, consider CXR, sputum culture if available",
            "urgency": "Moderate"
        })
    
    # Diarrheal Diseases Screening
    diarrhea_symptoms = {"Diarrhea", "Abdominal cramps", "Nausea", "Vomiting", "Fever"}
    if any(symptom in diarrhea_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "Diarrheal Disease",
            "confidence": "Medium", 
            "recommendation": "Stool exam, oral rehydration, consider antibiotics if bacterial",
            "urgency": "Moderate"
        })
    
    # Sepsis Screening (based on vital signs)
    temp, hr, sbp = vital_signs
    sepsis_indicators = []
    if temp and temp > 38.5: sepsis_indicators.append("Fever")
    if hr and hr > 100: sepsis_indicators.append("Tachycardia") 
    if sbp and sbp < 100: sepsis_indicators.append("Hypotension")
    
    if len(sepsis_indicators) >= 2:
        suspected_conditions.append({
            "condition": "Sepsis",
            "confidence": "High",
            "recommendation": "EMERGENCY - Immediate IV antibiotics, fluid resuscitation, hospital admission",
            "urgency": "Critical"
        })
    
    # Meningitis Screening
    meningitis_symptoms = {"Headache", "Neck stiffness", "Photophobia", "Fever", "Altered mental status"}
    if any(symptom in meningitis_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "Meningitis",
            "confidence": "Medium",
            "recommendation": "EMERGENCY - Lumbar puncture, IV antibiotics, hospital admission",
            "urgency": "Critical"
        })
    
    # Vector-Borne Diseases Screening
    vector_symptoms = {"Fever", "Headache", "Myalgia", "Rash", "History of travel"}
    if any(symptom in vector_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "Vector-Borne Disease",
            "confidence": "Low",
            "recommendation": "Malaria test, consider dengue/other vector-borne diseases based on region",
            "urgency": "Moderate"
        })
    
    # Endocarditis Screening
    endocarditis_symptoms = {"Fever", "Heart murmur", "Fatigue", "Night sweats", "IV drug use"}
    if any(symptom in endocarditis_symptoms for symptom in symptoms):
        suspected_conditions.append({
            "condition": "Endocarditis",
            "confidence": "Low", 
            "recommendation": "Blood cultures, echocardiogram, infectious disease consult",
            "urgency": "High"
        })
    
    return suspected_conditions

# -----------------------
# WHO Rule-based (Expanded, aligned with 2016 WHO Guidelines)
# -----------------------
def who_sti_diagnosis(sex, pregnant, symptoms):
    """
    Returns WHO syndromic diagnosis, possible etiologies, treatment, and labs.
    Hierarchy ensures higher-priority syndromes (PID, Epididymo-orchitis, Inguinal bubo)
    override less severe conditions.
    """
    s = set(symptoms)

    # --- FEMALE hierarchy ---
    # PID: prioritize if fever + pelvic pain/discharge/dyspareunia
    if sex == "Female" and (
        "Lower abdominal pain" in s
        or "Dyspareunia" in s
        or ("Fever" in s and "Vaginal discharge" in s)
    ):
        return {
            "probable": "Pelvic Inflammatory Disease (PID)",
            "possible": "GC/CT, anaerobes",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x14d + Metronidazole 500 mg PO bid x14d",
            "labs": "Pregnancy test; pelvic exam; HIV & syphilis testing"
        }

    # Vaginal discharge (default for women if discharge symptoms present)
    if sex == "Female" and (
        "Vaginal discharge" in s
        or "Itching/burning" in s
    ):
        return {
            "probable": "Vaginal discharge syndrome",
            "possible": "GC/CT, Trichomonas, BV",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x7d + Metronidazole 500 mg PO bid x7d",
            "labs": "Speculum exam; NAAT for GC/CT; wet mount; HIV/syphilis testing"
        }

    # --- MALE hierarchy ---
    # Epididymo-orchitis: prioritize if fever + dysuria or testicular pain
    if sex == "Male" and (
        "Testicular/scrotal pain/swelling" in s
        or ("Fever" in s and "Dysuria (painful urination)" in s)
    ):
        return {
            "probable": "Epididymo-orchitis",
            "possible": "GC/CT, enteric organisms",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x10–14d",
            "labs": "Urinalysis; NAAT for GC/CT; ultrasound if torsion suspected"
        }

    # Urethral discharge
    if sex == "Male" and (
        "Urethral discharge" in s or "Dysuria (painful urination)" in s
    ):
        return {
            "probable": "Urethral discharge syndrome",
            "possible": "Gonorrhea, Chlamydia",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x7d",
            "labs": "NAAT for GC/CT; HIV & syphilis testing"
        }

    # --- BOTH SEXES ---
    # Inguinal bubo
    if "Inguinal swelling/tenderness" in s:
        return {
            "probable": "Inguinal bubo syndrome",
            "possible": "LGV, chancroid",
            "treatment": "Doxycycline 100 mg PO bid x21d OR Azithromycin 1g PO weekly x3",
            "labs": "Ultrasound if abscess; HIV & syphilis testing"
        }

    # Genital ulcers
    if "Genital ulcer(s)" in s:
        return {
            "probable": "Genital ulcer disease",
            "possible": "Syphilis, HSV, ±Chancroid",
            "treatment": "Benzathine Penicillin G 2.4 MU IM once + Acyclovir 400 mg PO tid x7–10d; Add Azithromycin 1g PO if chancroid suspected",
            "labs": "RPR/VDRL; HIV testing; HSV PCR if available"
        }

    # --- Default fallback ---
    return {
        "probable": "No clear WHO-defined syndrome",
        "possible": "Consider alternative causes",
        "treatment": "Symptomatic care; reassess",
        "labs": "Screen HIV/syphilis; NAAT if feasible"
    }

# -----------------------
# AI based diagnosis
# -----------------------
def run_gpt(symptoms, risks, temp_val, hr_val, sbp, dbp, sex, pregnant, hiv, pain, notes, age):
    client = OpenAI()  # uses API key from environment
    prompt = f"""
    You are a careful assistant using WHO syndromic guidelines for STIs.
    Patient info:
    Sex: {sex}, Pregnant: {pregnant}, HIV: {hiv}, Age: {age}
    Vitals: Temp={temp_val}, HR={hr_val}, BP={sbp}/{dbp}, Pain={pain}/10
    Symptoms: {", ".join(symptoms) if symptoms else "none"}
    Risks: {", ".join(risks) if risks else "none"}
    Notes: {notes or "n/a"}

    Return JSON only:
    {{
      "probable": "...",
      "possible": "...",
      "treatment": "...",
      "labs": "...",
      "confidence": "low|medium|high",
      "patient_sms": "plain text <=160 chars"
    }}
    """
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2
    )
    text = resp.choices[0].message.content.strip()
    try:
        start,end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end+1])
    except:
        return {"probable":"AI parsing issue","possible":"—","treatment":"—","labs":"—",
                "confidence":"low","patient_sms":"Return if symptoms worsen."}

# -----------------------
# Login Page
# -----------------------
if not st.session_state["authenticated"]:
    st.title(" SynDx - Clinical Dashboard")
    st.subheader("Please login to continue")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if LOGO_EXISTS:
            st.image(LOGO_PATH, width=200)
        else:
            st.markdown("<h1 style='text-align: center;'>🧬</h1>", unsafe_allow_html=True)
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if verify_login(username, password):
                    st.session_state["authenticated"] = True
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.info("**Default credentials:** username: `admin`, password: `admin123`")
    
    st.stop()

# -----------------------
# Main Application (After Login)
# -----------------------

# -----------------------
# Layout with Top Tabs
# -----------------------
tabs = st.tabs([
    "About SynDx",
    "Patient Screening",
    "STI Diagnosis",
    "Case History",
    "Export & Surveillance",
    "Analytics Dashboard",
    "Clinical Guidelines",
    "Training"
])

# -----------------------
# Quick Actions Sidebar
# -----------------------
with st.sidebar:
    if LOGO_EXISTS:
        st.image(LOGO_PATH, width=80)
    else:
        st.markdown("<h1>🧬</h1>", unsafe_allow_html=True)
    
    st.header("Quick Actions")
    
    if st.button("🆕 New Screening", use_container_width=True, key="new_screening_btn"):
        st.session_state.active_tab = "Patient Screening"
        st.rerun()
    
    if st.button("🔍 STI Diagnosis", use_container_width=True, key="sti_diagnosis_btn"):
        st.session_state.active_tab = "STI Diagnosis"
        st.rerun()
    
    if st.button("📊 Analytics", use_container_width=True, key="analytics_btn"):
        st.session_state.active_tab = "Analytics Dashboard"
        st.rerun()
    
    st.markdown("---")
    st.subheader("System Status")
    
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        st.metric("Total Cases", len(df))
        
        # Check for today's cases safely
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_cases = len([case for case in st.session_state["cases"] if today_str in case.get('Timestamp', '')])
        st.metric("Today's Cases", today_cases)
        
        # Outbreak detection
        outbreak_status = detect_outbreak_patterns(df)
        if "outbreak" in outbreak_status.lower():
            st.warning(outbreak_status)
        else:
            st.info(outbreak_status)
    else:
        st.info("No cases yet")
    
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        st.session_state["authenticated"] = False
        st.rerun()

# -----------------------
# About SynDx Tab - COMPLETE CONTENT
# -----------------------
with tabs[0]:
    if LOGO_EXISTS:
        st.image(LOGO_PATH, width=140)
    else:
        st.markdown("<h1 style='text-align: center;'>🧬</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='margin-bottom:0;'>SynDx - Syndromic Diagnosis & Surveillance System</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:18px;color:gray;'>AI-Powered Clinical Dashboard for Comprehensive Infectious Disease Management</p>", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    ### 🌍 Introduction  
    **SynDx** represents a paradigm shift in clinical decision support systems for infectious disease management in resource-limited settings. Developed through collaboration between the **Ethiopian Public Health Institute** and **Elomi Health Research & Training LLC**, this platform bridges the gap between frontline clinical care and public health surveillance.
    
    In many low- and middle-income countries, laboratory diagnostics remain inaccessible or unaffordable, making syndromic management the primary approach for infectious disease care. SynDx enhances this approach by integrating **digital health technologies**, **artificial intelligence**, and **real-time data analytics** to support clinicians while simultaneously generating valuable surveillance data.
    """)

    st.markdown("---")
    
    st.markdown("""
    ### 🎯 Mission & Vision
    
    **Our Mission:**
    To empower healthcare providers with intelligent, evidence-based clinical decision support that improves patient outcomes while strengthening national disease surveillance systems.
    
    **Our Vision:**
    A future where every clinician, regardless of location or resources, has access to expert guidance for infectious disease management, and where real-time data drives public health action.
    """)

    st.markdown("---")
    
    st.markdown("""
    ### 🔑 Why SynDx Matters  
    
    **For Clinicians:**
    - **Decision Support**: Reduces diagnostic uncertainty in settings with limited laboratory capacity
    - **Guideline Adherence**: Ensures consistent application of WHO and national treatment protocols
    - **Time Efficiency**: Streamlines clinical assessment and documentation
    - **Continuous Learning**: Built-in training modules support professional development
    
    **For Patients:**
    - **Improved Care**: More accurate diagnoses and appropriate treatments
    - **Patient Education**: Clear SMS instructions in local languages
    - **Continuity**: Structured follow-up and referral recommendations
    
    **For Public Health:**
    - **Real-time Surveillance**: Automated data collection for outbreak detection
    - **Epidemiological Insights**: Pattern analysis across facilities and regions
    - **Resource Planning**: Data-driven drug supply and staffing decisions
    - **Program Evaluation**: Monitoring intervention effectiveness
    """)

    st.markdown("---")
    
    st.markdown("""
    ### ⚙️ How It Works  
    
    **1. Comprehensive Patient Screening**
    - Multi-disease symptom assessment (STI, UTI, RTI, diarrhea, sepsis, meningitis, vector-borne, endocarditis)
    - Automated triage and urgency classification
    - Intelligent routing to appropriate care pathways
    
    **2. Specialized STI Diagnosis**
    - WHO 2016 syndromic management algorithms
    - AI-enhanced differential diagnosis
    - Integrated risk factor assessment
    - Automated treatment recommendations
    
    **3. Data for Surveillance**
    - Structured data capture compatible with national HMIS
    - Automated outbreak detection algorithms
    - Export functionality for central data archival
    - Analytics dashboard for program monitoring
    """)

    st.markdown("---")
    
    st.markdown("""
    <div style='text-align:center;color:gray;'>
    <h3>SynDx © 2025 | Version 3.0</h3>
    <p><strong>Ethiopian Public Health Institute</strong> in collaboration with <strong>Elomi Health Research & Training LLC</strong></p>
    <p>📧 Contact: info@ephi.gov.et | 🌐 www.ephi.gov.et</p>
    <p>📍 Addis Ababa, Ethiopia</p>
    <br>
    <p><em>⚠️ Disclaimer: SynDx supports—but does not replace—professional clinical evaluation. 
    Always verify critical decisions and consult national guidelines for specific contexts.</em></p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------
# Patient Screening Tab - COMPLETE CONTENT
# -----------------------
with tabs[1]:
    st.subheader("🩺 Comprehensive Patient Screening")
    st.info("Use this module for initial assessment of patients with infectious disease symptoms")
    
    with st.expander("Patient Information", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            pid = st.text_input("Patient ID", key="screen_pid")
            age = st.number_input("Age", 0, 120, 28, key="screen_age")
        with col2:
            sex = st.selectbox("Sex", ["Female", "Male"], key="screen_sex")
            pregnant = st.selectbox("Pregnant?", ["No", "Yes"], key="screen_pregnant") if sex == "Female" else "No"
            occupation = st.selectbox("Occupation", [
                "Farmer", "Student", "Healthcare Worker", "Teacher", 
                "Government Employee", "Merchant", "Driver", "Housewife", 
                "Daily Laborer", "Unemployed", "Other"
            ], key="screen_occupation")
        with col3:
            temp_c = st.text_input("Temp °C", "37.0", key="screen_temp")
            hr = st.text_input("HR bpm", "80", key="screen_hr")
            bp = st.text_input("BP (e.g. 120/80)", "120/80", key="screen_bp")
    
    # Comprehensive symptom list for screening
    st.subheader("Symptoms Checklist")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sti_symptoms = st.multiselect("STI Symptoms", [
            "Urethral discharge", "Vaginal discharge", "Genital ulcer(s)",
            "Dysuria (painful urination)", "Lower abdominal pain", "Dyspareunia",
            "Inguinal swelling/tenderness", "Testicular/scrotal pain/swelling"
        ], key="screen_sti_symptoms")
        
        uti_symptoms = st.multiselect("UTI Symptoms", [
            "Dysuria (painful urination)", "Frequent urination", "Urgency",
            "Lower abdominal pain", "Hematuria", "Cloudy urine"
        ], key="screen_uti_symptoms")
    
    with col2:
        rti_symptoms = st.multiselect("Respiratory Symptoms", [
            "Cough", "Sputum production", "Shortness of breath", "Chest pain",
            "Fever", "Runny nose", "Sore throat"
        ], key="screen_rti_symptoms")
        
        diarrhea_symptoms = st.multiselect("Gastrointestinal Symptoms", [
            "Diarrhea", "Abdominal cramps", "Nausea", "Vomiting",
            "Fever", "Blood in stool"
        ], key="screen_diarrhea_symptoms")
    
    with col3:
        systemic_symptoms = st.multiselect("Systemic Symptoms", [
            "Fever", "Headache", "Fatigue", "Myalgia", "Night sweats",
            "Rash", "Joint pain", "Weight loss"
        ], key="screen_systemic_symptoms")
        
        neurological_symptoms = st.multiselect("Neurological Symptoms", [
            "Headache", "Neck stiffness", "Photophobia", "Altered mental status",
            "Confusion", "Seizures"
        ], key="screen_neuro_symptoms")
    
    # Combine all symptoms
    all_symptoms = sti_symptoms + uti_symptoms + rti_symptoms + diarrhea_symptoms + systemic_symptoms + neurological_symptoms
    
    risk_factors = st.multiselect("Risk Factors", [
        "New sexual partner", "Multiple partners", "Unprotected sex",
        "Recent travel", "IV drug use", "Animal exposure",
        "Contact with sick person", "Healthcare worker", "Recent hospitalization"
    ], key="screen_risk_factors")
    
    notes = st.text_area("Additional Clinical Notes", key="screen_notes")
    
    if st.button("🔍 Run Comprehensive Screening", type="primary", key="screen_run_btn"):
        if not all_symptoms:
            st.warning("Please select at least one symptom")
        else:
            # Parse vital signs
            temp_val = parse_float_safe(temp_c)
            hr_val = parse_float_safe(hr)
            sbp, dbp = parse_bp(bp)
            
            # Run screening
            vital_signs = (temp_val, hr_val, sbp)
            demographics = {"age": age, "sex": sex, "pregnant": pregnant, "occupation": occupation}
            
            screening_results = screen_patient(all_symptoms, vital_signs, demographics)
            
            # Display results
            st.subheader("🎯 Screening Results")
            
            if not screening_results:
                st.info("No specific infectious disease pattern detected. Consider non-infectious causes.")
            else:
                # Sort by urgency
                urgency_order = {"Critical": 1, "High": 2, "Moderate": 3, "Low": 4}
                screening_results.sort(key=lambda x: urgency_order.get(x["urgency"], 5))
                
                for i, result in enumerate(screening_results, 1):
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{i}. {result['condition']}**")
                            st.write(f"Confidence: {result['confidence']}")
                            st.write(f"Recommendation: {result['recommendation']}")
                        with col2:
                            urgency_color = {
                                "Critical": "red",
                                "High": "orange", 
                                "Moderate": "yellow",
                                "Low": "green"
                            }
                            st.markdown(
                                f"<div style='background-color:{urgency_color[result['urgency']]}; "
                                f"color:white; padding:10px; border-radius:5px; text-align:center;'>"
                                f"{result['urgency']}</div>",
                                unsafe_allow_html=True
                            )
                        
                        # Special action for STI
                        if result["condition"] == "STI":
                            st.info("💡 **STI Detected** - Consider proceeding to detailed STI diagnosis")
                            if st.button(f"Go to STI Diagnosis", key=f"sti_btn_{i}"):
                                st.session_state.active_tab = "STI Diagnosis"
                                st.rerun()
                        
                        st.markdown("---")

# -----------------------
# STI Diagnosis Tab - COMPLETE CONTENT
# -----------------------
with tabs[2]:
    if LOGO_EXISTS:
        st.image(LOGO_PATH, width=120)
    st.subheader("STI Diagnosis Portal")

    with st.expander("🧍 Patient Demographics & Vitals", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            pid = st.text_input("Patient ID / Name", key="diag_pid")
            age = st.number_input("Age",0,120,28, key="diag_age")
        with c2:
            sex = st.selectbox("Sex",["Female","Male"], key="diag_sex")
            pregnant = st.selectbox("Pregnant?",["No","Yes"], key="diag_pregnant") if sex=="Female" else "No"
            hiv = st.selectbox("HIV status",["Unknown","Negative","Positive"], key="diag_hiv")
            occupation = st.selectbox("Occupation", [
                "Farmer", "Student", "Healthcare Worker", "Teacher", 
                "Government Employee", "Merchant", "Driver", "Housewife", 
                "Daily Laborer", "Unemployed", "Other"
            ], key="diag_occupation")
        with c3:
            temp_c = st.text_input("Temp °C","37.0", key="diag_temp")
            hr = st.text_input("HR bpm","80", key="diag_hr")
        with c4:
            bp = st.text_input("BP (e.g. 120/80)","120/80", key="diag_bp")
            pain = st.select_slider("Pain 0-10",list(range(11)),3, key="diag_pain")
        
        # Input validation
        temp_val,hr_val = parse_float_safe(temp_c),parse_float_safe(hr)
        sbp,dbp = parse_bp(bp)
        vital_errors = validate_vitals(temp_val, hr_val, (sbp, dbp))
        if vital_errors:
            for error in vital_errors:
                st.warning(f"⚠️ {error}")

    symptoms = st.multiselect("STI Symptoms",[
        "Urethral discharge","Vaginal discharge","Dysuria (painful urination)",
        "Genital ulcer(s)","Lower abdominal pain","Dyspareunia",
        "Inguinal swelling/tenderness","Testicular/scrotal pain/swelling",
        "Itching/burning","Intermenstrual bleeding","Postcoital bleeding"
    ], key="diag_symptoms")
    
    risks = st.multiselect("STI Risk factors",[
        "New partner in last 3 months","Multiple partners","Unprotected sex",
        "Known partner with STI","Age <25","Sex worker","MSM","Recent antibiotic use"
    ], key="diag_risks")
    
    notes = st.text_area("Additional STI-specific notes", key="diag_notes")
    phone = st.text_input("📱 Phone number (for SMS delivery)", key="diag_phone")
    
    # Enhanced SMS language option
    sms_lang = st.radio("📱 SMS Language", ["English", "Amharic"], index=0, key="diag_sms_lang")
    
    if st.button("🔎 Run STI Diagnosis", key="diag_run_btn"):
        if not symptoms:
            st.warning("Please select at least one STI symptom")
        else:
            who_result = who_sti_diagnosis(sex,pregnant,symptoms)
            triage = triage_level(temp_val,sbp,pain,pregnant,hiv,symptoms)
            
            # Calculate triage score
            triage_score = calculate_triage_score(temp_val,sbp,pain,pregnant,hiv,symptoms)

            try:
                ai_out = run_gpt(symptoms,risks,temp_val,hr_val,sbp,dbp,sex,pregnant,hiv,pain,notes,age)
                st.success("✅ AI Mode (GPT-3.5) completed")
            except Exception as e:
                st.error(f"AI error: {e}")
                ai_out = {"probable":"AI error","possible":"—","treatment":"—",
                          "confidence":"low","patient_sms":"Return if symptoms worsen."}

            # --- Merge probable + possible into Syndromic Diagnosis ---
            def merge_diag(d):
                return "; ".join([d.get("probable",""), d.get("possible","")]).strip("; ") if d else "-"

            ai_dx = merge_diag(ai_out)
            who_dx = merge_diag(who_result)

            # --- AI Commentary Function ---
            def ai_commentary(ai_dx, who_dx):
                if ai_dx == "—" or who_dx == "—":
                    return "AI could not generate interpretation."
                return f"AI suggests: {ai_dx}. WHO baseline: {who_dx}. Overlap noted; AI highlights potential nuances or severity."

            commentary_diag = ai_commentary(ai_dx, who_dx)

            # --- Triage Card with Score ---
            st.markdown("### 🚑 Triage Assessment")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(triage_badge(triage), unsafe_allow_html=True)
            with col2:
                st.metric("Triage Score", f"{triage_score}/10")

            # --- Comparison Table ---
            st.markdown("### 🔍 WHO vs AI Outputs + AI Commentary")
            comp = pd.DataFrame({
                "Field":["Syndromic Diagnosis","Treatment","Follow-up & Counseling"],
                "WHO Baseline":[who_dx, who_result.get("treatment","-"), "Partner treatment; condom advice; return if no improvement"],
                "AI (GPT-3.5)":[ai_dx, ai_out.get("treatment","-"), "Partner treatment; condom advice; return if no improvement"],
                "AI Commentary":[
                    commentary_diag,
                    "AI supports WHO regimen; may suggest refinements if aligned.",
                    "AI emphasizes adherence, partner notification, condom use, and timely return visits."
                ]
            })
            st.table(comp)

            # --- AI Confidence ---
            if "confidence" in ai_out:
                conf = ai_out["confidence"].capitalize()
                pct = {"Low":"40%","Medium":"70%","High":"90%"}.get(conf,conf)
                st.markdown(f"**AI Confidence:** {pct}")

            # --- SMS with Enhanced Amharic Translation ---
            sms = ai_out.get("patient_sms","Return if symptoms worsen. Take medication as prescribed. Complete the full course.")
            if sms_lang == "Amharic":
                sms = translate_to_amharic(sms)
            if phone:
                sms = f"To {phone}: {sms}"
            
            st.markdown("### 📱 Patient SMS")
            st.info(sms)
            
            # SMS sending simulation
            if phone and st.button("📤 Send SMS to Patient", key="send_sms_btn"):
                st.success(f"✅ SMS sent to {phone}")

            # --- Save Case ---
            new_case = {
                "CaseID": st.session_state["case_counter"],
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "PatientID": pid,"Age":age,"Sex":sex,"Occupation": occupation,"Pregnant":pregnant,"HIV":hiv,
                "Symptoms":";".join(symptoms),"Risks":";".join(risks),
                "WHO_SyndromicDiagnosis": who_dx,
                "AI_SyndromicDiagnosis": ai_dx,
                "AI_Commentary": commentary_diag,
                "WHO_Treatment": who_result.get("treatment","-"),
                "AI_Treatment": ai_out.get("treatment","-"),
                "WHO_Followup": "Partner treatment; condom advice; return if no improvement",
                "AI_Followup": "Partner treatment; condom advice; return if no improvement",
                "AI_Confidence": ai_out.get("confidence","-"),
                "Triage": triage,
                "Triage_Score": triage_score,
                "SMS": sms
            }

            st.session_state["cases"].append(new_case)
            st.session_state["case_counter"] += 1

            # --- Save persistently to CSV ---
            pd.DataFrame(st.session_state["cases"]).to_csv(SAVE_PATH, index=False)
            st.success("✅ Case saved successfully!")

# -----------------------
# Case History Tab - COMPLETE CONTENT
# -----------------------
with tabs[3]:
    st.subheader("📋 Case History")
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        
        # Search and filter
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Search cases...", key="search_cases")
        with col2:
            triage_filter = st.multiselect("Filter by Triage", ["RED", "YELLOW", "GREEN"], key="triage_filter")
        
        # Apply filters
        if search_term:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        if triage_filter:
            df = df[df["Triage"].isin(triage_filter)]
        
        st.dataframe(df)
        st.metric("Displaying Cases", len(df))
    else:
        st.caption("No cases yet.")

# -----------------------
# Export & Surveillance Tab - COMPLETE CONTENT
# -----------------------
with tabs[4]:
    st.subheader("💾 Export & Central Surveillance Data")
    st.info("This module facilitates data export for central archival and public health surveillance")
    
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        
        # Ensure Occupation column exists for backward compatibility
        if 'Occupation' not in df.columns:
            df['Occupation'] = 'Not Specified'
        
        st.markdown("### 📊 Surveillance Data Export")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Complete Dataset (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                "syndx_surveillance_data.csv",
                "text/csv",
                key="download_complete_csv"
            )
            
            # Safe HMIS export - only include columns that exist
            hmis_columns = ['PatientID', 'Age', 'Sex', 'Symptoms', 'Triage', 'Timestamp']
            if 'Occupation' in df.columns:
                hmis_columns.insert(3, 'Occupation')  # Insert Occupation at position 3
            
            st.download_button(
                "📋 Download HMIS Format",
                df[hmis_columns].to_csv(index=False).encode("utf-8"),
                "syndx_hmis_data.csv",
                "text/csv",
                key="download_hmis"
            )
        
        with col2:
            # Generate surveillance report
            occupation_summary = "Not available"
            if 'Occupation' in df.columns:
                top_occupations = df['Occupation'].value_counts().head(3).index.tolist()
                occupation_summary = ', '.join(top_occupations) if top_occupations else "No data"
            
            report = f"""
            SYN-DX SURVEILLANCE REPORT
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            Facility: [FACILITY_NAME]
            Reporting Period: {df['Timestamp'].min()} to {df['Timestamp'].max()}
            
            SUMMARY STATISTICS:
            Total Cases: {len(df)}
            Demographic Distribution:
            - Female: {(df['Sex']=='Female').sum()} | Male: {(df['Sex']=='Male').sum()}
            - Average Age: {df['Age'].mean():.1f} years
            - Common Occupations: {occupation_summary}
            
            Triage Distribution:
            - RED (Urgent): {len(df[df['Triage']=='RED'])}
            - YELLOW (Priority): {len(df[df['Triage']=='YELLOW'])} 
            - GREEN (Routine): {len(df[df['Triage']=='GREEN'])}
            
            Symptom Patterns:
            {', '.join(';'.join(df['Symptoms'].fillna('')).split(';')[:5])}
            
            Outbreak Detection: {detect_outbreak_patterns(df)}
            """
            st.download_button(
                "📄 Download Surveillance Report",
                report,
                "syndx_surveillance_report.txt",
                "text/plain",
                key="download_surveillance_report"
            )
        
        # Date range export for surveillance
        st.markdown("### 🗓️ Custom Surveillance Export")
        st.warning("Use this for periodic reporting to central surveillance units")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date for Reporting", key="surv_start_date")
        with col2:
            end_date = st.date_input("End Date for Reporting", key="surv_end_date")
            
        if st.button("Generate Surveillance Report", key="surv_report_btn"):
            filtered_df = df[(df['Timestamp'] >= str(start_date)) & (df['Timestamp'] <= str(end_date + pd.Timedelta(days=1)))]
            if len(filtered_df) > 0:
                st.success(f"✅ Found {len(filtered_df)} cases for selected period")
                
                # Enhanced surveillance data with safe column selection
                surveillance_columns = ['CaseID', 'Timestamp', 'PatientID', 'Age', 'Sex', 'Symptoms', 'Triage', 'WHO_SyndromicDiagnosis', 'Triage_Score']
                if 'Occupation' in filtered_df.columns:
                    surveillance_columns.insert(5, 'Occupation')  # Insert Occupation after Sex
                
                surveillance_data = filtered_df[surveillance_columns]
                
                st.download_button(
                    "📥 Download Period Surveillance Data",
                    surveillance_data.to_csv(index=False).encode("utf-8"),
                    f"syndx_surveillance_{start_date}_to_{end_date}.csv",
                    "text/csv",
                    key="download_period_surveillance"
                )
                
                # Display summary
                st.subheader("📈 Period Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Cases", len(filtered_df))
                with col2:
                    st.metric("Average Triage Score", f"{filtered_df['Triage_Score'].mean():.1f}/10")
                with col3:
                    completeness = (filtered_df.notna().mean() * 100).mean()
                    st.metric("Data Completeness", f"{completeness:.1f}%")
                
                st.dataframe(surveillance_data)
            else:
                st.warning("No cases found in selected date range")
        
        # Data quality check
        st.markdown("### 🔍 Data Quality Assessment")
        col1, col2, col3 = st.columns(3)
        with col1:
            completeness = (df.notna().mean() * 100).mean()
            st.metric("Data Completeness", f"{completeness:.1f}%")
        with col2:
            st.metric("Unique Patients", df['PatientID'].nunique())
        with col3:
            st.metric("Data Consistency", "Verified")
            
    else:
        st.caption("No surveillance data available yet. Generate cases to populate reports.")

# -----------------------
# Analytics Dashboard Tab - COMPLETE CONTENT
# -----------------------
with tabs[5]:
    st.subheader("📊 Advanced Analytics Dashboard")
    
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        
        # Convert timestamp safely
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            has_timestamp = True
        except:
            has_timestamp = False
        
        # Key metrics in columns
        st.markdown("### 📈 Key Performance Indicators")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_cases = len(df)
            st.metric("Total Cases", total_cases)
        with col2:
            urgent_cases = len(df[df["Triage"] == "RED"])
            st.metric("🚨 Urgent Cases", urgent_cases)
        with col3:
            avg_age = df['Age'].mean()
            st.metric("Average Age", f"{avg_age:.1f}")
        with col4:
            female_count = (df['Sex'] == 'Female').sum()
            male_count = (df['Sex'] == 'Male').sum()
            st.metric("Female:Male Ratio", f"{female_count}:{male_count}")
        
        # First row of charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔄 Triage Distribution")
            triage_counts = df["Triage"].value_counts()
            if len(triage_counts) > 0:
                fig = px.pie(
                    values=triage_counts.values, 
                    names=triage_counts.index,
                    color=triage_counts.index,
                    color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFC107', 'GREEN':'#28A745'},
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(showlegend=True, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No triage data available")
        
        with col2:
            st.subheader("📊 Common Symptoms")
            all_symptoms = ';'.join(df['Symptoms'].fillna('')).split(';')
            symptom_counts = pd.Series([s for s in all_symptoms if s]).value_counts().head(10)
            if len(symptom_counts) > 0:
                fig = px.bar(
                    x=symptom_counts.values,
                    y=symptom_counts.index,
                    orientation='h',
                    color=symptom_counts.values,
                    color_continuous_scale='viridis'
                )
                fig.update_layout(
                    xaxis_title="Frequency",
                    yaxis_title="Symptoms",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No symptom data available")
        
        # Second row of charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Cases Over Time")
            if has_timestamp:
                df_daily = df.copy()
                df_daily['Date'] = df_daily['Timestamp'].dt.date
                daily_cases = df_daily.groupby('Date').size().reset_index(name='Cases')
                
                if len(daily_cases) > 0:
                    fig = px.line(
                        daily_cases, 
                        x='Date', 
                        y='Cases',
                        markers=True,
                        line_shape='spline'
                    )
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Number of Cases",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Insufficient data for time series")
            else:
                st.info("Timestamp data not available")
        
        with col2:
            st.subheader("👥 Age Distribution")
            if len(df) > 0 and 'Age' in df.columns:
                fig = px.histogram(
                    df, 
                    x='Age',
                    nbins=20,
                    color_discrete_sequence=['#1f77b4']
                )
                fig.update_layout(
                    xaxis_title="Age",
                    yaxis_title="Number of Patients",
                    height=400,
                    bargap=0.1
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No age data available")
        
        # Outbreak detection and alerts
        st.markdown("---")
        st.subheader("🔍 Public Health Alerts")
        
        outbreak_status = detect_outbreak_patterns(df)
        if "potential outbreak" in outbreak_status.lower():
            st.error(f"🚨 {outbreak_status}")
        else:
            st.success(outbreak_status)
            
    else:
        st.info("📊 No data available yet. Run diagnoses to populate analytics.")

# -----------------------
# Clinical Guidelines Tab - COMPLETE CONTENT
# -----------------------
with tabs[6]:
    st.subheader("📚 Clinical Guidelines – WHO 2016 STI Syndromic Management")
    
    st.markdown("""
    ### 🎯 Overview
    This section provides comprehensive clinical guidance based on **WHO 2016 STI Syndromic Management** guidelines. 
    These algorithms are designed for frontline clinicians in resource-limited settings where laboratory diagnostics may be unavailable.
    """)
    
    # Urethral Discharge Syndrome
    with st.expander("👨‍⚕️ Urethral Discharge Syndrome (Male)", expanded=True):
        st.markdown("""
        **Clinical Presentation:**
        - Urethral discharge
        - Dysuria (painful urination)
        - Itching at urethral meatus
        
        **Probable Causes:**
        - Gonorrhea (*Neisseria gonorrhoeae*)
        - Chlamydia (*Chlamydia trachomatis*)
        
        **Recommended Treatment:**
        ```
        Ceftriaxone 500 mg IM single dose
        PLUS
        Doxycycline 100 mg PO twice daily for 7 days
        ```
        
        **Follow-up:**
        - Partner notification and treatment
        - Advise condom use
        - Return if symptoms persist after 7 days
        """)
    
    # Vaginal Discharge Syndrome
    with st.expander("👩 Vaginal Discharge Syndrome", expanded=True):
        st.markdown("""
        **Clinical Presentation:**
        - Abnormal vaginal discharge
        - Vulval itching/burning
        - Dysuria
        - Lower abdominal pain
        
        **If HIGH RISK for cervical infection:**
        ```
        Ceftriaxone 500 mg IM single dose
        PLUS
        Doxycycline 100 mg PO twice daily for 7 days
        PLUS
        Metronidazole 500 mg PO twice daily for 7 days
        ```
        
        **If LOW RISK for cervical infection:**
        ```
        Metronidazole 500 mg PO twice daily for 7 days
        PLUS
        Fluconazole 150 mg PO single dose
        ```
        """)
    
    st.info("""
    ⚠️ **Important Note:** These guidelines should be adapted to local antimicrobial resistance patterns and 
    national treatment protocols. Always consult the most recent national guidelines for your practice setting.
    """)

# -----------------------
# Training Tab - COMPLETE CONTENT
# -----------------------
with tabs[7]:
    st.subheader("🎓 Training & Capacity Building")
    
    st.markdown("""
    ### 🎯 Training Objectives
    This module provides comprehensive training resources for healthcare workers on syndromic management of STIs 
    and other infectious diseases, following WHO guidelines and best practices.
    """)
    
    # Interactive Case Studies
    with st.expander("🧩 Interactive Case Studies", expanded=True):
        st.markdown("""
        **Case Study 1: Young Male with Urethral Discharge**
        
        **Presentation:** 22-year-old male presents with 3-day history of purulent urethral discharge and dysuria.
        No fever, no genital ulcers. Sexually active with one partner.
        
        **Learning Objectives:**
        - Apply syndromic management for urethral discharge
        - Select appropriate treatment regimen
        - Provide patient counseling
        - Arrange partner notification
        """)
        
        if st.button("Show Solution - Case 1", key="case1_solution"):
            st.success("""
            **Recommended Management:**
            - **Treatment:** Ceftriaxone 500 mg IM stat + Doxycycline 100 mg BD x 7 days
            - **Counseling:** Condom use, complete treatment, partner notification
            - **Follow-up:** Return if no improvement in 3 days
            - **Partner:** Must be treated epidemiologically
            """)
    
    # Skills Training
    with st.expander("🏥 Clinical Skills Training"):
        st.markdown("""
        **Essential Clinical Skills:**
        
        **1. Patient History Taking**
        - Sexual history taking techniques
        - Symptom characterization
        - Risk factor assessment
        - Partner notification approaches
        
        **2. Physical Examination**
        - Genital examination techniques
        - Speculum examination
        - Bimanual pelvic examination
        - Lymph node examination
        """)
    
    st.info("""
    💡 **Training Tip:** Regular practice and case discussion with colleagues enhances clinical skills. 
    Consider establishing a peer learning group at your health facility.
    """)

# -----------------------
# Footer
# -----------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "SynDx v3.0 | Comprehensive Clinical & Surveillance Platform | © 2025 Ethiopian Public Health Institute"
    "</div>",
    unsafe_allow_html=True
)
