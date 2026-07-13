import streamlit as st
import google.generativeai as genai
import yaml
import json

st.set_page_config(page_title="Web-to-Quiz Architect", layout="wide")
st.title("Web-to-Quiz Architect 🛠️")

# --- API KEY HANDLING ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_sidebar = st.sidebar.text_input("Enter Gemini API Key:", type="password")
    api_key = api_sidebar if api_sidebar else None

if api_key:
    genai.configure(api_key=api_key)
else:
    st.info("👉 Please ensure your Gemini API Key is set to activate the app.")
    st.stop()

# --- STEP 1: CONTEXT PARAMS ---
col1, col2 = st.columns([1, 3])
with col1:
    quiz_id_input = st.text_input("Quiz ID:", value="101", placeholder="e.g., 101")
with col2:
    web_url = st.text_input("Paste Webpage URL here:", placeholder="https://...")

# --- STEP 2: AI GENERATION ---
if st.button("Generate Resource and Quiz", type="primary"):
    if not web_url:
        st.warning("Please provide a valid URL.")
    else:
        status_placeholder = st.empty()
        
        system_instruction = (
            "You are an expert UK secondary school science teacher and GCSE examiner. "
            "Your task is to generate educational content calibrated to the UK GCSE standard (14-15 year olds)."
        )
        
        prompt = f"""
        Analyze the content at this URL: {web_url}

        Generate a JSON object containing:
        1. "resource_text": A 300-400 word educational resource in Markdown format covering the topic.
        2. "title": A descriptive title for the assessment.
        3. "questions": Exactly 15 multiple choice objects. Each must have:
           "text", "A", "B", "C", "D", 
           "answer" (exact text of correct option), 
           "explanation" (GCSE-level scientific explanation), 
           "points" (1).
        4. "long_answer": Exactly 1 object:
           "text" (A 6-mark question using command terms like 'Explain' or 'Evaluate'),
           "rubric" (GCSE mark scheme levels L1-L3),
           "points" (6).

        Strict JSON structure:
        {{
          "resource_text": "...",
          "title": "...",
          "questions": [...],
          "long_answer": {{ ... }}
        }}
        """
        
        generation_config = genai.GenerationConfig(response_mime_type="application/json", temperature=0.2)
        
        with st.spinner("Architecting resource and quiz..."):
            try:
                model = genai.GenerativeModel(model_name='gemini-2.0-flash', system_instruction=system_instruction)
                response = model.generate_content(prompt, generation_config=generation_config)
                compiled_data = json.loads(response.text)
                
                st.session_state['resource_text'] = compiled_data.get('resource_text', '')
                st.session_state['quiz_title'] = compiled_data.get('title', 'Assessment')
                st.session_state['quiz_data'] = compiled_data.get('questions', [])
                st.session_state['long_answer_data'] = compiled_data.get('long_answer', {})
                st.session_state['saved_url'] = web_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                status_placeholder.success("🎉 Content and assessment generated!")
            except Exception as e:
                st.error(f"Generation failed: {e}")

# --- REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Edit")
    # (Existing editing logic remains the same for consistency)
    # ... [Review/Edit interface logic] ...

    # --- YAML EXPORT ---
    st.divider()
    yaml_data = {
        "quiz_id": quiz_id_input,
        "web_url": st.session_state['saved_url'],
        "title": st.session_state['quiz_title'],
        "resource_text": st.session_state['resource_text'],
        "multiple_choice": st.session_state['quiz_data'],
        "long_answer": st.session_state['long_answer_data']
    }
    
    st.download_button(
        label=f"💾 Download QUIZ_{quiz_id_input}.yaml",
        data=yaml.dump(yaml_data, allow_unicode=True, sort_keys=False),
        file_name=f"QUIZ_{quiz_id_input}.yaml",
        mime="text/yaml"
    )
