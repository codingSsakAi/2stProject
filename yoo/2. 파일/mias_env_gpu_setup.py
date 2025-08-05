
# GPU 전용 가상환경 패키지 설치 스크립트
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install faiss-gpu
pip install pymupdf pdfminer-six pdfplumber camelot-py[cv] pypdf pytesseract pillow numpy pandas sentence-transformers transformers scikit-learn scipy requests tqdm
