# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based AI-powered insurance recommendation system that helps users find and compare car insurance policies. The system uses RAG (Retrieval Augmented Generation) with Pinecone vector database to search through insurance company documents and provides personalized recommendations using OpenAI's GPT models.

## Technology Stack

- **Backend**: Django 5.x with REST Framework
- **Database**: SQLite (development)
- **AI/ML**: OpenAI GPT-4o-mini, SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Vector Database**: Pinecone for document embeddings
- **PDF Processing**: pdfplumber, pytesseract, pdf2image for document parsing
- **External APIs**: CODEF API for insurance premium data
- **Frontend**: Django templates with HTML/CSS

## Development Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### Running the Application
```bash
# Start development server
python manage.py runserver

# Run on specific port
python manage.py runserver 8080
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test insurance_app

# Run with verbose output
python manage.py test -v 2
```

### Database Management
```bash
# Make migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (be careful!)
python manage.py flush
```

## Key Architecture Components

### Core Applications
- `insurance_app/`: Main application containing all business logic
- `insurance_project/`: Django project configuration

### AI/ML Components
- `llm_client.py`: OpenAI GPT integration for text summarization and recommendation generation
- `rag_search.py`: RAG implementation using SentenceTransformers and Pinecone
- `pinecone_client.py`: Pinecone vector database client and index management
- `pinecone_search.py`: Insurance clause retrieval and search functionality

### Data Processing
- `pdf_processor.py`: Enhanced PDF processing for insurance documents
- `pdf_to_pinecone.py`: Pipeline for converting PDFs to vector embeddings
- `upload_all_to_pinecone.py`: Batch upload utility for document processing

### API Integration
- `insurance_api.py`: CODEF API integration for real insurance premium data
- `insurance_mock_server.py`: Mock server for development/testing
- `codef_client.py`: CODEF API client implementation

### Models
- `CustomUser`: Extended Django user model with insurance-specific fields (birth_date, gender, has_license)
- `Clause`: Insurance document clauses with metadata
- `InsuranceQuote`: User insurance recommendations with scoring

## Environment Configuration

The application requires a `.env` file with:
- `PINECONE_API_KEY`: Pinecone vector database API key
- `PINECONE_ENV`: Pinecone environment (optional, defaults to serverless)
- `OPENAI_API_KEY`: OpenAI API key for GPT models
- `CODEF_CLIENT_ID`: CODEF API client ID (for production)
- `CODEF_CLIENT_SECRET`: CODEF API client secret (for production)
- `PINECONE_INDEX_NAME`: Index name (optional, defaults to "insurance-clauses-new")

## Development Notes

### Mock vs Production Mode
- Set `USE_MOCK_API = True` in settings.py for development
- Uses mock server instead of real CODEF API calls
- Switch to `False` for production with real API credentials

### Vector Database Setup
- Pinecone index uses 768-dimensional embeddings (SentenceTransformers model)
- Uses cosine similarity metric
- Serverless spec on AWS us-east-1 region

### Document Processing Pipeline
1. PDFs stored in `insurance_app/documents/[company_name]/`
2. Process with `pdf_processor.py` to extract text and metadata
3. Generate embeddings using SentenceTransformers
4. Upload to Pinecone with `upload_all_to_pinecone.py`

### Authentication
- Custom user model extends Django's AbstractUser
- Login required for insurance recommendations
- User profiles store demographic data for premium calculations

## Utility Scripts

```bash
# Upload all documents to Pinecone
python manage.py shell
>>> from insurance_app.upload_all_to_pinecone import main
>>> main()

# Purge all vectors from Pinecone (be careful!)
python manage.py shell
>>> from insurance_app.purge_all_vectors import main
>>> main()
```