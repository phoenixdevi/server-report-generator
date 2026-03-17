# Server Report Generator

A automated web pipeline that converts Grafana dashboard screenshots into professionally formatted Excel reports using Vision AI.

---

## 🚀 Quick Start (Windows)

1.  **Clone/Download** this repository.
2.  **Run `setup.bat`**: Double-click the file. It will:
    - Create your `.env` configuration file.
    - Ask for your initial API key.
    - (Optional) Build and start the Docker container for you.
3.  **Open Browser**: Go to [http://localhost:5000](http://localhost:5000).

---

## 🛠 Features

### 1. Model-Agnostic Settings (NEW)
You are no longer locked to one AI. Manage multiple providers and models via the **AI Settings** dashboard in the UI:
- **Standardized Terminology**: Uses industry-standard jargon like **Model ID** (e.g., `gpt-4o`, `claude-3-5-sonnet`).
- **Multiple Providers**: Supports **Anthropic Claude**, **Google AI (Gemini)**, **OpenAI**, and **DeepSeek**.
- **Persistent Storage**: Configurations are saved securely in a local SQLite database (`settings.db`).

### 2. Specialized Data Extraction
- **Photocopier Accuracy**: Custom AI prompts ensure metrics (CPU, Memory, Disk) are extracted literally.
- **Disk Label Cleaning**: Automatically fixes OCR errors in disk paths (e.g., preserving backslashes like `\C:`).
- **Master List Matching**: Matches IP addresses to hostnames using `data/master_servers.json`.

---

## 💳 Financial & Account Setup

To use the AI services, you need API credits. If you are in a region with restricted international payments:

1.  **Dollar Virtual Card**: Use an app like **Evertry** to create a USD virtual card.
2.  **API Credits**:
    - **Anthropic**: [Console.anthropic.com](https://console.anthropic.com/) (Recommended for accuracy).
    - **Google Gemini**: [AIStudio.google.com](https://aistudio.google.com/) (Affordable & high limit).
    - **OpenAI**: [Platform.openai.com](https://platform.openai.com/).
3.  **Top-up**: Add a minimum of $5 to your chosen provider's balance to generate your API key.

---

## 🐳 Technical Guide

### Infrastructure
- **Dockerized**: Runs in a lightweight Python 3.11 container.
- **Persistent Data**: Logs and settings are stored in a Docker volume named `report_data`, so they survive container updates.

### File Architecture
- `app.py`: Central Flask API handling extraction and generation.
- `ai_service.py`: Provider-agnostic bridge supporting multiple AI visions.
- `report_builder.py`: The core logic for Excel formatting and server reconciliation.
- `database.py`: Clean SQLite persistence for user settings.

### Manual Setup (Non-Script)
If you prefer the command line:
```bash
# 1. Prepare environment
copy .env.example .env

# 2. Build & Launch
docker compose up -d --build
```
