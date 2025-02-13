# Fiscal printing application

## Components
1. Web server
2. Database
3. Utilities


### 1. Flask web server
Served on port 9090
Two routes:
-  /v1/login
- /v1/prints

### 2. Database 

Sqlite database with an SQLAlchemy ORM
3 Models:
- User 
- Print Job
- Error Log

### 3. Utilities
- Direct printer send, using pywin32 API

## Installation

1. Install python 3.10+ [here](https://www.python.org/downloads/release/python-3106/)*
2. Clone this repository 
```
git clone https://github.com/go-prime/ef_fiscal_api

```
4. Create virtual environment
```
python -m venv env
env/scripts/activate
```
5. Install dependencies 
```
pip install -r requirements.txt 
```
6. Create database
```
python models.py
```
7. Setup environment by creating a .env file with the following keys:
- API_KEY
- SESSION_PASSWORD
- SECRET_KEY

8. Start the app
```
python app.py
```

9. Make the app a background task with windows task scheduler.
WIP

---
* On windows, installing most packages using chocolatey is the preferred approach for reliability.
* Follow [this](https://learn.microsoft.com/en-us/troubleshoot/windows-server/printing/print-to-file-without-user-intervention) guide to setup a generic test printer 
