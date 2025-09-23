# MaxiAgent - Motorcycle Finance Assistant

## Overview

MaxiAgent is an AI-powered conversational agent specialized in motorcycle financing for Maxikash. It provides expert consultation on motorcycle credits, generates personalized quotations, and offers up-to-date information about motorcycle catalogs from partner brands (Italika, Bajaj, Vento).

![RAG Architecture](RAG_architecture.png)

The agent combines Retrieval-Augmented Generation (RAG) technology with Google Cloud's Agent Development Kit to deliver comprehensive financial advisory services. It processes user queries through specialized tools for credit consultation, catalog search, quotation calculation, and session management.

## Agent Details
| Attribute         | Details                                                                                                                                                                                             |
| :---------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Interaction Type** | Conversational                                                                                                                                                                                      |
| **Complexity**    | Advanced
| **Agent Type**    | Single Agent with Multiple Tools                                                                                                                                                                                        |
| **Components**    | Financial Calculator, Web Search, RAG, Session Management                                                                                                                                                                               |
| **Vertical**      | Financial Services - Motorcycle Financing                                                                                                               |

### Agent Architecture

![RAG](RAG_workflow.png)

## Key Features

### 🏍️ **Motorcycle Catalog Consultation**
- **Brand Coverage**: Italika, Bajaj, and Vento motorcycles
- **Real-time Search**: Up-to-date pricing and specifications
- **Category Filtering**: Work motorcycles, scooters, sports, tricycles, choppers, urban
- **Detailed Information**: Technical specifications, pricing, and availability

### 💰 **Credit Advisory Services**
- **RAG-powered Responses**: Intelligent document retrieval for credit questions
- **Financing Process**: Complete guidance on requirements and documentation
- **Payment Options**: Information on terms, rates, and payment schedules
- **Eligibility Assessment**: Professional consultation on credit options

### 📊 **Quotation Generation**
- **Personalized Calculations**: Based on income, motorcycle price, and personal data
- **Multiple Payment Plans**: Various financing options with different terms
- **Session Management**: Persistent data storage during consultation
- **Real-time Processing**: Instant calculation through external API integration

### 🔍 **Smart Session Management**
- **Data Persistence**: Maintains client information throughout the conversation
- **Status Tracking**: Monitors completeness of required data for quotations
- **Flexible Input**: Handles various data formats and user input styles
- **Privacy Focused**: Secure handling of personal financial information

## Core Capabilities

### Tools Available:
- **`semantic_search`**: RAG-based search for credit and financing information
- **`google_web_search`**: Real-time web search for motorcycle catalogs
- **`calculate_quotation`**: Financial calculation service for loan quotations
- **Session Management Tools**: Data storage and retrieval for user information

### Required Data for Quotations:
1. **Monthly Income** (`ingreso_mensual`)
2. **Motorcycle Price** (`precio_moto`)
3. **Birth Date** (`fecha_nacimiento`)
4. **Motorcycle Brand** (`marca_moto`)
5. **Motorcycle Model** (`modelo_moto`)

## Setup and Installation

### Prerequisites

