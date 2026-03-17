# Server Report Generator

> Stopping the "Stare-and-Type" routine. Turn your Grafana dashboard screenshots into professional Excel reports in seconds.

---

## 🚀 Quick Start (Windows)

1.  **Clone/Download** this repository.
2.  **Run `setup.bat`**: Double-click the file. It will:
    - Create your `.env` configuration file.
    - Ask for your initial API key.
    - (Optional) Build and start the Docker container for you.
3.  **Open Browser**: Go to [http://localhost:5000](http://localhost:5000).

---

## 📖 The Story

Monitoring large infrastructure is critical, but reporting it is often a chore. For many teams, the daily routine involves opening dozens of Grafana dashboards and manually typing percentages into a spreadsheet. This "stare-and-type" process is:
- **Painfully slow**: Taking hours away from actual engineering work.
- **Accident-prone**: A single typo in a server name or IP can break the report's credibility.
- **Inconsistent**: Each engineer might interpret or format data slightly differently.

We built the **Server Report Generator** to bridge the gap between **Visual Monitoring** and **Structured Reporting**. 

## ✨ How it Works & Why AI?

This isn't just a simple OCR tool. We use **Vision AI** as an "intelligent bridge":

### 1. The "Photocopier" Vision
Generic OCR often struggles with the high-density grid lines of Grafana. Our system uses specialized **Vision Prompting**. It tells the AI to treat the image as a literal document, ensuring that numbers and labels are extracted with high fidelity without "hallucinating" or rounding values.

### 2. Intelligent OCR Repair
Grafana labels can be tricky. A disk label like `\C:` often gets read as `IC:` by standard tools. Our AI layer is specifically tuned to **recognize and fix these nuances** in real-time, ensuring your disk metrics are always accurate.

### 3. Server Reconciliation
You don't need to rename your servers in Grafana to match your Excel. The app uses a **Master Server List**. Provide an IP address from a screenshot, and the app automatically looks up the friendly name (e.g., `FinGridApp01`) and places the data in the correct row of your report.

### 4. Model-Agnostic Freedom
Because AI is moving fast, we built this to be **Provider Agnostic**. You can manage multiple configurations (Anthropic, Google, OpenAI, DeepSeek) directly from the **AI Settings** dashboard. Your keys are stored in a local SQLite database, so they survive container restarts but never leave your machine.

---

## 💳 Financial & Account Setup

To use professional models, you need an API key and credits:
1.  **Financial Setup**: If local cards are restricted, use a **Dollar Virtual Card** like [Evertry](https://evertry.com/).
2.  **Purchase**: Load the card and buy credits on the [Anthropic Console](https://console.anthropic.com/) or [Google AI Studio](https://aistudio.google.com/).
3.  **API Key**: Copy your key and paste it into the app's **AI Settings** panel.

---

## 🐳 Technical Guide

### Infrastructure
- **Dockerized**: Runs in a lightweight Python 3.11 container.
- **Persistent Data**: Logs, settings, and the master list are stored in a Docker volume named `report_data`.

### File Architecture
- `app.py`: Central Flask API handling extraction and generation.
- `ai_service.py`: Provider-agnostic bridge supporting multiple AI visions.
- `report_builder.py`: Excel formatting and server matching logic.
- `database.py`: Clean SQLite persistence for user settings.

### Manual Setup (Non-Script)
```bash
# 1. Prepare environment
copy .env.example .env

# 2. Build & Launch
docker compose up -d --build
```
