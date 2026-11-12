# Company Lead Finder - Client Deployment & Setup Guide

This guide explains how to install and run the **Company Lead Finder** application on any Windows, Mac, or Linux computer from scratch.

---

## 1. System Requirements

1. **Python 3.11** (Recommended: Python 3.11.x)
   - Download from: [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - ⚠️ **CRITICAL (Windows Users):** During installation, you **MUST check the box that says "Add Python to PATH"** before clicking Install.
2. **Node.js (LTS)** (Optional - only required if modifying frontend source code)
   - Download from: [https://nodejs.org/](https://nodejs.org/)

---

## 2. One-Click Setup (Windows)

We have created automated batch scripts for quick setup:

1. **Install all dependencies**:
   - Double-click `setup_environment.bat`.
   - It will automatically verify your Python installation, create an isolated virtual environment (`venv`), and install all requirements from `requirements.txt`.
2. **Start the application**:
   - Double-click `start_app.bat`.
   - It will start the backend server and open the dashboard in your default browser.

---

## 3. Manual Installation (Command Line)

If you prefer installing via PowerShell or Terminal:

### Step 1: Open Terminal in the Project Directory
```powershell
cd /path/to/Company_lead_Finder
```

### Step 2: Create a Virtual Environment (Recommended)
```powershell
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Step 3: Install All Python Requirements
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Install Browser Binaries (for Playwright scraping)
```powershell
playwright install chromium
```

### Step 5: Configure API Keys (`.env`)
Make sure your `.env` file exists in the root folder with your keys:
```env
SERPER_API_KEY=your_serper_key_here
APIFY_API_TOKEN=your_apify_token_here
HUNTER_API_KEY=your_hunter_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### Step 6: Start the Server
```powershell
python run_backend.py
```
Then visit: `http://localhost:5173` (or `http://127.0.0.1:8000`) in your browser.

