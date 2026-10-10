# DocChat

**Chat with your documents. Find answers without searching through every page.**

[**Live Demo**](https://docchats.vercel.app/) · [**GitHub Repository**](https://github.com/naflanmohamed/DocChat)

DocChat is an AI-powered document assistant that lets you upload your files and ask questions about their contents. Instead of manually searching through long documents, you can ask questions in natural language and get answers supported by relevant passages from your files.

I built DocChat to explore how large language models and Retrieval-Augmented Generation (RAG) can make document-based information easier to access, understand, and use.

Whether you're reviewing study materials, reading reports, or working with technical documentation, DocChat provides a simpler way to find the information you need.

## What You Can Do

- **Upload Documents:** Upload PDF, DOCX, and TXT files directly through the interface.
- **Ask Questions in Natural Language:** Interact with your documents through a conversational chat experience.
- **Get Context-Aware Answers:** Use document retrieval to provide the AI with relevant information before it generates a response.
- **View Source Citations:** Trace answers back to relevant document content instead of relying entirely on unsupported model knowledge.
- **Manage Uploaded Documents:** Access your uploaded documents through the document interface.
- **Use a Simple Web Interface:** Work with your files through a clean interface without manually searching page by page.

## How It Works

DocChat uses Retrieval-Augmented Generation (RAG) to connect a language model with information from your uploaded documents.

1. **Upload:** The user uploads a supported document.
2. **Extract:** The backend extracts readable text from the file.
3. **Split:** The extracted text is divided into smaller chunks so relevant information can be retrieved efficiently.
4. **Embed and Index:** The text is converted into embeddings and stored in a vector database.
5. **Retrieve:** When the user asks a question, the system searches for document passages relevant to the query.
6. **Generate:** The retrieved context is passed to the language model to generate an answer.
7. **Cite:** Relevant source information is presented alongside the answer to help the user verify it.

This approach helps ground responses in uploaded material and makes it easier to check where an answer came from.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Next.js, React |
| Backend | Python, FastAPI |
| AI framework | LangChain |
| Language model | Google Gemini API |
| Vector database | ChromaDB |
| Core AI technique | Retrieval-Augmented Generation (RAG) |
| Deployment | Vercel for the frontend, Render for the backend |

## Understanding the RAG Pipeline

The central part of DocChat is its document retrieval pipeline.

A normal chatbot generates responses primarily from the information available to its language model. DocChat takes a different approach by retrieving relevant content from the user's documents and using that content to answer questions.

For example, imagine uploading a course PDF and asking:

*“What are the main differences between supervised and unsupervised learning?”*

Instead of requiring you to search the entire PDF manually, DocChat retrieves relevant passages and uses them to construct an answer with source references.

The retrieval process helps connect the generated response to the document being discussed. As with other AI systems, citations should still be checked against the original file.

## Running Locally

### Prerequisites

Before getting started, install:

- Python and pip.
- Node.js and npm.
- Git.
- Docker Desktop, if you want to use the provided Docker configuration.

You'll also need a Google Gemini API key.

### 1. Clone the repository

```powershell
git clone https://github.com/naflanmohamed/DocChat.git
cd DocChat
```

### 2. Configure the backend

Open a PowerShell terminal and navigate to the backend directory.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create the required environment configuration using the variables expected by the backend. Add your Gemini API key and configure any required vector database or service settings.

### 3. Start the backend

Use the FastAPI entry point defined in the backend source code. For example, if the application entry point is `main.py` and exposes `app`, run:

```powershell
uvicorn main:app --reload
```

The API documentation is typically available at:

`http://localhost:8000/docs`

### 4. Configure and start the frontend

Open another PowerShell terminal from the repository root.

```powershell
cd frontend
npm install
npm run dev
```

Configure the frontend's API URL to point to your local backend, using the environment variable name expected by the frontend.

Once both services are running, open the local frontend URL shown in the terminal.

**Setup note:** Confirm the exact dependency files, environment variable names, application entry point, and required services in the repository before running these commands. The commands above are a starting point, not a verified end-to-end setup.

## Project Structure

```text
DocChat/
├── backend/             # FastAPI backend and AI logic
├── frontend/            # Web interface
├── .github/workflows/   # GitHub Actions workflows
├── docker-compose.yml   # Docker service configuration
└── README.md
```

## What I Learned

Working on DocChat helped me explore the practical challenges of building an AI application beyond simply connecting a language model to a chat interface.

Some of the key areas include:

- Building APIs with Python and FastAPI.
- Integrating Google Gemini into an application.
- Designing document ingestion and retrieval workflows.
- Working with embeddings and vector databases.
- Using LangChain to connect retrieval with language model generation.
- Providing source citations to make document-based answers easier to verify.
- Connecting a frontend to a separately deployed backend.
- Managing configuration and troubleshooting issues across application services.

## Future Improvements

Potential areas for further development include more advanced retrieval strategies, document-level access controls, improved retrieval evaluation, automated testing, and support for additional file formats.

## Try DocChat

**Live application:** https://docchats.vercel.app/

**Source code:** https://github.com/naflanmohamed/DocChat

Feedback and suggestions are welcome.

---

**Built by Naflan Mohamed**

AI Engineer focused on practical AI applications, LLM-powered products, and full-stack development.
