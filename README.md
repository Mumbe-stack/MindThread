# MindThread
MindThread is a full-stack web application that blends a modern blogging experience with interactive Q&A-style community features. Users can create insightful posts, contribute comments, vote on content, and manage their profiles, while admins maintain a clean and collaborative environment.



## Features

### User Features
- Register, log in, and manage profile
- Create, edit, and delete blog posts
- Comment on posts with threaded replies
- Upvote/downvote posts and comments
- View user profiles with contribution history

### Admin Features
- Admin dashboard for content moderation
- Approve or hide blog posts
- Remove inappropriate comments
- Manage users and content

### Relationships
- One-to-many between User ↔ Post, User ↔ Comment, Post ↔ Comment
- One-to-many between User ↔ Vote, Post ↔ Vote, Comment ↔ Vote



## Technologies

- **Frontend**: React, Axios, React Router
- **Backend**: Flask, Flask SQLAlchemy, Flask-JWT-Extended
- **Database**: SQLite / PostgreSQL (configurable)
- **Auth**: JWT-based login system
- **API Style**: RESTful JSON APIs



## Project Structure
MindThread
root/
├── client/                  
│   ├── src/
│   ├── public/
│   └── package.json
├── server/                  
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── routes/
│   │   ├── schemas/         
│   │   ├── utils/
│   │   └── auth.py
│   ├── migrations/          
│   ├── config.py
│   ├── run.py
│   └── requirements.txt
├── README.md
└── LICENSE


## How to Run the Application

### Clone the Repository
git clone https://github.com/Mumbe-stack/MindThread
cd insightbase

## Set Up the Backend (Flask API)
cd server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables (create a .env file if needed)
export FLASK_APP=run.py
export FLASK_ENV=development

# Run migrations (if using Flask-Migrate)
flask db init
flask db migrate
flask db upgrade

# Start the server
flask run

## Set Up the Frontend (React)
cd ../client
npm install
npm start
React runs on http://localhost:3000 and Flask API runs on http://localhost:5000

## Environment Variables Example

Backend (.env or terminal exports)
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-key
DATABASE_URL=sqlite:///app.db

Frontend (.env)
REACT_APP_API_BASE_URL=http://localhost:5000

## API Endpoints Overview
Method	Endpoint	             Description
POST	/api/register	         Register a new user
POST	/api/login	             Login and receive JWT token
GET	    /api/posts	             List all approved blog posts
POST	/api/posts	             Create a new blog post
GET	    /api/posts/:id	          Get a specific post
POST	/api/posts/:id/comments	  Comment on a post
POST	/api/votes/post/:id	      Vote on a post
POST	/api/votes/comment/:id	  Vote on a comment

## License
Copyright (c) 2025 [YMercy Mumbe Munyongwe,https://github.com/Mumbe-stack/MindThread]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.