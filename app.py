import streamlit as st
import google.generativeai as genai
import trafilatura
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
        
        # Fetch content using trafilatura
        with st.spinner("Fetching content from the web..."):
            downloaded = trafilatura.fetch_url(web_url)
            page_content = trafilatura.extract(downloaded)
        
        if not page_content:
            st.error("Failed to extract content from the URL. Please check the link or try another.")
            st.stop()

        system_instruction = (
            "You are an expert secondary school teacher. "
            "Your task is to generate educational content calibrated to the secondary school standard."
        )
        
        prompt = f"""
        Analyze the following text extracted from a webpage:
        {page_content[:15000]} 

        Generate a JSON object containing:
        1. "resource_text": A 300-400 word educational resource in Markdown format covering the topic.
        2. "title": A descriptive title for the assessment.
        3. "questions": Exactly 15 multiple choice objects. Each must have:
           "text", "A", "B", "C", "D", 
           "answer" (exact text of correct option), 
           "explanation" (a clear educational explanation), 
           "points" (1).
        4. "long_answer": Exactly 1 object:
           "text" (A 6-mark question using appropriate command terms),
           "rubric" (Mark scheme levels L1-L3),
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
                model = genai.GenerativeModel(model_name='gemini-3.1-flash-lite', system_instruction=system_instruction)
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
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    st.subheader("Multiple Choice Questions")
    final_compiled_questions = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Q{i+1}: {q.get('text', '')[:50]}...", expanded=False):
            e_text = st.text_input(f"Question {i+1}", value=q.get('text', ''), key=f"q_{i}")
            e_A = st.text_input(f"A", value=q.get('A', ''), key=f"A_{i}")
            e_B = st.text_input(f"B", value=q.get('B', ''), key=f"B_{i}")
            e_C = st.text_input(f"C", value=q.get('C', ''), key=f"C_{i}")
            e_D = st.text_input(f"D", value=q.get('D', ''), key=f"D_{i}")
            
            e_ans = st.text_input(f"Correct Answer Text", value=q.get('answer', ''), key=f"ans_{i}")
            e_exp = st.text_area(f"Explanation", value=q.get('explanation', ''), key=f"exp_{i}")
            e_pts = st.number_input(f"Points", value=int(q.get('points', 1)), key=f"pts_{i}")
            
            if st.checkbox(f"Include Q{i+1}", value=True, key=f"keep_{i}"):
                final_compiled_questions.append({
                    "question_num": len(final_compiled_questions) + 1,
                    "text": e_text, "A": e_A, "B": e_B, "C": e_C, "D": e_D,
                    "answer": e_ans, "points": e_pts, "explanation": e_exp
                })

    st.subheader("Long Answer Question")
    la = st.session_state.get('long_answer_data', {})
    with st.expander("Edit Long Answer Task", expanded=True):
        e_la_text = st.text_area("Question Text", value=la.get('text', ''), key="la_t")
        e_la_rubric = st.text_area("Rubric", value=la.get('rubric', ''), key="la_r")
        e_la_pts = st.number_input("Points", value=int(la.get('points', 6)), key="la_p")
    
    final_la = {"question_num": 1, "text": e_la_text, "points": e_la_pts, "rubric": e_la_rubric}

    # --- YAML EXPORT ---
    st.divider()
    yaml_data = {
        "quiz_id": quiz_id_input,
        "web_url": st.session_state['saved_url'],
        "title": edited_title,
        "resource_text": st.session_state['resource_text'],
        "multiple_choice": final_compiled_questions,
        "long_answer": final_la
    }
    
    st.download_button(
        label=f"💾 Download QUIZ_{quiz_id_input}.yaml",
        data=yaml.dump(yaml_data, allow_unicode=True, sort_keys=False),
        file_name=f"QUIZ_{quiz_id_input}.yaml",
        mime="text/yaml"
    )
