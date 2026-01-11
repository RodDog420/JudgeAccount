# JudgeAccount

**Live Site:** [https://judgeaccount.com](https://judgeaccount.com)

A public accountability platform dedicated to judicial transparency through community-driven reviews and media documentation.

---

## Table of Contents

- [About](#about)
- [Mission](#mission)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Deployment](#deployment)
- [Security Considerations](#security-considerations)
- [License](#license)
- [Contact](#contact)

---

## About

JudgeAccount is a Flask-based web application that enables citizens to share firsthand experiences with judges and document judicial conduct through verified media links. The platform prioritizes accountability, transparency, and integrity in the judicial system.

---

## Mission

To create an accessible, transparent platform where individuals can:
- Share truthful, firsthand accounts of their experiences with judges
- Document judicial conduct through verified media sources
- Hold the judicial system accountable to the public it serves
- Foster informed civic engagement through reliable information

---

## Features

### Core Functionality
- **User Authentication:** Secure registration and login system with role-based access control
- **Judge Reviews:** Submit and browse firsthand accounts of judicial conduct
- **Media Documentation:** Verified media link submissions with source attribution
- **Content Moderation:** Comprehensive flagging and review system for community standards enforcement
- **Administrative Dashboard:** Full-featured admin panel for content management and user administration

### User Experience
- **Advanced Search:** Filter judges by name, state, and court level
- **Responsive Design:** Mobile-first approach ensuring accessibility across all devices
- **Community Guidelines:** Comprehensive policies ensuring truthful, firsthand content
- **Privacy Protection:** GDPR and CCPA compliant data handling

### Content Integrity
- **Firsthand Experience Requirement:** All reviews must be based on direct personal experience
- **Media Verification:** Links to reputable news sources and official court documents
- **Conflict of Interest Reporting:** Dedicated flagging category for potential bias
- **False Reporting Protection:** Multi-tier enforcement system to prevent abuse

---

## Technology Stack

### Backend
- **Framework:** Flask 3.0.0
- **Database:** PostgreSQL (production) / SQLite (development)
- **ORM:** Flask-SQLAlchemy 3.1.1
- **Migrations:** Flask-Migrate 4.0.5
- **Authentication:** Flask-Login 0.6.3
- **Forms:** Flask-WTF 1.2.1, WTForms 3.1.1
- **Password Security:** Werkzeug 3.0.1 (bcrypt hashing)

### Frontend
- **Template Engine:** Jinja2 3.1.2
- **Styling:** Custom CSS with responsive design patterns
- **Form Validation:** Client-side JavaScript + server-side WTForms

### Production Server
- **WSGI Server:** Gunicorn 21.2.0
- **Platform:** Render.com
- **Database Driver:** psycopg2-binary 2.9.9

### Development Tools
- **Environment Management:** python-dotenv 1.0.0
- **Version Control:** Git
- **Dependency Management:** pip, requirements.txt

---

## Project Structure

```
judge-review/
├── app/
│   ├── __init__.py           # Application factory
│   ├── models.py             # Database models (User, Judge, Review, MediaLink, etc.)
│   ├── routes.py             # Main application routes
│   ├── auth.py               # Authentication routes
│   ├── forms.py              # WTForms form classes
│   ├── court_data.py         # Court hierarchy and state data
│   ├── static/
│   │   └── css/
│   │       ├── base.css      # Base styling and layout
│   │       ├── cards.css     # Card component styles
│   │       ├── components.css # Reusable UI components
│   │       ├── forms.css     # Form styling
│   │       ├── navigation.css # Navigation and header
│   │       └── tables.css    # Table layouts
│   └── templates/
│       ├── base.html         # Base template with navigation and footer
│       ├── index.html        # Homepage with search functionality
│       ├── judge.html        # Individual judge page with reviews and media
│       ├── submit_review.html
│       ├── submit_media.html
│       ├── dashboard.html    # User dashboard
│       ├── moderation_queue.html
│       ├── guidelines.html   # Community guidelines
│       ├── privacy_policy.html
│       ├── terms_of_service.html
│       ├── contact.html
│       ├── sitemap.html
│       ├── support.html
│       └── admin/            # Admin-only templates
│           ├── admin_dashboard.html
│           ├── admin_users.html
│           └── ...
├── migrations/               # Database migration files
├── instance/                 # Instance-specific files (not in Git)
│   └── judge_review.db      # SQLite database (development only)
├── .env                      # Environment variables (not in Git)
├── .flaskenv                 # Flask-specific environment vars (not in Git)
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── render.yaml              # Render.com deployment configuration
├── build.sh                 # Render build script
├── DEPLOYMENT.md            # Deployment documentation
└── judge_review.py          # Application entry point
```

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git
- PostgreSQL (for production deployment)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RodDog420/JudgeAccount.git
   cd JudgeAccount
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (this file is git-ignored):

```env
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///C:/Users/yourusername/judge-review/instance/judge_review.db
```

Create a `.flaskenv` file for Flask-specific settings (this file is git-ignored):

```env
FLASK_APP=judge_review.py
FLASK_DEBUG=1
```

**Important:** Never commit `.env` or `.flaskenv` to version control. These are already included in `.gitignore`.

---

## Database Setup

### Initialize the database:

```bash
flask db init           # Only needed once for new projects
flask db migrate -m "Initial migration"
flask db upgrade
```

This creates the SQLite database in the `instance/` directory with all necessary tables:
- Users
- Judges
- Reviews
- MediaLinks
- ContentFlags
- AdminNotes

---

## Running the Application

### Development Server

1. **Ensure your virtual environment is activated**
2. **Run the Flask development server:**
   ```bash
   flask run
   ```
3. **Access the application:**
   - Open your browser to `http://localhost:5000`

### Create an Admin User

To access admin features, you'll need to manually set a user's `is_admin` flag in the database or through the Flask shell:

```bash
flask shell
```

Then in the Python shell:
```python
from app import db
from app.models import User

user = User.query.filter_by(username='your_username').first()
user.is_admin = True
db.session.commit()
exit()
```

---

## Deployment

### Render.com Deployment

This application is configured for seamless deployment on Render.com using the included `render.yaml` blueprint.

**Deployment Process:**

1. **Push code to GitHub**
2. **Connect Render to your GitHub repository**
3. **Render automatically:**
   - Creates a PostgreSQL database
   - Sets up environment variables
   - Runs migrations via `build.sh`
   - Deploys with Gunicorn

**For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**

### Production Environment Variables

Render automatically configures:
- `SECRET_KEY` (auto-generated secure key)
- `DATABASE_URL` (PostgreSQL connection string)

### Custom Domain Configuration

Point your domain's DNS to Render:
- See Render dashboard for specific CNAME/A records
- SSL certificates are automatically provisioned

---

## Security Considerations

### Implemented Security Measures

1. **Password Security:**
   - Werkzeug bcrypt hashing for all passwords
   - No plain-text password storage

2. **Session Management:**
   - Secure session cookies
   - Flask-Login session protection
   - Auto-generated secret keys in production

3. **Data Privacy:**
   - GDPR and CCPA compliant
   - Clear privacy policy
   - User data deletion capabilities

4. **Input Validation:**
   - Server-side form validation with WTForms
   - Client-side validation for user experience
   - CSRF protection on all forms

5. **Content Moderation:**
   - Community flagging system
   - Admin moderation queue
   - Multi-tier violation enforcement

6. **Environment Security:**
   - Sensitive data in environment variables
   - `.env` and `.flaskenv` git-ignored
   - No hardcoded credentials

### Security Best Practices

- **Never commit `.env` files to version control**
- **Regularly update dependencies for security patches**
- **Use strong, unique SECRET_KEY in production**
- **Keep admin credentials secure**
- **Monitor application logs for suspicious activity**

---

## License

**© 2026 JudgeAccount. All Rights Reserved.**

This is proprietary software. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited without explicit written permission from the copyright holder.

For licensing inquiries, contact: Admin@JudgeAccount.com

---

## Contact

**Email:** Admin@JudgeAccount.com

**Website:** [https://judgeaccount.com](https://judgeaccount.com)

**GitHub:** [@RodDog420](https://github.com/RodDog420)

---

## Contributions

This project is not currently accepting contributions. This is a privately maintained project focused on a specific mission and vision.

---

## Acknowledgments

Built with Flask and deployed on Render.com. Committed to transparency, accountability, and integrity in the judicial system.

---

**Last Updated:** January 2026