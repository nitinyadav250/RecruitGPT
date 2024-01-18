import openai
import PyPDF2
import docx
import os
import re
import pandas as pd
from pdfminer.high_level import extract_text
import json
import tempfile
import os

api_key = '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'
openai.api_key = api_key

def get_all_resumes(folder_path):
    resumes = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            text = convert_files_to_text(file_path)
            resumes.append(text)
    return resumes

def convert_files_to_text(file_path):
    if file_path.endswith('.pdf'):
        text = convert_pdf_to_text2(file_path)
    elif file_path.endswith('.docx'):
        text = convert_docx_to_text(file_path)
    else:
        return ""
    return text

def convert_pdf_to_text2(file_path):
    text = extract_text(file_path)
    return text

def convert_pdf_to_text(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

def convert_docx_to_text(file_path):
    doc = docx.Document(file_path)
    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text + '\n'
    return text

def get_choice_text_from_prompt(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
            max_tokens=1000
        )
        choice_text = response.choices[0]["message"]["content"]
        return choice_text
    except Exception as e:
        print("Error in get_choice_text_from_prompt:", str(e))
        return ""

def analyze_resume(resumetext,job_description,skills):
    system_message = """
    You are an excellent talent recuiter and your task is to score resumes of candidates between 0-100 against a job description and skills required.
    You will be provided with candidate resume, job description and skills required for the job.

    The system instruction is:
    Step-1: First check whether the candidate's resume is an actual resume or not.
    Step-2: If the candidate's resume is not an actual resume then score=0, else further
    analyse the candidate's resume against the job description and skills required by looking for these following qualities:
      1. Relevant Experience: Relevant work experience in the field or industry related to the job role
      2. Duration of experiences
      3. Previous job titles
      4. Specific responsibilities and their impact
      5. Achievements in previous experiences
      6. Education - The candidate's educational background
      7. Educational quality
      8. Certifications: specialized training, especially if they align with the job requirements
      9. Technical skills
      10. Soft skills
    Step-3:
    Score the overall quality of resume against the job description and skills required between 0-100.
    Score should be such that it can be compared against different candidate's resumes for shortlisting purpose.
    Score should be a floating point number with upto 2 decimal point accuracy.
    Step-4:
    Return the final score of resume, name of the candidate, file name, work experience, Education, Skill set,  and the detailed explanation of the scoring procedure which include how scores are allocated,
    answer should be in json format with keys as - score, name, file, experience, education, skills and explanation.
    """
    user_message = f"""
    Score the resume of candidate out of 100 against the given job description and skill requirements.
    Information about the candidate's resume, skills/requirements and job description are given inside text delimited by triple backticks.

    Candidate's Resume :{resumetext}
    The skills/requirements expected from the candidates: {skills}
    Job Description for the Target Role: {job_description}
    """
    messages =  [
                {'role':'system',
                'content': system_message},
                {'role':'user',
                'content': user_message},
                ]

    resume_score = get_choice_text_from_prompt(messages)
    return resume_score

def analyze_all_resumes(folder_path, job_description, skills):
  resumes = get_all_resumes(folder_path)
  scores = []
  for filename, resume_text in zip(os.listdir(folder_path), resumes):
      resume_score = analyze_resume(resume_text, job_description, skills)
      scores.append((filename, resume_score))

  df = pd.DataFrame(scores, columns=["File_Name", "Score"])

  return df



def extract_values(json_str):
    data = json.loads(json_str)
    score = data.get("score")
    explanation = data.get("explanation")
    name = data.get('name')
    file = data.get('file')
    experience = data.get('experience')
    education = data.get('education')
    skills = data.get('skills')

    return score, explanation, name, file, education, skills, experience

import streamlit as st
import pandas as pd

# Define your functions here (convert_files_to_text, analyze_resume, extract_values)

def upload_file(files, job_description, skills):

    file_paths = [file for file in files]

    result = []
    scores = []

    for file_path in file_paths:
        text = convert_files_to_text(file_path)
        result.append((file_path, text))

    for path, text in result:
        resume_score = analyze_resume(text, job_description, skills)
        scores.append((path, resume_score))

    df = pd.DataFrame(scores, columns=["File_Name", "Score"])

    extracted_data = df["Score"].apply(extract_values).tolist()

    new_df = pd.DataFrame(extracted_data, columns=["score", "explanation", "name", "file", "education", "skills", "experience"])

    new_df['File_Name'] = df['File_Name']

    return new_df

# Streamlit interface
st.title("RecruitGPT")

description = st.text_area("Description", height=200)
skills = st.text_area("Required Skills", height=50)
resumes = st.file_uploader("Resume", accept_multiple_files=True)

if st.button("Submit"):

    if resumes:
        temp_dir = tempfile.TemporaryDirectory()
        
        file_paths = []

        for file in resumes:
            with open(os.path.join(temp_dir.name, file.name), "wb") as f:
                f.write(file.read())
            file_paths.append(os.path.join(temp_dir.name, file.name))


        new_df = upload_file(file_paths, description, skills)
        st.dataframe(new_df)
        # Save the new_df to a CSV file and provide a download link
        csv = new_df.to_csv(index=False)
        st.download_button("Download Result", data=csv, file_name='result.csv', mime='text/csv')