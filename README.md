📚 ChatBook

ChatBook is a powerful web-based platform that blends real-time chat with intelligent book analysis and AI-driven assistance. Built with Flask and Socket.IO, it enables interactive literary discussions, smart content retrieval, and collaborative analysis—all in one sleek interface.

⸻

🚀 Features

🔹 Real-time Communication
	•	Seamless messaging with WebSocket (Socket.IO)
	•	Multi-user chatrooms with live updates
	•	Real-time reactions and user presence tracking
	•	Secure SSL-based communication
	•	Flexible, environment-based configuration

📖 Intelligent Book Analysis
	•	Upload books in PDF, EPUB, and more
	•	AI-generated summaries and key insights
	•	Vector-based content search via MongoDB Atlas
	•	Create, share, and collaborate on notes
	•	Group discussion and shared reading tools

🤖 AI Integration
	•	Powered by LangChain and Gemini AI
	•	Smart recommendations based on reading history
	•	Instant help via Gemini-powered AI Assistant
	•	Context-aware conversation and search
	•	Natural language understanding for precise queries

🔐 Authentication & Security
	•	Auth0-powered secure login
	•	Role-based access control
	•	End-to-end encrypted chat
	•	Safe file uploads and session security

🗂️ Database & Search
	•	MongoDB Atlas for scalable storage
	•	Semantic vector search for deep content understanding
	•	Real-time sync and recovery-ready architecture

⸻

🧰 Prerequisites
	•	Python 3.x
	•	pip (Python package manager)
	•	MongoDB Atlas account
	•	Auth0 account
	•	OpenAI API key
	•	Gemini API key

⸻

⚙️ Installation
	1.	Clone the repo:

git clone <repository-url>
cd ChatBook


	2.	Set up the virtual environment:

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate


	3.	Install dependencies:

pip install -r requirements.txt


	4.	Configure environment variables:
Create a .env file with:

PORT=8000
MONGODB_URI=your_mongodb_atlas_uri
AUTH0_DOMAIN=your_auth0_domain
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key



⸻

▶️ Running the App

Start the server:

python run.py

Or use the helper script:

./start_servers.sh

Default port: 8000 (configurable via .env)

⸻

📁 Project Structure

ChatBook/
├── app/                 → Core app logic
│   ├── auth/            → Auth handlers (Auth0)
│   ├── models/          → Database models
│   ├── routes/          → REST & WebSocket routes
│   ├── services/        → Business logic
│   └── utils/           → Helper functions
├── backend/             → Backend modules
│   ├── ai/              → AI integrations
│   ├── search/          → Vector search logic
│   └── storage/         → File handling
├── config.py            → App settings
├── requirements.txt     → Python dependencies
├── run.py               → Main entry point
└── start_servers.sh     → Startup script



⸻

🧩 Tech Stack & Dependencies
	•	Flask – Web framework
	•	Flask-SocketIO – WebSocket support
	•	LangChain – Language model orchestration
	•	Google Generative AI (Gemini) – AI Assistant
	•	OpenAI – Language understanding
	•	Auth0 – Authentication
	•	MongoDB + PyMongo – Database & vector search
	•	PyPDF2 – PDF parsing
	•	python-dotenv – Config management
	•	Gevent – Asynchronous I/O

⸻

🤝 Contributing
	1.	Fork the repo
	2.	Create a branch:

git checkout -b feature/YourFeature


	3.	Commit your work:

git commit -m "Add: Your feature"


	4.	Push & open a pull request

⸻

📜 License

This project is licensed under the MIT License.

⸻

💬 Support

Need help?
👉 Open an issue or contact the maintainers.

⸻
