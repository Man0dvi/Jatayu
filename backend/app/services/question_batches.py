import wikipediaapi
import faiss
import numpy as np
import time
import random
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests
import os
import json

def prepare_question_batches():

    # Configure Gemini AI API
    api_key = "AIzaSyBSpjhnYk97Un4eTDcxs9I2oDosw7YNr6g"  # Replace with your actual Gemini key
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 0.2,
        "max_output_tokens": 2048
    }

    model_gemini = genai.GenerativeModel(
        model_name="gemini-2.0-flash", generation_config=generation_config
    )

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    wiki = wikipediaapi.Wikipedia(
        user_agent="MandviAIQuiz/1.0 (contact: mandvishukla20@gmail.com)", language='en'
    )

    # Inputs
    jd_skills = [
        {"name": "Machine Learning", "priority": 3},
        {"name": "Cloud Computing", "priority": 2},
        {"name": "Data Science", "priority": 4},
        {"name": "NLP", "priority": 5},
        {"name": "Cybersecurity", "priority": 1}
    ]

    jd_experience_range = "3-6"
    candidate_experience = 4.0
    candidate_proficiency_per_skill = {
        "Machine Learning": "mid",
        "Data Science": "mid",
        "NLP": "low"
    }

    # Utility Functions
    def divide_experience_range(jd_range):
        start, end = map(float, jd_range.split("-"))
        interval = (end - start) / 3
        return {
            "good": (start, start + interval),
            "better": (start + interval, start + 2 * interval),
            "perfect": (start + 2 * interval, end)
        }

    def get_candidate_band(candidate_exp, jd_range):
        band_ranges = divide_experience_range(jd_range)
        for band, (low, high) in band_ranges.items():
            if low <= candidate_exp <= high:
                return band
        return "good"

    def get_weightage(proficiency):
        return {
            "low": (0.7, 0.3),
            "mid": (0.5, 0.5),
            "high": (0.3, 0.7)
        }.get(proficiency, (0.5, 0.5))

    def expand_skills_with_gemini(skill):
        prompt = f"List 5 key subtopics under {skill} that are relevant for a technical interview. Only list the subskills."
        try:
            chat_session = model_gemini.start_chat(history=[{"role": "user", "parts": [prompt]}])
            response = chat_session.send_message(prompt)
        except TooManyRequests:
            print(f"⛔️ Gemini quota exceeded while expanding skill: {skill}")
            return []

        if response and isinstance(response.text, str):
            subtopics = [line.strip("- ") for line in response.text.split("\n") if line.strip()][:5]
            return subtopics
        return []

    def fetch_wikipedia_content(topic):
        page = wiki.page(topic)
        return page.summary if page.exists() else None

    def generate_questions_prompt(skill, subskills, difficulty_band):
        difficulty_descriptor = {
            "good": "easy and theory-based, suitable for beginners",
            "better": "moderate difficulty, mixing theory and practical concepts",
            "perfect": "challenging, practical, and suitable for advanced learners"
        }[difficulty_band]

        prompt = f"""
    Generate 20 unique and diverse multiple-choice questions (MCQs) on the skill '{skill}' and its subskills: {", ".join(subskills)}.
    The questions should be {difficulty_descriptor}.
    Guidelines:
    1. Each question must be different in wording and concept.
    2. Cover a broad range of topics from the subskills provided.
    3. Do NOT repeat similar ideas or phrasing.
    4. Each MCQ must have exactly four options labeled (A), (B), (C), (D).
    5. Include the correct answer at the end in the format: "Correct Answer: (B)"
    6. Format each question exactly like this:
    "Question text\n\n(A) Option A\n(B) Option B\n(C) Option C\n(D) Option D\n\nCorrect Answer: (B)"

    Return ONLY a Python list of 20 such formatted MCQs. No explanation, no extra text.
    """
        return prompt.strip()

    # Initialize
    band_ranges = divide_experience_range(jd_experience_range)
    knowledge_base = {}
    question_bank = {"good": {}, "better": {}, "perfect": {}}
    faiss_indices = {"good": {}, "better": {}, "perfect": {}}

    for skill_data in jd_skills:
        skill = skill_data["name"]
        print(f"\n📌 Processing Skill: {skill} (Priority: {skill_data['priority']})")
        subskills = expand_skills_with_gemini(skill)
        all_topics = [skill] + subskills

        # Fetch and store Wikipedia summaries
        for topic in all_topics:
            if topic not in knowledge_base:
                content = fetch_wikipedia_content(topic)
                if content:
                    embedding = embedding_model.encode(content)
                    knowledge_base[topic] = {
                        "content": content,
                        "embedding": np.array(embedding)
                    }

        # Generate MCQ batches per band
        for band in ["good", "better", "perfect"]:
            key = f"{skill}"
            if key not in question_bank[band]:
                question_bank[band][key] = []
                faiss_indices[band][key] = faiss.IndexFlatL2(384)

            questions = []
            embeddings = []

            prompt = generate_questions_prompt(skill, subskills, band)
            try:
                chat = model_gemini.start_chat(history=[{"role": "user", "parts": [prompt]}])
                response = chat.send_message(prompt)
                if response and isinstance(response.text, str):
                    raw_text = response.text.strip()
                    if raw_text.startswith("[") and raw_text.endswith("]"):
                        questions = json.loads(raw_text)
                    else:
                        questions = [q.strip() for q in raw_text.split("\n\n") if q.strip()]
                    questions = questions[:20]  # Cap to 20

                    for q in questions:
                        emb = embedding_model.encode(q)
                        embeddings.append(emb)

                    print(f"✅ [{band.upper()}] {skill}: {len(questions)} questions stored")
            except TooManyRequests:
                print("⛔️ Gemini quota exceeded. Retrying in 10 seconds...")
                time.sleep(10)
            except Exception as e:
                print(f"⚠️ Error generating batch: {e}")
            time.sleep(1.5)

            question_bank[band][key] = questions
            if embeddings:
                faiss_indices[band][key].add(np.array(embeddings))
                print(f"✅ FAISS index built for {skill} in {band} band.")

    # Save to JSON
    def save_question_batches_to_json(question_bank, directory="question_batches"):
        os.makedirs(directory, exist_ok=True)
        for band in ["good", "better", "perfect"]:
            for skill, questions in question_bank[band].items():
                filename = f"{directory}/{skill.replace(' ', '_')}_{band}.json"
                with open(filename, "w") as f:
                    json.dump(questions, f, indent=2)

    save_question_batches_to_json(question_bank)
    print("✅ Questions saved to JSON files in 'question_batches' folder.")
    print("\n✅ All tasks completed!")
