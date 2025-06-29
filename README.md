## MindThread

MindThread is a full-stack web application that combines a modern blogging experience with community-driven Q&A-style features. Users can create posts, engage in discussions through comments, vote on content, and personalize their profiles. Admins maintain content quality through moderation tools.

>> By Mercy Mumbe Munyongwe
>> https://drive.google.com/file/d/1lbnwi7VQQrGgqa6cHobdlzu3sFMSIc2X/view?usp=sharing

## Features

### User Features
### A Regular User Can: 
Register an account using a unique username, email, and password. 
Login securely using credentials. 
Update their profile details (username, email, bio). 
Publish a blog post, including a title, content, and optional tags or categories. 
View a list of all blog posts (searchable by title, category, or author). 
View individual blog posts, including full content and comments. 
Edit or delete their posts if needed. 
Comment on any blog post, contributing to a discussion or sharing feedback. 
Edit or delete their comments. 
Vote on blog posts and comments (upvote or downvote to indicate quality or relevance). 
View their profile, which includes a summary of their posted blogs, comments, and voting activity. 

### An Admin Can: 
Login to a protected admin dashboard. 
View a list of all registered users on the platform. 
Approve or unpublish blog posts (if moderation is enabled). 
Hide or delete inappropriate comments that do not meet community guidelines. 
Manage all content, including blog posts, comments, votes, and users. 
If necessary, update or delete any post, comment, or user for moderation or policy enforcement. 


### Admin Features
Admin dashboard for:
Content moderation (approve/flag/remove posts/comments)
User management
Data insights and visual analytics
Export user/post data as CSV
Toggle post/comment approval and flag status

### Data Relationships

One-to-many: User ↔ Post, User ↔ Comment, Post ↔ Comment
One-to-many: User ↔ Vote, Post ↔ Vote, Comment ↔ Vote

### Tech Stack

🔹 Frontend
React (Vite)
React Router DOM
Tailwind CSS
Chart.js
Toast Notifications

🔸 Backend
Flask
Flask-JWT-Extended (Token-based Auth)
Flask-SQLAlchemy + Migrate
Flask-Mail
Flask-CORS

🗄️ Database
SQLite (Development)
PostgreSQL (Production-ready)

### Getting Started

Backend Setup
Navigate to the backend directory:

cd backend
Create a virtual environment and activate it:

python -m venv venv
source venv/bin/activate
Install dependencies:

pip install -r requirements.txt
Set up environment variables in a .env file (example below):

FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
MAIL_SERVER=smtp.example.com
Run the app:

flask run
Frontend Setup
Navigate to the frontend directory:

cd frontend
Install dependencies:

npm install
Create a .env file with your API URL:

VITE_API_URL=http://localhost:5000
Start the development server:

npm run dev

# Deployment

Frontend: Netlify or Vercel
Backend: Render or Railway
Use CORS settings in Flask to whitelist frontend domains
Set production .env variables securely on deployment platforms

# Testing

Test APIs using Postman or curl
Use pytest (or unittest) for backend testing
Ensure CORS, auth, and edge cases are fully covered

# Contributing

Fork the repository
Create a new branch:
git checkout -b feature/your-feature-name
Make your changes

Commit and push:
git commit -m "Add your feature"
git push origin feature/your-feature-name
Open a pull request

## Contact details
Email: mercymumbe!7@gmail.com
Github: https://github.com/Mumbe-stack
