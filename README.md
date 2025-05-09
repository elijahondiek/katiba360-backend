# Set Up Guide

## Prerequisites

### Required Software
- Python 3.x (Download from [python.org](https://python.org](https://www.python.org/downloads/)))
- pip (Python package installer, comes with Python)
- Code editor of your choice (VS Code recommended)
- Git installed and set up (Optional) (Download from [Git](https://python.org](https://www.python.org/downloads/](https://git-scm.com/downloads))))

## Setting Up Your Development Environment

Navigate to your projects directory

### 1. Clone the Starter Repository
```bash
git clone https://github.com/ondiekelijah/gdg-fastapi-demo.git fastapi-demo-project
```
### 2. Navigate into the folder

```bash
cd fastapi-demo-project
```
All commands and project files mentioned in this guide should be executed/created inside this folder. Once inside the folder, you can open your terminal (Command Prompt on Windows or Terminal on Mac/Linux) and proceed with the next steps.

### 3. 🐍 Set Up Virtual Environment

- **Create a virtual environment**:
```bash
   python3 -m venv venv
 ```

  ### 4. Activate the Virtual Environment

- **On macOS and Linux:**

```
source venv/bin/activate
```

- **On Windows:**

```
. venv/Scripts/activate
```

### 5. 📦 Install Requirements

Use pip to install the necessary dependencies

```bash
pip install -r requirements.txt
```
### 6. ▶️ Run the Application

Use the start.sh script to initialize database migrations and start the application.

Development Mode:

```bash
alembic upgrade head
fastapi dev
```

Production Mode:

```bash
chmod 755 start.sh
sh start.sh
```

### 6. 🔍 Testing
API Documentation: Access the interactive API docs at `http://127.0.0.1:8000/docs` 📑

Swagger UI: Available at /docs endpoint