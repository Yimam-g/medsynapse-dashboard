# app.py
# MedSynapse — Professional STI Dashboard with AI + WHO Syndromic Support

import os
import re
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from openai import OpenAI

# -----------------------
# Streamlit Page Config
# -----------------------
st.set_page_config(
    page_title="MedSynapse – STI Dashboard",
    page_icon="🧬",
    layout="wide"
)

# -----------------------
# Assets
# -----------------------
LOGO_PATH = "assets/logo.png"
BANNER_PATH = "assets/banner.png"

# -----------------------
# State Init
# -----------------------
if "cases" not in st.session_state:
    st.session_state["cases"] = []
    st.session_state["case_counter"] = 1

# -----------------------
# Helpers
# -----------------------
def parse_float_safe(x):
    try: return float(str(x).strip())
    except: return None

def parse_bp(bp_str):
    if not bp_str: return None, None
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)\s*", str(bp_str))
    if not m: return None, None
    return int(m.group(1)), int(m.group(2))

def triage_level(temp, sbp, pain, pregnant, hiv, symptoms):
    """Simple WHO-inspired triage logic"""
    # RED
    if temp and temp >= 39: return "RED"
    if sbp and sbp < 90: return "RED"
    if pain >= 8: return "RED"
    if "Lower abdominal pain" in symptoms and pregnant == "Yes": return "RED"
    if "Testicular/scrotal pain/swelling" in symptoms and pain >= 7: return "RED"

    # YELLOW
    if pain >= 5: return "YELLOW"
    if temp and 38 <= temp < 39: return "YELLOW"
    if pregnant == "Yes": return "YELLOW"
    if hiv == "Positive": return "YELLOW"

    # Else GREEN
    return "GREEN"

def triage_badge(level: str):
    colors = {"GREEN": "✅ Routine", "YELLOW": "⚠️ Priority", "RED": "🚨 Urgent"}
    style = {
        "GREEN": "background-color:#d4edda;padding:12px;border-radius:10px;font-weight:bold;",
        "YELLOW": "background-color:#fff3cd;padding:12px;border-radius:10px;font-weight:bold;",
        "RED": "background-color:#f8d7da;padding:12px;border-radius:10px;font-weight:bold;"
    }
    return f"<div style='{style.get(level,'')}'>{colors.get(level,'')}</div>"

# -----------------------
# WHO Rule-based (Expanded, aligned with 2016 WHO Guidelines, strict hierarchy)
# -----------------------
def who_sti_diagnosis(sex, pregnant, symptoms):
    """
    Returns WHO syndromic diagnosis, possible etiologies, treatment, and labs
    Strict hierarchy is applied to avoid misclassification:
      - PID > Vaginal discharge
      - Epididymo-orchitis > Urethral discharge
      - Inguinal bubo > Genital ulcer disease
    """
    s = set(symptoms)

    # --- FEMALE hierarchy ---
    # PID has priority over VDS
    if sex == "Female" and "Lower abdominal pain" in s:
        return {
            "probable": "Pelvic Inflammatory Disease (PID)",
            "possible": "GC/CT, anaerobes",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x14d + Metronidazole 500 mg PO bid x14d",
            "labs": "Pregnancy test; pelvic exam; HIV & syphilis testing"
        }

    if sex == "Female" and "Vaginal discharge" in s:
        return {
            "probable": "Vaginal discharge syndrome",
            "possible": "GC/CT, Trichomonas, BV",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x7d + Metronidazole 500 mg PO bid x7d",
            "labs": "Speculum exam; NAAT for GC/CT; wet mount; HIV/syphilis testing"
        }

    # --- MALE hierarchy ---
    # Epididymo-orchitis has priority over urethral discharge
    if sex == "Male" and "Testicular/scrotal pain/swelling" in s:
        return {
            "probable": "Epididymo-orchitis",
            "possible": "GC/CT, enteric organisms",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x10–14d",
            "labs": "Urinalysis; NAAT for GC/CT; ultrasound if torsion suspected"
        }

    if sex == "Male" and ("Urethral discharge" in s or "Dysuria (painful urination)" in s):
        return {
            "probable": "Urethral discharge syndrome",
            "possible": "Gonorrhea, Chlamydia",
            "treatment": "Ceftriaxone 500 mg IM once + Doxycycline 100 mg PO bid x7d",
            "labs": "NAAT for GC/CT; HIV & syphilis testing"
        }

    # --- BOTH SEXES ---
    # Inguinal bubo has priority over GUD
    if "Inguinal swelling/tenderness" in s:
        return {
            "probable": "Inguinal bubo syndrome",
            "possible": "LGV, chancroid",
            "treatment": "Doxycycline 100 mg PO bid x21d OR Azithromycin 1g PO weekly x3",
            "labs": "Ultrasound if abscess; HIV & syphilis testing"
        }

    if "Genital ulcer(s)" in s:
        return {
            "probable": "Genital ulcer disease",
            "possible": "Syphilis, HSV, ±Chancroid",
            "treatment": "Benzathine Penicillin G 2.4 MU IM once + Acyclovir 400 mg PO tid x7–10d; Add Azithromycin 1g PO if chancroid suspected",
            "labs": "RPR/VDRL; HIV testing; HSV PCR if available"
        }

    # --- Default catch ---
    return {
        "probable": "No clear WHO-defined syndrome",
        "possible": "Consider alternative causes",
        "treatment": "Symptomatic care; reassess",
        "labs": "Screen HIV/syphilis; NAAT if feasible"
    }

