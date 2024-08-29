import os
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from chromadb import Client
from chromadb.utils import embedding_functions  # Adjust based on correct usage from chromadb documentation
from openai import ChatCompletion

app = Flask(__name__)

# Load the OpenAI API key from environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize ChromaDB client and create a collection for storing FAQs
client = Client()
collection = client.get_or_create_collection(name="service_faqs")

# Sample FAQ data extracted from the PDF
faq_data = [
    {"id": "1", "question": "What is the average cost of plumbing services?", "answer": "The average repair cost for plumbing services ranges from $100 to $200 for minor fixes."},
    {"id": "2", "question": "How do I know the contractors are reliable?", "answer": "Contractors are vetted based on experience, customer reviews, and licensing, ensuring high-quality service."},
    {"id": "3", "question": "What is the replacement time for water heaters?", "answer": "The replacement time for water heaters is typically 10-15 years with regular maintenance."}
]

# Correct method to add documents to the collection
for faq in faq_data:
    collection.add(
        documents=[faq["question"]],
        metadatas=[{"answer": faq["answer"]}],
        ids=[faq["id"]]
    )

# Dummy contractor data
contractors = [
    {"id": 1, "name": "John's Plumbing", "phone": "123-456-7890"},
    {"id": 2, "name": "Jane's Landscaping", "phone": "123-456-7891"},
    {"id": 3, "name": "Mike's Electrical", "phone": "123-456-7892"},
    {"id": 4, "name": "Sara's Roofing", "phone": "123-456-7893"},
]

# Initialize the database
def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, 
            name TEXT, 
            email TEXT, 
            phone TEXT, 
            selected_service TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Root route to serve the frontend HTML file
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

# Chat route accepting POST requests
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    response = generate_response(user_input)
    return jsonify({"response": response})

# Store user data route accepting POST requests
@app.route('/store_user_data', methods=['POST'])
def store_user_data():
    user_name = request.json.get('name')
    email = request.json.get('email')
    phone = request.json.get('phone')
    service = request.json.get('service')
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email, phone, selected_service) VALUES (?, ?, ?, ?)", 
                   (user_name, email, phone, service))
    conn.commit()
    conn.close()
    return jsonify({"message": "Thank you! Your details have been captured, and we will assist you shortly."})

# Get contractor options
@app.route('/get_contractors', methods=['GET'])
def get_contractors():
    return jsonify({"contractors": contractors})

# Handle form submission
@app.route('/submit_form', methods=['POST'])
def submit_form():
    selected_contractors = request.json.get('selected_contractors')
    return jsonify({"message": f"Form submitted for contractors: {', '.join(selected_contractors)}"})

# Set an appointment
@app.route('/set_appointment', methods=['POST'])
def set_appointment():
    selected_contractors = request.json.get('selected_contractors')
    return jsonify({"message": f"Appointment set with contractors: {', '.join(selected_contractors)}"})

# Function to generate a response based on user input
def generate_response(user_input):
    user_input = user_input.lower()
    if 'plumbing' in user_input:
        return "You can fill out a form, call a contractor, or set an appointment for plumbing services. What would you like to do?"
    elif 'landscaping' in user_input:
        return "You can fill out a form, call a contractor, or set an appointment for landscaping services. What would you like to do?"
    elif 'service' in user_input:
        return "Would you like to fill in a form, call a contractor, or set an appointment?"
    else:
        return "Hi there! I'm here to help you connect with top-rated contractors. How can I assist you today?"

# FAQ endpoint to handle user queries
@app.route('/faq', methods=['POST'])
def faq():
    user_query = request.json.get('query')
    results = collection.query(query=user_query, top_k=3)  # Adjust top_k as needed

    if results and len(results["documents"]) > 0:
        retrieved_answer = results["documents"][0]["metadata"]["answer"]
        enhanced_answer = generate_gpt_response(user_query, retrieved_answer)
        return jsonify({"answer": enhanced_answer})
    else:
        return jsonify({"answer": "Sorry, I couldn't find an answer to your question."})

# Function to generate response using GPT-4
def generate_gpt_response(user_query, retrieved_answer):
    response = ChatCompletion.create(
        model="gpt-4",
        api_key=openai_api_key,  # Use the API key loaded from environment variables
        messages=[
            {"role": "system", "content": "You are a helpful assistant answering FAQs about contractor services."},
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": retrieved_answer}
        ]
    )
    return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
