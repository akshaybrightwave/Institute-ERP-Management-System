# Online Examination Portal

A **full-stack web-based examination system** built with **Django 5.1.4** that enables Admins, Teachers, and Students to manage, create, and take exams online — complete with timed sessions, auto-grading, negative marking, and analytics dashboards.

---

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Django](https://img.shields.io/badge/Django-5.1.4-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Data Models](#-data-models)
- [Technology Stack](#-technology-stack)
- [Installation & Setup](#-installation--setup)
- [URL Reference](#-url-reference)
- [Screenshots & Pages](#-pages-overview)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## Features

### Admin
- Full dashboard with system-wide statistics (students, teachers, exams, feedback)
- Complete CRUD for teachers and students (add, edit, delete, search, filter by role)
- Feedback inbox with read/unread tracking, pagination, and delete
- Manage all exams and questions across all teachers
- Django admin panel access (`/admin/`)

### Teacher
- Personal dashboard with per-exam analytics: submissions, average scores, pass rates
- Create, edit, and delete own exams with full configuration:
  - Duration, pass percentage, negative marking, retake policy, end date, publish toggle
- Add questions with **dynamic MCQ options** (variable number of choices, mark correct answer)
- View and filter student submissions (by score, date range)
- Drill down into individual student answer sheets
- Export submissions to **CSV** for offline analysis
- Profile management with photo upload

### Student
- Dashboard showing available exams, attempt history, and average score
- Pre-exam **instructions page** with eligibility and deadline checks
- Take exams online with a **server-side countdown timer**
- Auto-submission when time expires (grace period of 60 seconds)
- Instant **auto-grading** with negative marking support
- Detailed result page with pass/fail status, marks breakdown, and progress bar
- Exam history with ability to delete past attempts
- Profile management with photo upload and bio

### Shared / System
- Role-based access control: `admin`, `teacher`, `student`
- 4-step password reset flow (email → confirm → reset → done)
- Contact/feedback form for public users
- Custom 404 and 500 error pages
- Paginated listings throughout the app
- Responsive Bootstrap 5 UI

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Client)                  │
│   HTML + Bootstrap 5 + JavaScript (Timer/UI)        │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────┐
│                 Django Application                   │
│                                                      │
│  ┌──────────────┐    ┌───────────────────────────┐  │
│  │   accounts   │    │          exam             │  │
│  │  (Auth/User) │    │  (Exams/Questions/Grades) │  │
│  └──────────────┘    └───────────────────────────┘  │
│                                                      │
│  Middleware: CSRF, Sessions, Auth, Messages          │
└──────────────────────────┬──────────────────────────┘
                           │ ORM
┌──────────────────────────▼──────────────────────────┐
│              MySQL 8.0 Database                      │
│         online_exam_portal_db                        │
└─────────────────────────────────────────────────────┘
```

---

## Data Models

### Accounts App
| Model | Description |
|-------|-------------|
| `User` | Custom user extending `AbstractUser` with `role` field (admin/teacher/student) |
| `Feedback` | Contact form submissions with read/unread tracking |

### Exam App
| Model | Description |
|-------|-------------|
| `Exam` | Exam metadata: title, dates, duration, marks, pass %, negative marks, retake, publish |
| `Question` | Question text and marks, linked to an Exam |
| `Option` | Dynamic MCQ choices with `is_correct` flag, linked to a Question |
| `StudentExamAttempt` | Tracks each exam session: start time, score, completion status |
| `StudentAnswer` | Records the option selected by a student for each question |
| `StudentProfile` | Extended profile: name, phone, email, photo, bio |
| `TeacherProfile` | Extended profile: name, phone, email, photo, bio |

### Relationships
```
User ──1:N──> Exam (created_by)
User ──1:1──> StudentProfile
User ──1:1──> TeacherProfile
User ──1:N──> StudentExamAttempt
Exam ──1:N──> Question ──1:N──> Option
Exam ──1:N──> StudentExamAttempt ──1:N──> StudentAnswer
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| Framework | Django 5.1.4 |
| Database | MySQL 8.0 (via `mysqlclient`) |
| Frontend | HTML5, CSS3, Bootstrap 5.3, JavaScript |
| Image Handling | Pillow |
| Form Rendering | django-widget-tweaks |
| Auth | Django built-in + custom `AbstractUser` |

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/AkshayG02/Online-Examination-Portal.git
cd Online-Examination-Portal
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure the Database
Make sure MySQL is running, then create the database:
```sql
CREATE DATABASE online_exam_portal_db;
```

> The database credentials in `online_exam_portal/settings.py` are:
> - **Name:** `online_exam_portal_db`
> - **User:** `root`
> - **Password:** `root`
> - **Host:** `localhost:3306`
>
> Update these in `settings.py` if your MySQL config differs.

### 5. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run the Development Server
```bash
python manage.py runserver
```
Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

> **Password Reset (Dev):** Uses `console.EmailBackend` — reset links print to the terminal instead of sending email.

---

## URL Reference

### Public
| URL | Purpose |
|-----|---------|
| `/` | Home — paginated exam listings |
| `/contact/` | Feedback/contact form |
| `/login/` | Login page |
| `/signup_admin/` | Admin registration |
| `/signup_teacher/` | Teacher registration |
| `/signup_student/` | Student registration |
| `/password_reset/` | Password reset (4-step flow) |

### Admin
| URL | Purpose |
|-----|---------|
| `/admin_dashboard/` | Statistics overview |
| `/admin_users/` | User list (search + filter) |
| `/admin_users_add/` | Add teacher/student |
| `/admin_feedback/` | Feedback inbox |

### Exam Management (Admin + Teacher)
| URL | Purpose |
|-----|---------|
| `/exams/` | Exam list |
| `/exams_add/` | Create exam |
| `/exams/<id>/questions/` | Manage questions |
| `/exam_list_dashboard/` | Question dashboard |

### Student
| URL | Purpose |
|-----|---------|
| `/student_dashboard/` | Student home |
| `/student_exams/` | Available exams |
| `/student_exam/<id>/attempt/` | Take exam |
| `/student_exam_result/<id>/` | View result |
| `/student_exam_history/` | Attempt history |

### Teacher
| URL | Purpose |
|-----|---------|
| `/teacher_dashboard/` | Teacher home + analytics |
| `/teacher/exam_dashboard/` | Submissions dashboard |
| `/teacher/exam/<id>/submissions/` | View submissions |
| `/teacher/exam/<id>/submissions/export/` | CSV export |

---

## Pages Overview

### Authentication
- Login, Signup (Admin/Teacher/Student), Password Reset (4 pages)

### Admin Panel
- Dashboard, User List, User Add/Edit, Feedback Inbox, Feedback Detail

### Exam Management
- Exam List, Add/Edit Exam, Question Dashboard, Question List, Add/Edit Question

### Student Pages
- Dashboard, Exam List, Instructions, Attempt Exam (with timer), Result, History, Profile, Edit Profile

### Teacher Pages
- Dashboard (with analytics), Profile, Profile Detail, Edit Profile, Exam Dashboard, Submissions, Student Answers

### Error Pages
- Custom 404 and 500 pages

---

## Project Structure

```
Online-Examination-Portal/
├── accounts/                  # Auth, user management, feedback app
│   ├── models.py              # User (custom AbstractUser), Feedback
│   ├── views.py               # Auth, dashboard, user CRUD, feedback
│   ├── forms.py               # Signup forms, FeedbackForm
│   ├── admin.py               # Admin registrations
│   └── templates/accounts/    # 18 HTML templates
│
├── exam/                      # Exam, questions, attempts, profiles app
│   ├── models.py              # Exam, Question, Option, Attempt, Answer, Profiles
│   ├── views.py               # Exam CRUD, grading, dashboards, CSV export
│   ├── forms.py               # ExamForm, QuestionForm, ProfileForms
│   ├── admin.py               # Admin registrations
│   └── templates/
│       ├── exam/              # 9 templates
│       ├── student/           # 8 templates
│       └── teacher/           # 7 templates
│
├── online_exam_portal/        # Django project settings
│   ├── settings.py            # MySQL config, auth model, middleware
│   ├── urls.py                # All URL patterns (~40 routes)
│   ├── wsgi.py
│   └── asgi.py
│
├── static/                    # CSS, images, favicon
├── media/                     # Uploaded profile pictures
├── templates/                 # Global error templates (404, 500)
├── manage.py
├── requirements.txt
└── context.md                 # Detailed project context document
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

This project is open-source and available under the [MIT License](LICENSE).

---

## Contact

For questions or feedback, please use the contact form on the deployed site or open a GitHub issue.