# -----------------------
# AI GPT-3.5
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
# Layout with Top Tabs
# -----------------------
tabs = st.tabs([
    "About MedSynapse",
    "Diagnosis",
    "Case History",
    "Export",
    "Analytics Dashboard",
    "Clinical Guidelines",
    "Training & Education"
])
# -----------------------
# About Tab
# -----------------------
with tabs[0]:
    # Logo + Title
    st.image("assets/logo.png", width=140)
    st.markdown("<h2 style='margin-bottom:0;'>MedSynapse</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:18px;color:gray;'>AI-Powered Clinical Dashboard for Syndromic STI Care</p>", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    ### 🌍 Introduction  
    **MedSynapse** is a next-generation digital health solution designed to strengthen clinical decision-making in the management of sexually transmitted infections (STIs).  
    The tool was created in response to the persistent global health challenge posed by STIs, particularly in **low- and middle-income countries (LMICs)** where diagnostic laboratory infrastructure remains limited and syndromic management is the primary standard of care.  

    By integrating **World Health Organization (WHO) syndromic guidelines** with **artificial intelligence (AI) reasoning**, MedSynapse provides clinicians with **real-time, evidence-based recommendations** that enhance accuracy, consistency, and patient outcomes.
    """)

    st.markdown("---")
    st.markdown("""
    ### 🔑 Why MedSynapse Matters  
    - **Bridging the Gap:** Translates WHO syndromic guidelines into digital workflows, reducing variability in clinical practice.  
    - **Supporting Clinicians:** Offers decision support where access to specialists or laboratory confirmation is limited.  
    - **Enhancing Surveillance:** Captures structured case data that can feed into national health information systems.  
    - **Driving Innovation:** Positions itself as a hybrid tool (WHO + AI) that is both practical and research-oriented, opening doors for **funding, publications, and policy uptake**.  
    """)

    st.markdown("---")
    st.markdown("""
    ### ⚙️ How It Works  
    1. Clinicians enter patient demographics, vitals, symptoms, and risk factors.  
    2. The **WHO module** applies standardized syndromic algorithms to suggest a probable diagnosis and recommended treatment.  
    3. The **AI module (GPT-3.5)** contextualizes the information, providing reasoning, confidence scoring, and tailored SMS messages for patients.  
    4. A **triage engine** categorizes cases as **Routine (GREEN)**, **Priority (YELLOW)**, or **Urgent (RED)** to guide clinical action.  
    5. Each case is logged for **future reference, export, and analysis**.  
    """)

    st.markdown("---")
    st.markdown("""
    ### 🧬 Core Features  
    - **Hybrid Diagnosis:** AI reasoning combined with WHO logic for robustness.  
    - **Dynamic Triage:** Automated urgency levels for better resource allocation.  
    - **Patient Messaging:** Generates clear and concise SMS messages for patient education and follow-up.  
    - **Case History & Export:** Maintains structured logs and allows one-click CSV export.  
    - **Research & Analytics Ready:** Future modules will integrate dashboards for real-time surveillance and program evaluation.  
    """)

    st.markdown("---")
    st.markdown("""
    ### 🚀 Vision and Impact  
    MedSynapse is more than just a clinical tool—it is an **innovation platform**.  
    - For clinicians, it ensures **consistent, guideline-based care**.  
    - For patients, it improves **communication and empowerment**.  
    - For researchers and policymakers, it generates **structured, high-quality data** that supports decision-making and future funding proposals.  

    Ultimately, MedSynapse aims to become a **scalable model for AI-powered clinical dashboards** that can be adapted to other health conditions beyond STIs, contributing to stronger health systems worldwide.
    """)

    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:gray;'>
    MedSynapse © 2025 | Elomi Health Research & Training LLC | Incollaboartion with Ethiopian Public Health Institute | Version 2.0 <br>
    📧 Contact: contact@lomiconsulting.com | 🌐 www.elomiconsulting.com <br>
    ⚠️ Disclaimer: MedSynapse supports—but does not replace—professional clinical evaluation.
    </div>
    """, unsafe_allow_html=True)
    