- **Google Cloud Account**: Active GCP project with billing enabled
- **Python 3.11+**: Ensure you have Python 3.11 or later version installed
- **Poetry**: Install Poetry for dependency management: [https://python-poetry.org/docs/](https://python-poetry.org/docs/)
- **Git**: Version control system

### Project Setup

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd maxiagent
   ```

2. **Install Dependencies with Poetry:**
   ```bash
   poetry install
   ```

3. **Activate the Poetry Environment:**
   ```bash
   poetry shell
   ```
   Or alternatively:
   ```bash
   source .venv/bin/activate
   ```

4. **Set up Environment Variables:**
   Create a `.env` file based on the following template:
   ```env
   # Google Cloud Configuration
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1

   # Agent Configuration
   ROOT_AGENT_MODEL=gemini-1.5-pro
   AGENT_ENGINE_ID=projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID

   # RAG Configuration
   RAG_CORPUS=projects/YOUR_PROJECT/locations/us-central1/ragCorpora/YOUR_CORPUS_ID
   EMBEDDING_MODEL_NAME=text-embedding-004

   # Google Search API
   GOOGLE_SEARCH_API_KEY=your-google-search-api-key
   GOOGLE_CSE_ID=your-custom-search-engine-id

   # Environment
   FLASK_ENV=dev

   # External APIs - Development
   URL_CALCULADORA_DEV=https://your-calculator-api-dev.com
   KEY_CALCULADORA_DEV=your-calculator-api-key-dev
   API_MAXIKASH_DEV=https://your-maxikash-api-dev.com

   # External APIs - Production
   URL_CALCULADORA_PROD=https://your-calculator-api-prod.com
   KEY_CALCULADORA_PROD=your-calculator-api-key-prod
   API_MAXIKASH_PROD=https://your-maxikash-api-prod.com

   # Database Configuration (for RAG)
   POSTGRE_IP_PUBLIC=your-public-postgres-ip
   POSTGRE_IP_PRIVATE=your-private-postgres-ip
   POSTGRE_PORT=5432
   POSTGRE_USR_RAG_REPO_DEV=your-postgres-username
   POSTGRE_PASS_RAG_REPO_DEV=your-postgres-password
   POSTGRE_DB_RAG_REPO=your-database-name
   ```

5. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth application-default login
   ```

## Running the Agent

### Local Development

1. **Run agent in CLI:**
   ```bash
   adk run maxiagent
   ```

2. **Run agent with ADK Web UI:**
   ```bash
   adk web
   ```
   Then select MaxiAgent from the dropdown.

### Example Interactions

**Credit Consultation:**
```
User: ¿Qué documentos necesito para un crédito de moto?
Agent: [Uses semantic_search to provide detailed documentation requirements]
```

**Catalog Search:**
```
User: ¿Qué motos de trabajo tiene Italika?
Agent: [Uses google_web_search to find current Italika work motorcycles with pricing and specifications]
```

**Quotation Generation:**
```
User: Quiero cotizar una moto
Agent: Perfecto, necesito algunos datos para generar su cotización:
        ¿Cuál es su ingreso mensual aproximado?
[Collects data step by step and generates personalized financing options]
```

## Deployment

### Deploy to Vertex AI Agent Engine

1. **Configure deployment settings** in `deployment/deploy.py`

2. **Deploy the agent:**
   ```bash
   python deployment/deploy.py
   ```

3. **Grant necessary permissions:**
   ```bash
   chmod +x deployment/grant_permissions.sh
   ./deployment/grant_permissions.sh
   ```

4. **Test the deployed agent:**
   ```bash
   python deployment/run.py
   ```

## Development

### Project Structure
```
maxiagent/
├── agent.py              # Main agent configuration
├── config/               # Environment and configuration management
│   ├── __init__.py
│   └── config.py
├── prompts/              # Agent instruction prompts
│   ├── __init__.py
│   └── root_agent_prompts.py
├── tools/                # Agent tools and capabilities
│   ├── __init__.py
│   └── root_agent_tools.py
└── utils/                # Utility functions
    ├── __init__.py
    └── utils.py
```

### Adding New Tools

1. Add the tool function to `maxiagent/tools/root_agent_tools.py`
2. Register it in the `_tools` dictionary
3. Update the prompt instructions in `maxiagent/prompts/root_agent_prompts.py`

### Testing

Run tests using pytest:
```bash
poetry run pytest eval/
```

## Configuration

### Environment-Specific Settings

The agent supports multiple environments (dev/prod) with different API endpoints and configurations. Set `FLASK_ENV=dev` or `FLASK_ENV=prod` to switch between environments.

### Database Configuration

For RAG functionality, configure PostgreSQL with pgvector extension for embedding storage and semantic search capabilities.

## Customization

### Modify Agent Behavior
- **Prompts**: Edit `maxiagent/prompts/root_agent_prompts.py` to change agent responses and behavior
- **Tools**: Add or modify tools in `maxiagent/tools/root_agent_tools.py`
- **Configuration**: Adjust settings in `maxiagent/config/config.py`

### Integrate Additional APIs
- Add new API configurations to the config classes
- Create corresponding tool functions
- Update agent prompts to include new capabilities

## Supported Motorcycle Brands

- **Italika**: Work motorcycles, scooters, urban bikes
- **Bajaj**: Various motorcycle categories
- **Vento**: Complete motorcycle lineup

For other brands, the agent will redirect users to the supported options.

## Disclaimer

This project is designed for motorcycle financing consultation and quotation generation. All financial calculations are provided through external APIs and should be verified for accuracy. The agent is intended for informational and consultation purposes within the Maxikash ecosystem.