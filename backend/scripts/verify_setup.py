"""
Setup Verification Script
=========================
Run this to confirm your Phase 2 setup is correct
before moving to Phase 3.

Usage: python scripts/verify_setup.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check(label: str, fn):
    """Run a check and print pass/fail."""
    try:
        result = fn()
        print(f"  PASS  {label}" + (f": {result}" if result else ""))
        return True
    except Exception as e:
        print(f"  FAIL  {label}: {e}")
        return False


def main():
    print("=" * 55)
    print("PHASE 2 SETUP VERIFICATION")
    print("=" * 55)
    
    all_passed = True
    
    # ── Python version ───────────────────────────────────────
    print("\n1. Python Environment")
    
    def check_python():
        v = sys.version_info
        assert v.major == 3 and v.minor >= 11, f"Need Python 3.11+, got {v.major}.{v.minor}"
        return f"Python {v.major}.{v.minor}.{v.micro}"
    
    all_passed &= check("Python 3.11+", check_python)
    
    # ── Core imports ─────────────────────────────────────────
    print("\n2. Core Package Imports")
    
    all_passed &= check("fastapi",            lambda: __import__("fastapi").__version__)
    all_passed &= check("uvicorn",            lambda: __import__("uvicorn").__version__)
    all_passed &= check("langchain",          lambda: __import__("langchain").__version__)
    all_passed &= check("pydantic",           lambda: __import__("pydantic").__version__)
    all_passed &= check("python-dotenv",      lambda: __import__("dotenv") and "ok")
    all_passed &= check("chromadb",           lambda: __import__("chromadb").__version__)
    all_passed &= check("sentence-transformers", lambda: __import__("sentence_transformers").__version__)
    all_passed &= check("pymupdf (fitz)",     lambda: __import__("fitz").__version__)
    all_passed &= check("python-docx",        lambda: __import__("docx") and "ok")
    all_passed &= check("requests",           lambda: __import__("requests").__version__)
    
    # ── Config loading ───────────────────────────────────────
    print("\n3. Configuration")
    
    def check_config():
        from app.config import get_settings
        s = get_settings()
        return f"env={s.environment}, llm={s.llm_provider}, db={s.vector_db_provider}"
    
    all_passed &= check(".env loads correctly", check_config)
    
    # ── API key checks ───────────────────────────────────────
    print("\n4. API Keys")
    
    def check_gemini_key():
        from app.config import get_settings
        s = get_settings()
        if s.llm_provider == "gemini":
            assert s.gemini_api_key, "GEMINI_API_KEY not set"
            return f"present (ends: ...{s.gemini_api_key[-4:]})"
        return "skipped (provider is not gemini)"
    
    def check_groq_key():
        from app.config import get_settings
        s = get_settings()
        if s.llm_provider == "groq":
            assert s.groq_api_key, "GROQ_API_KEY not set"
            return f"present (ends: ...{s.groq_api_key[-4:]})"
        return "skipped (provider is not groq)"
    
    all_passed &= check("LLM API key", check_gemini_key)
    all_passed &= check("Groq API key (backup)", check_groq_key)
    
    # ── Directory creation ───────────────────────────────────
    print("\n5. Directories")
    
    def check_dirs():
        from app.config import get_settings
        s = get_settings()
        os.makedirs(s.upload_dir, exist_ok=True)
        os.makedirs(s.chroma_persist_dir, exist_ok=True)
        return "uploads/ and chroma_db/ created"
    
    all_passed &= check("Upload + Chroma dirs", check_dirs)
    
    # ── FastAPI app imports ───────────────────────────────────
    print("\n6. FastAPI Application")
    
    def check_app():
        from app.main import app
        assert app is not None
        routes = [r.path for r in app.routes]
        assert "/api/health" in routes, f"Missing /api/health. Routes: {routes}"
        return f"{len(routes)} routes registered"
    
    all_passed &= check("App imports and routes", check_app)
    
    # ── Embedding model (local) ───────────────────────────────
    print("\n7. Embedding Model (downloads ~90MB on first run)")
    
    def check_embeddings():
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vec = model.encode("test sentence").tolist()
        assert len(vec) == 384, f"Expected 384 dims, got {len(vec)}"
        return f"384-dim vector generated"
    
    all_passed &= check("Local embedding model", check_embeddings)
    
    # ── Result ───────────────────────────────────────────────
    print("\n" + "=" * 55)
    if all_passed:
        print("ALL CHECKS PASSED — Ready for Phase 3!")
        print("\nTo start the backend:")
        print("  uvicorn app.main:app --reload --port 8000")
        print("\nThen visit: http://localhost:8000/docs")
    else:
        print("SOME CHECKS FAILED — Fix the errors above")
        print("Then run this script again.")
    print("=" * 55)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()