import os

SAVE_PATH = "diagnosis_cases.csv"

# --- Initialize persistent storage ---
if "cases" not in st.session_state:
    if os.path.exists(SAVE_PATH):
        st.session_state["cases"] = pd.read_csv(SAVE_PATH).to_dict("records")
        st.session_state["case_counter"] = len(st.session_state["cases"]) + 1
    else:
        st.session_state["cases"] = []
        st.session_state["case_counter"] = 1

# -----------------------
# Diagnosis Tab
# -----------------------
with tabs[1]:
    st.image(LOGO_PATH, width=120)
    st.subheader("Diagnosis Portal")

    with st.expander("🧍 Patient Demographics & Vitals", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            pid = st.text_input("Patient ID / Name (optional)")
            age = st.number_input("Age",0,120,28)
        with c2:
            sex = st.selectbox("Sex",["Female","Male"])
            pregnant = st.selectbox("Pregnant?",["No","Yes"]) if sex=="Female" else "No"
            hiv = st.selectbox("HIV status",["Unknown","Negative","Positive"])
        with c3:
            temp_c = st.text_input("Temp °C","37.0")
            hr = st.text_input("HR bpm","80")
        with c4:
            bp = st.text_input("BP (e.g. 120/80)","120/80")
            pain = st.select_slider("Pain 0-10",list(range(11)),3)
        temp_val,hr_val = parse_float_safe(temp_c),parse_float_safe(hr)
        sbp,dbp = parse_bp(bp)

    symptoms = st.multiselect("Symptoms",[
        "Urethral discharge","Vaginal discharge","Dysuria (painful urination)",
        "Genital ulcer(s)","Lower abdominal pain","Dyspareunia",
        "Inguinal swelling/tenderness","Testicular/scrotal pain/swelling",
        "Itching/burning","Intermenstrual bleeding","Postcoital bleeding"
    ])
    risks = st.multiselect("Risk factors",[
        "New partner in last 3 months","Multiple partners","Unprotected sex",
        "Known partner with STI","Age <25","Sex worker","MSM","Recent antibiotic use"
    ])
    notes = st.text_area("Additional notes; including specific symptoms, discharge colour, smell, or other related symptoms")
    phone = st.text_input("📱 Phone number (for SMS delivery)")
    sms_lang = st.radio("📱 SMS Language",["English","Amharic (placeholder)"],0)

    if st.button("🔎 Run Diagnosis"):
        who_result = who_sti_diagnosis(sex,pregnant,symptoms)
        triage = triage_level(temp_val,sbp,pain,pregnant,hiv,symptoms)

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

        # --- Triage Card ---
        st.markdown("### 🚑 Triage")
        st.markdown(triage_badge(triage), unsafe_allow_html=True)

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

        # --- Transparency Note ---
        with st.expander("📝 Methodology Note: WHO + AI with Commentary (click to expand)", expanded=False):
            st.markdown("""
            **Purpose.** MedSynapse integrates WHO 2016 **syndromic management** with AI reasoning.  
            This note explains how WHO and AI outputs are displayed and interpreted.

            ---

            ### 1) Syndromic Diagnosis
            - WHO provides the **baseline syndrome classification**.  
            - AI generates a **parallel diagnosis**.  
            - A Commentary column highlights **agreement, differences, or added nuance** (e.g., severity, co-infections).  
            - Non-STI suggestions (e.g., respiratory infections) are discarded automatically.  

            ---

            ### 2) Treatment & Follow-up
            - WHO regimens are **always the anchor**.  
            - AI commentary may reinforce adherence, partner notification, risk reduction, or follow-up.  
            - AI does **not override WHO** recommendations.  

            ---

            ✅ **Outcome:** WHO is preserved as the standard. AI enhances context through **interpretation and commentary**, making the dashboard more informative and clinician-friendly.
            """)

        # --- SMS ---
        sms = ai_out.get("patient_sms","Return if symptoms worsen.")
        if sms_lang=="Amharic (placeholder)":
            sms="[Amharic translation placeholder] "+sms
        if phone:
            sms=f"To {phone}: {sms}"
        st.markdown("### 📱 Patient SMS")
        st.info(sms)

        # --- Save Case ---
        new_case = {
            "CaseID": st.session_state["case_counter"],
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "PatientID": pid,"Age":age,"Sex":sex,"Pregnant":pregnant,"HIV":hiv,
            "Symptoms":";".join(symptoms),"Risks":";".join(risks),
            "WHO_SyndromicDiagnosis": who_dx,
            "AI_SyndromicDiagnosis": ai_dx,
            "AI_Commentary": commentary_diag,
            "WHO_Treatment": who_result.get("treatment","-"),
            "AI_Treatment": ai_out.get("treatment","-"),
            "WHO_Followup": "Partner treatment; condom advice; return if no improvement",
            "AI_Followup": "Partner treatment; condom advice; return if no improvement",
            "AI_Confidence": ai_out.get("confidence","-"),
            "Triage": triage,"SMS": sms
        }

        st.session_state["cases"].append(new_case)
        st.session_state["case_counter"] += 1

        # --- Save persistently to CSV ---
        pd.DataFrame(st.session_state["cases"]).to_csv(SAVE_PATH, index=False)

# -----------------------
# Case History Tab
# -----------------------
with tabs[2]:
    st.subheader("📋 Case History")
    if st.session_state["cases"]:
        st.dataframe(pd.DataFrame(st.session_state["cases"]))
    else:
        st.caption("No cases yet.")
# -----------------------
# Export Tab
# -----------------------
with tabs[3]:
    st.subheader("💾 Export Cases")
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        st.download_button(
            "📥 Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "medsynapse_cases.csv",
            "text/csv"
        )
    else:
        st.caption("No cases saved yet.")

# -----------------------
# Analytics Dashboard Tab
# -----------------------
with tabs[4]:
    st.subheader("📊 Analytics Dashboard (Preview)")
    st.info("This section will display summary charts and insights from saved cases.")
    if st.session_state["cases"]:
        df = pd.DataFrame(st.session_state["cases"])
        st.write("Example metrics:")
        st.metric("Total Cases", len(df))
        st.metric("Female Patients", (df["Sex"]=="Female").sum())
        st.metric("Male Patients", (df["Sex"]=="Male").sum())
        st.bar_chart(df["Triage"].value_counts())
    else:
        st.caption("No data available yet. Run diagnoses to populate analytics.")

# -----------------------
# Clinical Guidelines Tab
# -----------------------
with tabs[5]:
    st.subheader("📚 Clinical Guidelines – WHO 2016 STI Syndromic Management")

    st.markdown("""
    This section provides a practical reference to the **WHO 2016 STI syndromic management guidelines**.  
    These algorithms are designed for **frontline clinicians** in resource-limited settings where laboratory facilities are minimal.  
    """)

    # Urethral Discharge (Male)
    st.markdown("### 👨‍⚕️ Urethral Discharge (Male)")
    st.markdown("""
    **Probable causes:** *Gonorrhea, Chlamydia*  
    **Recommended Treatment:**  
    - **Ceftriaxone 500 mg IM once**  
    - **Doxycycline 100 mg PO bid x7 days**  
    **Laboratory (if available):** NAAT for GC/CT; HIV & syphilis testing  
    **Notes:** Counsel patient and partners, reinforce condom use, partner notification.  
    """)

    st.markdown("---")

    # Vaginal Discharge (Female)
    st.markdown("### 👩 Vaginal Discharge (Female)")
    st.markdown("""
    **Probable causes:** *Gonorrhea, Chlamydia, Trichomonas, Bacterial Vaginosis (BV)*  
    **Recommended Treatment:**  
    - **Ceftriaxone 500 mg IM once**  
    - **Doxycycline 100 mg PO bid x7 days**  
    - **Metronidazole 500 mg PO bid x7 days**  
    **Laboratory (if available):** Speculum exam; NAAT for GC/CT; Wet mount for Trichomonas; HIV/syphilis testing  
    **Notes:** Consider pregnancy status when prescribing doxycycline.  
    """)

    st.markdown("---")

    # Genital Ulcer Disease
    st.markdown("### 🧾 Genital Ulcer Disease")
    st.markdown("""
    **Probable causes:** *Syphilis, Herpes Simplex Virus (HSV), ±Chancroid*  
    **Recommended Treatment:**  
    - **Benzathine Penicillin G 2.4 MU IM once** (syphilis)  
    - **Acyclovir 400 mg PO tid x7–10 days** (HSV)  
    - **Add Azithromycin 1 g PO once** if chancroid suspected  
    **Laboratory (if available):** RPR/VDRL; HIV testing; HSV PCR if available  
    **Notes:** Test and treat partners; always counsel for HIV risk.  
    """)

    st.markdown("---")

    # Pelvic Inflammatory Disease
    st.markdown("### 👩‍⚕️ Pelvic Inflammatory Disease (PID)")
    st.markdown("""
    **Probable causes:** *Gonorrhea, Chlamydia, anaerobes*  
    **Recommended Treatment:**  
    - **Ceftriaxone 500 mg IM once**  
    - **Doxycycline 100 mg PO bid x14 days**  
    - **Metronidazole 500 mg PO bid x14 days**  
    **Laboratory (if available):** Pregnancy test; HIV/syphilis testing; pelvic exam  
    **Notes:** High risk of infertility if untreated – treat aggressively.  
    """)

    st.markdown("---")

    # Inguinal Bubo
    st.markdown("### 🦠 Inguinal Bubo Syndrome")
    st.markdown("""
    **Probable causes:** *Lymphogranuloma venereum (LGV), chancroid*  
    **Recommended Treatment:**  
    - **Doxycycline 100 mg PO bid x21 days**  
    - **OR Azithromycin 1 g PO weekly x3 weeks**  
    **Laboratory (if available):** Ultrasound if abscess suspected; HIV & syphilis testing  
    **Notes:** Surgical drainage only if fluctuant.  
    """)

    st.markdown("---")

    # Epididymo-orchitis
    st.markdown("### 👨 Epididymo-orchitis")
    st.markdown("""
    **Probable causes:** *Gonorrhea, Chlamydia, enteric organisms*  
    **Recommended Treatment:**  
    - **Ceftriaxone 500 mg IM once**  
    - **Doxycycline 100 mg PO bid x10–14 days**  
    **Laboratory (if available):** Urinalysis; NAAT for GC/CT; Ultrasound if torsion suspected  
    **Notes:** Urgent referral if torsion cannot be excluded.  
    """)

    st.markdown("---")

    st.info("⚠️ These guidelines are simplified summaries of WHO 2016 STI syndromic algorithms. Clinicians should adapt based on local epidemiology and drug resistance patterns.")

# -----------------------
# Training & Education Tab
# -----------------------
with tabs[6]:
    st.subheader("🎓 Training & Education – Building Clinical Capacity")

    st.markdown("""
    The **Training & Education** module is designed to provide **continuous professional development** for clinicians, 
    nurses, and community health workers engaged in STI care.  

    By embedding training directly into the MedSynapse dashboard, the tool goes beyond diagnosis to support 
    **skills development, quality improvement, and guideline adherence** in real-world practice.
    """)

    st.markdown("---")

    # Key Learning Features
    st.markdown("### 📘 Planned Learning Features")
    st.markdown("""
    - 🧩 **Case Studies & Quizzes**  
      Interactive case scenarios to test knowledge on STI syndromes, differential diagnosis, and treatment decisions.  

    - ❓ **Frequently Asked Questions (FAQs)**  
      Clear answers to common clinical dilemmas (e.g., "What if the patient is pregnant?", 
      "When should I suspect antimicrobial resistance?").  

    - 🏥 **Clinical Mini-Modules**  
      Short, structured training sessions covering:  
        • WHO syndromic algorithms  
        • Rational use of antibiotics  
        • Partner notification and counseling  
        • Infection prevention and control  

    - 💻 **Interactive Tutorials**  
      Step-by-step simulations that mirror real patient encounters, guiding clinicians from 
      history taking → triage → treatment → follow-up.  
    """)

    st.markdown("---")

    # Future Integration
    st.markdown("### 🌐 Future Integration")
    st.markdown("""
    - **E-Learning Platform:** Link MedSynapse with a full LMS (Learning Management System) to track progress and issue certificates.  
    - **Offline Mode:** Provide downloadable training modules for clinicians in low-connectivity areas.  
    - **Accreditation:** Explore partnerships with Ministries of Health or academic institutions to 
      accredit training for CME/CPD credits.  
    """)

    st.markdown("---")

    # Goal Statement
    st.markdown("""
    ✅ **Goal:** Position MedSynapse as not only a diagnostic decision support tool, 
    but also a **capacity-building ecosystem** that empowers clinicians with knowledge, skills, 
    and tools to deliver high-quality STI care in any setting.
    """)

    st.info("Training and education content is under development. Pilot modules will be added in the next release.")

