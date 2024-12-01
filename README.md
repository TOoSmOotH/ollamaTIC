# OllamaTIC (Ollama Token Information Center)

A proxy server for monitoring Ollama model usage and metrics. This proxy sits between Cline and Ollama, capturing usage metrics while maintaining compatibility with both Ollama's native API and OpenAI's API format.

## Features

- Proxies requests to Ollama server
- Supports both Ollama native API and OpenAI-compatible endpoints
- Captures detailed usage metrics:
  - Token usage (input/output)
  - Request latency
  - Context sizes
  - Model performance metrics
- Compatible with Cline's token parsing

## Installation

1. Clone the repository

## Configuration

Create a `.env` file in the root directory with the following variables:
```env
OLLAMA_SERVER=http://gpu:11434
DEFAULT_MODEL=llama2
```

## Usage

Start the server:
```bash
./start.sh
```

The proxy server will be available at `http://localhost:8000`
