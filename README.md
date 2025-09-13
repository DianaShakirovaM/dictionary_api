# Translation and Dictionary API

A Flask-based REST API for text translation and personal dictionary management with user authentication.

## Features
- User Authentication (registration, login, JWT tokens)
- Password Recovery via email
- Text Translation using MyMemory Translation API
- Personal Dictionary for saving translations
- Pagination and Search in dictionary
- Dictionary Export
---
# Installation and Setup
1. Clone the repository:
```bash
git clone[ https://github.com/DianaShakirovaM/dictionary_api
cd dictionary_api
```
2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```
3. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```
3. Run the application:
```bash
flask run
```
# Usage Examples
1. User Registration
```http
POST /api/auth/login 
```
### Response
```json
{
  "email": "test@example.com",
  "password": "password123"
}
```
2. Text Translation
```
POST /api/translate
```
### Response
```json
{
    "text": "Hello world",
    "langpair": "en|ru"
}
```
3. Get Dictionary with Pagination
```http
Content-Type: application/json
Authorization: Token your_token
GET /api/dictionary?page=1&per_page=10&q=hello
```
### Response
```json
{
  "pagination": {
    "page": 1,
    "per_page": 10,
    "next_num": null,
    "prev_num": null,
    "total": 1,
    "pages": 1
  },
  "dictionary": [
    {
      "id": 1,
      "text": "Hello world",
      "translation": "Привет мир",
    }
  ]
}
```
