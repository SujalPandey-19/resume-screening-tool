import os
import requests
import PyPDF2
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def analyze_resume(resume_text, job_description):
    # Extract skills using HuggingFace
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    # Define skill categories to check
    skills_to_check = [
        "Python", "Java", "Azure", "AWS", "GCP", "Kubernetes",
        "Docker", "Terraform", "DevOps", "SQL", "Machine Learning",
        "React", "Node.js", "CI/CD", "Linux", "Git"
    ]

    # Check which skills are in resume
    found_skills = []
    for skill in skills_to_check:
        if skill.lower() in resume_text.lower():
            found_skills.append(skill)

    # Calculate match score with job description
    job_words = set(job_description.lower().split())
    resume_words = set(resume_text.lower().split())
    common_words = job_words.intersection(resume_words)
    
    # Remove common english words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    common_words = common_words - stop_words
    
    match_score = min(int((len(common_words) / max(len(job_words), 1)) * 100), 100)

    # Determine experience level
    experience_keywords = {
        'senior': ['senior', 'lead', 'principal', 'architect', 'manager'],
        'mid': ['analyst', 'engineer', 'developer', 'associate'],
        'junior': ['intern', 'trainee', 'fresher', 'junior']
    }
    
    experience_level = "Mid Level"
    for level, keywords in experience_keywords.items():
        for keyword in keywords:
            if keyword in resume_text.lower():
                if level == 'senior':
                    experience_level = "Senior Level"
                elif level == 'junior':
                    experience_level = "Junior Level"
                break

    # Generate recommendation
    if match_score >= 70:
        recommendation = "Strong Match ✅"
        recommendation_detail = "This candidate is a strong fit for the role!"
    elif match_score >= 40:
        recommendation = "Moderate Match ⚠️"
        recommendation_detail = "This candidate partially matches the requirements."
    else:
        recommendation = "Weak Match ❌"
        recommendation_detail = "This candidate may not be the best fit for this role."

    return {
        'skills': found_skills,
        'match_score': match_score,
        'experience_level': experience_level,
        'recommendation': recommendation,
        'recommendation_detail': recommendation_detail,
        'word_matches': list(common_words)[:10]
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume uploaded'}), 400
    
    file = request.files['resume']
    job_description = request.form.get('job_description', '')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF and TXT files allowed'}), 400

    if not job_description:
        return jsonify({'error': 'Please provide a job description'}), 400

    # Save and process file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Extract text
    if filename.endswith('.pdf'):
        resume_text = extract_text_from_pdf(filepath)
    else:
        with open(filepath, 'r') as f:
            resume_text = f.read()

    # Analyze resume
    results = analyze_resume(resume_text, job_description)

    # Clean up uploaded file
    os.remove(filepath)

    return render_template('result.html', results=results, job_description=job_description)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)