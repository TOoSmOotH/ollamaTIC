# OllamaTIC (Ollama Token Information Center)

A comprehensive platform for interacting with and learning from Ollama models. OllamaTIC serves as an intelligent proxy between clients and Ollama, offering advanced features like usage analytics, learning capabilities, and RAG (Retrieval-Augmented Generation) integration.

## Key Features

### Core Functionality
- **API Compatibility**: 
  - Full support for Ollama's native API
  - OpenAI-compatible endpoints for drop-in replacement
  - Streaming response support for both formats

### Analytics & Monitoring
- **Detailed Usage Metrics**:
  - Token usage tracking (input/output)
  - Request latency monitoring
  - Context size analysis
  - Model performance metrics
  - Compatible with Cline's token parsing

### Learning System
- **Pattern Recognition**:
  - Automatic code pattern learning
  - Language-specific insights
  - Best practices detection
- **Experience Collection**:
  - Interaction history tracking
  - Success rate analysis
  - Code block effectiveness monitoring

### RAG Integration
- **Vector Store Integration**:
  - Efficient code snippet storage
  - Semantic search capabilities
  - Pattern-based retrieval
- **Context Enhancement**:
  - Automatic context enrichment
  - Relevant code suggestion
  - Historical interaction leveraging

## Installation

1. Clone the repository:
```bash
git clone https://github.com/TOoSmOotH/ollamaTIC.git
cd ollamaTIC
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory:
```env
OLLAMA_SERVER=http://gpu:11434
DEFAULT_MODEL=llama2
VECTOR_STORE_PATH=data/vectordb  # Optional: Path for vector database
LOG_LEVEL=INFO                   # Optional: Logging verbosity
```

## Usage

1. Start the server:
```bash
./start.sh
```

2. Access the web interface:
- Main interface: `http://localhost:8000`
- RAG interface: `http://localhost:8000/rag.html`
- Prompt management: `http://localhost:8000/prompt_management.html`

3. API Endpoints:
- Ollama API: `http://localhost:8000/api/ollama/*`
- OpenAI-compatible: `http://localhost:8000/v1/*`
- RAG API: `http://localhost:8000/api/rag/*`

## Architecture

OllamaTIC consists of several key components:

1. **Proxy Server**: Handles API compatibility and request routing
2. **Learning System**: Manages pattern recognition and experience collection
3. **Vector Store**: Provides efficient storage and retrieval of code snippets
4. **Web Interface**: Offers user-friendly access to all features

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:
- Bug fixes
- New features
- Documentation improvements
- Performance enhancements

## License

This project is licensed under the MIT License - see the LICENSE file for details.
