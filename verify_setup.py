"""Verify all dependencies are correctly installed."""
import sys
import os


def check_imports():
    """Check all critical imports."""
    checks = {
        # Core Framework
        "FastAPI": "fastapi",
        "Uvicorn": "uvicorn",
        "WebSockets": "websockets",
        
        # Multi-Agent
        "LangGraph": "langgraph",
        "LangChain": "langchain",
        "LangChain Community": "langchain_community",
        
        # LLM Provider
        "Groq": "groq",
        
        # Audio
        "Pydub": "pydub",
        
        # OCR & Vision
        "Tesseract": "pytesseract",
        "EasyOCR": "easyocr",
        "Pillow": "PIL",
        "OpenCV": "cv2",
        
        # PDF
        "PyPDF2": "PyPDF2",
        "PDFPlumber": "pdfplumber",
        
        # YouTube
        "YouTube Transcript": "youtube_transcript_api",
        
        # RAG & Embeddings
        "ChromaDB": "chromadb",
        "Sentence Transformers": "sentence_transformers",
        "Transformers": "transformers",
        "HuggingFace Hub": "huggingface_hub",
        "Tiktoken": "tiktoken",
        
        # Utilities
        "Pydantic": "pydantic",
        "Python Dotenv": "dotenv",
        
        # Testing
        "Pytest": "pytest",
        "HTTPX": "httpx",
    }
    
    failed = []
    passed = 0
    
    for name, module in checks.items():
        try:
            __import__(module)
            print(f"✓ {name}")
            passed += 1
        except ImportError as e:
            print(f"✗ {name}: {e}")
            failed.append(name)
    
    print(f"\n{'='*50}")
    print(f"Passed: {passed}/{len(checks)}")
    
    if failed:
        print(f"❌ Failed imports ({len(failed)}): {', '.join(failed)}")
        return False
    else:
        print(f"✅ All {len(checks)} Python dependencies installed successfully!")
        return True


def check_system_deps():
    """Check system dependencies."""
    import subprocess
    
    checks = {
        "Tesseract OCR": ["tesseract", "--version"],
        "FFmpeg": ["ffmpeg", "-version"],
    }
    
    failed = []
    passed = 0
    
    for name, cmd in checks.items():
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            print(f"✓ {name}")
            passed += 1
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name} not found")
            failed.append(name)
    
    print(f"\n{'='*50}")
    print(f"Passed: {passed}/{len(checks)}")
    
    if failed:
        print(f"❌ Missing system dependencies ({len(failed)}): {', '.join(failed)}")
        print("\nInstall missing dependencies:")
        if "Tesseract OCR" in failed:
            print("  brew install tesseract")
        if "FFmpeg" in failed:
            print("  brew install ffmpeg")
        return False
    else:
        print(f"✅ All system dependencies installed!")
        return True


def check_env_file():
    """Check if .env file exists and has required keys."""
    env_path = ".env"
    
    if not os.path.exists(env_path):
        print(f"✗ .env file not found")
        print("\nCreate .env file with:")
        print("  GROQ_API_KEY=your_key_here")
        return False
    
    print(f"✓ .env file exists")
    
    # Check for required key
    with open(env_path, 'r') as f:
        content = f.read()
    
    if "GROQ_API_KEY" not in content:
        print(f"⚠️  Warning: GROQ_API_KEY not found in .env")
        print("  Add: GROQ_API_KEY=your_key_here")
        return False
    
    if "your_groq_api_key_here" in content:
        print(f"⚠️  Warning: Replace 'your_groq_api_key_here' with actual API key")
        print("  Get key from: https://console.groq.com/keys")
        return False
    
    print(f"✓ GROQ_API_KEY configured")
    return True


def check_directories():
    """Check if project structure exists."""
    required_dirs = [
        "src/agents",
        "src/tools",
        "src/orchestration",
        "src/state",
        "src/api/routes",
        "src/rag",
        "src/utils",
        "tests",
        "frontend",
        "static",
    ]
    
    missing = []
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ missing")
            missing.append(dir_path)
    
    print(f"\n{'='*50}")
    
    if missing:
        print(f"❌ Missing directories ({len(missing)})")
        print(f"\nCreate with: mkdir -p {' '.join(missing)}")
        return False
    else:
        print(f"✅ Project structure complete!")
        return True


def main():
    """Run all verification checks."""
    print("=" * 50)
    print("SETUP VERIFICATION")
    print("=" * 50)
    print(f"Python version: {sys.version}\n")
    
    results = []
    
    print("\n" + "=" * 50)
    print("1. CHECKING PYTHON IMPORTS")
    print("=" * 50)
    results.append(check_imports())
    
    print("\n" + "=" * 50)
    print("2. CHECKING SYSTEM DEPENDENCIES")
    print("=" * 50)
    results.append(check_system_deps())
    
    print("\n" + "=" * 50)
    print("3. CHECKING ENVIRONMENT FILE")
    print("=" * 50)
    results.append(check_env_file())
    
    print("\n" + "=" * 50)
    print("4. CHECKING PROJECT STRUCTURE")
    print("=" * 50)
    results.append(check_directories())
    
    # Final summary
    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    
    if all(results):
        print("🎉 ALL CHECKS PASSED!")
        sys.exit(0)
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("❌ Fix the issues above before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()