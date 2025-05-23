import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from bs4 import BeautifulSoup
import pdfplumber
from PIL import Image
import pytesseract
import matplotlib.pyplot as plt
import re

def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Jika teks ditemukan
                text += page_text + "\n"
            else:  # Jika halaman tidak memiliki teks, gunakan OCR
                st.write(f"Using OCR on page {page.page_number}...")
                page_image = page.to_image()
                ocr_text = pytesseract.image_to_string(page_image.original)
                text += ocr_text + "\n"
    return text

def scrape_google_scholar(query, max_results=5):
    search_url = f"https://scholar.google.com/scholar?q={query}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    for result in soup.find_all('h3', {'class': 'gs_rt'}):
        if result.a and len(links) < max_results: 
            links.append(result.a['href'])
    return links

def is_valid_url(url):
    regex = re.compile(
        r'^(https?://)'  
        r'(www\.)?'     
        r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b'  
        r'([-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'  
    )
    return re.match(regex, url) is not None


def detect_plagiarism(uploaded_text, sources):
    documents = [uploaded_text] + sources
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix[0][1:], vectorizer, tfidf_matrix


def clean_text(text):
    lines = text.split("\n")
    cleaned_lines = [
        line for line in lines
        if not any(keyword in line.lower() for keyword in ["issn", "volume", "nomor", "doi", "https", "http"])
    ]
    return " ".join(cleaned_lines[:3])  

def clean_extracted_text(text):
    lines = text.splitlines()
    cleaned_lines = [
        line.strip() for line in lines
        if line.strip() and not any(keyword in line.lower() for keyword in ["font size", "help", "login", "register"])
    ]
    return " ".join(cleaned_lines)

st.title("Check Plagiarism")

uploaded_file = st.file_uploader("Upload your document (PDF only):", type=["pdf"])
if uploaded_file:
    st.write("Extracting text...")
    uploaded_text = extract_text_from_pdf(uploaded_file)
    st.text_area("Extracted Text:", uploaded_text, height=200)

 
    st.write("Analyzing References...")
    references = [line.strip() for line in uploaded_text.split("\n") if is_valid_url(line.strip())]
    if not references:
        st.write("No valid references found in the document.")
    else:
        for ref in references:
            st.write(f"Reference Found: {ref}")

 
    external_sources = [
        "https://example1.com/relevant-article",
        "https://example2.com/related-study"
    ]

    if not references:
        st.write("Using additional external sources...")
        references.extend(external_sources)


    cleaned_text = clean_text(uploaded_text)
    st.write("Searching for potential sources with the following query:")
    st.text(cleaned_text)


    sources_links = scrape_google_scholar(cleaned_text, max_results=5)
    all_sources_links = references + sources_links

    st.write("Found Sources:")
    for link in all_sources_links:
        st.write(f"[Source Link]({link})")

    sources_texts = []
    for link in all_sources_links:
        try:
            page = requests.get(link)
            soup = BeautifulSoup(page.text, 'html.parser')
            sources_texts.append(clean_extracted_text(soup.get_text()))
        except Exception as e:
            st.write(f"Could not access {link}: {e}")
            continue

    st.write("Detecting plagiarism...")
    similarities, vectorizer, tfidf_matrix = detect_plagiarism(uploaded_text, sources_texts)
    avg_similarity = similarities.mean() if len(similarities) > 0 else 0

    st.write(f"Similarity Score: {avg_similarity * 100:.2f}%")


    if len(similarities) > 0:
        st.write("Highlighted Plagiarized Sentences:")
        for i, similarity in enumerate(similarities):
            if similarity > 0.1: 
                source_text = sources_texts[i]
                st.write(f"From Source {i + 1}:")
                st.text(" ".join(source_text.split()[:50]))  


    labels = ['Original', 'Plagiarized']
    sizes = [100 - avg_similarity * 100, avg_similarity * 100]
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')
    st.pyplot(fig)
