# Online Examination Portal — Project Context

## 1. Project Overview

A full-stack web-based examination system built with **Django 5.1.4** that enables Admins, Teachers, and Students to manage, create, and take exams online. The portal supports role-based access control, timed exams, negative marking, auto-grading, and result analytics.

---

## 2. Technology Stack

| Layer          | Technology                                      |
| -------------- | ----------------------------------------------- |
| **Backend**    | Python 3.13, Django 5.1.4                       |
| **Frontend**   | HTML5, CSS3, Bootstrap 5.3, JavaScript          |
| **Database**   | MySQL 8 (`online_exam_portal_db`) via `mysqlclient` |
| **ORM**        | Django ORM (BigAutoField PKs)                   |
| **Auth**       | Django built-in auth + custom `AbstractUser`    |
| **Media**      | Pillow (image uploads for profiles)             |
| **Extras**     | django-widget-tweaks, django-rest-framework (installed), python-decouple (installed, not yet wired) |

> **Note:** SQLite config is commented out in `settings.py`. The active DB engine is MySQL on `localhost:3306`.

---

## 3. Project Structure

```
Online-Examination-Portal/
├── apps/                # Django apps package (ERP-ready architecture)
│   ├── accounts/        # Auth, user management, admin dashboard, feedback
│   ├── exams/           # Core exam engine, questions, answers, grading
│   ├── students/        # Student profiles, student dashboard, taking exams
│   └── teachers/        # Teacher profiles, teacher dashboard, submissions
│
├── online_exam_portal/  # Django project package
│   ├── settings.py      # Config: MySQL, auth model, message tags, email backend
│   ├── urls.py          # Central URL routing pointing to apps
│   ├── wsgi.py
│   └── asgi.py
│
├── static/              # Global static assets
│   ├── css/             # styles.css (empty), theme.css
│   └── images/          # Default profile, exam icons, favicon
│
├── media/               # User-uploaded files
│   ├── student_profiles/
│   └── teacher_profiles/
│
├── templates/           # Global templates (404.html, 500.html)
├── manage.py
├── requirements.txt
└── db.sqlite3           # Legacy SQLite file (not actively used)
```

---

## 4. Data Models

### 4.1 `apps.accounts` App

| Model      | Key Fields                                                  | Purpose                           |
| ---------- | ----------------------------------------------------------- | --------------------------------- |
| **User**   | `username`, `email`, `password`, `role` (admin/teacher/student) | Custom user with role-based access |
| **Feedback** | `name`, `email`, `subject`, `message`, `submitted_at`, `is_read` | Contact form submissions          |

### 4.2 `apps.exams` App

| Model                | Key Fields                                                                                              | Purpose                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Exam**             | `title`, `description`, `date`, `end_date`, `total_marks`, `duration_minutes`, `pass_percentage`, `negative_marks`, `allow_retake`, `is_published`, `created_by` (FK→User) | Exam metadata and configuration          |
| **Question**         | `exam` (FK→Exam), `question_text`, `marks`                                                              | Individual exam questions                |
| **Option**           | `question` (FK→Question), `text`, `is_correct`                                                          | Dynamic MCQ options (created at runtime) |
| **StudentExamAttempt** | `student` (FK→User), `exam` (FK→Exam), `start_time`, `submitted_at`, `score`, `is_completed`          | Tracks each student's exam session       |
| **StudentAnswer**    | `attempt` (FK→StudentExamAttempt), `question` (FK→Question), `selected_option` (FK→Option)              | Records individual answers               |

### 4.3 `apps.students` App

| Model                | Key Fields                                                                                              | Purpose                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **StudentProfile**   | `user` (1:1→User), `full_name`, `phone`, `email`, `profile_picture`, `bio`                              | Student profile data                     |

### 4.4 `apps.teachers` App

| Model                | Key Fields                                                                                              | Purpose                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **TeacherProfile**   | `user` (1:1→User), `full_name`, `phone`, `email`, `profile_picture`, `bio`                              | Teacher profile data                     |

### Entity Relationship Summary

```
User (accounts)
  ├── 1:N → Exam (created_by)
  ├── 1:1 → StudentProfile (students)
  ├── 1:1 → TeacherProfile (teachers)
  └── 1:N → StudentExamAttempt (exams)

Exam (exams)
  ├── 1:N → Question
  │         └── 1:N → Option
  └── 1:N → StudentExamAttempt
              └── 1:N → StudentAnswer
```

---

## 5. URL Routing & Views

### 5.1 Public / Auth Routes (handled by `accounts` app)

| URL Pattern                         | View                      | Access   |
| ----------------------------------- | ------------------------- | -------- |
| `/`                                 | `home`                    | Public   |
| `/contact/`                         | `contact_view`            | Public   |
| `/signup_admin/`                    | `signup_admin`            | Public   |
| `/signup_teacher/`                  | `signup_teacher`          | Public   |
| `/signup_student/`                  | `signup_student`          | Public   |
| `/login/`                           | `user_login`              | Public   |
| `/logout/`                          | `user_logout`             | Auth     |
| `/password_reset/` (+ 3 sub-URLs)   | Django auth views         | Public   |

### 5.2 Admin-Only Routes (handled by `accounts` app)

| URL Pattern                              | View                | Purpose                        |
| ---------------------------------------- | ------------------- | ------------------------------ |
| `/admin_dashboard/`                      | `admin_dashboard`   | Stats overview                 |
| `/admin_users/`                          | `user_list`         | List/search/filter users       |
| `/admin_users_add/`                      | `user_add`          | Add teacher or student         |
| `/admin_users/edit/<id>/`                | `user_edit`         | Edit user                      |
| `/admin_users/delete/<id>/`              | `user_delete`       | Delete user                    |
| `/admin_feedback/`                       | `feedback_list`     | Paginated feedback inbox       |
| `/admin_feedback/<id>/`                  | `feedback_detail`   | Read feedback (marks as read)  |
| `/admin_feedback/<id>/delete/`           | `feedback_delete`   | Delete feedback                |

### 5.3 Exam & Question Management (handled by `exams` app)

| URL Pattern                                    | View                          | Purpose                        |
| ---------------------------------------------- | ----------------------------- | ------------------------------ |
| `/exams/`                                      | `exam_list`                   | List exams (teacher sees own)  |
| `/exams_add/`                                  | `add_exam`                    | Create exam                    |
| `/exams/<id>/edit/`                            | `edit_exam`                   | Edit exam                      |
| `/exams/<id>/delete/`                          | `delete_exam`                 | Delete exam                    |
| `/exam_list_dashboard/`                        | `exam_question_dashboard_view`| Dashboard for question mgmt   |
| `/exams/<id>/questions/`                       | `question_list`               | List questions for an exam     |
| `/exams/<id>/questions/add/`                   | `add_question`                | Add question + dynamic options |
| `/questions/<id>/edit/`                        | `edit_question`               | Edit question text/marks       |
| `/questions/<id>/delete/`                      | `delete_question`             | Delete question                |

### 5.4 Student Routes (handled by `students` app)

| URL Pattern                                      | View                         | Purpose                         |
| ------------------------------------------------ | ---------------------------- | ------------------------------- |
| `/student_dashboard/`                            | `student_dashboard`          | Stats: exams, attempts, avg     |
| `/student_profile/`                              | `student_profile`            | View profile + attempt stats    |
| `/student_profile_edit/`                         | `edit_student_profile`       | Edit profile (with image)       |
| `/student_exams/`                                | `student_exam_list`          | Browse published exams          |
| `/exam/<id>/instructions/`                       | `exam_instructions_view`     | Pre-exam instructions page      |
| `/student_exam/<id>/attempt/`                    | `attempt_exam`               | Take exam (server-side timer)   |
| `/student_exam/<id>/submit/`                     | `submit_exam`                | Submit + auto-grade             |
| `/student_exam_result/<id>/`                     | `student_exam_result`        | View detailed result            |
| `/student_exam_history/`                         | `student_exam_history`       | All past attempts               |
| `/student_exam_attempt/delete/<id>/`             | `delete_student_exam_attempt`| Delete an attempt record        |

### 5.5 Teacher Routes (handled by `teachers` app)

| URL Pattern                                          | View                       | Purpose                          |
| ---------------------------------------------------- | -------------------------- | -------------------------------- |
| `/teacher_dashboard/`                                | `teacher_dashboard`        | Exam stats, paginated exam list  |
| `/teacher_profile/`                                  | `teacher_profile`          | View/edit profile                |
| `/teacher/profile/view/`                             | `teacher_profile_detail`   | Read-only profile detail         |
| `/edit_profile/`                                     | `edit_teacher_profile`     | Edit profile (forced on 1st login)|
| `/profile/delete/`                                   | `delete_teacher_profile`   | Delete profile + account         |
| `/teacher/exam_dashboard/`                           | `teacher_exam_dashboard`   | Submissions & answers dashboard  |
| `/teacher/exam/<id>/submissions/`                    | `view_submissions`         | Filterable submission list + stats|
| `/teacher/exam/<id>/submissions/export/`             | `export_submissions_csv`   | CSV download of submissions      |
| `/teacher/answers/<id>/`                             | `view_student_answers`     | View individual student answers  |

---

## 6. Key Features & Business Logic

### 6.1 Authentication & Authorization

- **Custom User Model:** `apps.accounts.User` extends `AbstractUser` with a `role` field (`admin`, `teacher`, `student`).
- **`admin_required` decorator:** Restricts views to admin-role users only (returns 403 otherwise).
- **`@user_passes_test`** with helper functions (`is_admin`, `is_teacher`, `is_admin_or_teacher`) for exam/question views.
- **`@login_required`** for all student and teacher profile views.
- **Role-based redirects** on login: admin → admin_dashboard, teacher → teacher_dashboard, student → student_dashboard.

### 6.2 Exam Lifecycle

1. **Creation:** Admin or Teacher creates an exam with title, description, date, duration, pass %, negative marks, retake policy, and publish status.
2. **Question Building:** Questions are added per exam with dynamic MCQ options (variable number of options, one marked correct).
3. **Publishing:** Exam is marked `is_published=True` to appear on student exam list.
4. **Student Attempt:**
   - Student views instructions → starts attempt (server creates `StudentExamAttempt`).
   - Timer is server-side: `remaining_seconds = (duration_minutes × 60) - elapsed_time`.
   - If time expires while student is away, attempt is auto-completed.
5. **Auto-Grading:**
   - Correct answer: `+question.marks`
   - Wrong answer: `-exam.negative_marks`
   - Score = `(marks_earned / total_marks) × 100` (clamped to 0 minimum).
6. **Results:** Pass/fail based on `exam.pass_percentage`, with visual progress bar.
7. **Retakes:** Controlled by `exam.allow_retake` flag.

### 6.3 Teacher Analytics

- Per-exam stats: total submissions, average/highest/lowest score, pass rate.
- Filterable by minimum score and date range.
- CSV export of submissions with student name, score, result, and timestamp.
- Drill-down into individual student answers.

### 6.4 Admin Dashboard

- Counts: total students, total teachers, total exams, unread feedback.
- Full user CRUD (add/edit/delete teachers and students).
- Feedback inbox with read/unread status, pagination, and delete.

### 6.5 Password Reset

- Full 4-step Django password reset flow (email → done → confirm → complete).
- Uses `console.EmailBackend` in development (prints reset link to terminal).

---

## 7. Forms

| Form                | App       | Model     | Fields                                     |
| ------------------- | --------- | --------- | ------------------------------------------ |
| `AdminSignupForm`   | accounts  | User      | username, email, password1, password2      |
| `TeacherSignupForm` | accounts  | User      | username, email, password1, password2      |
| `StudentSignupForm` | accounts  | User      | username, email, password1, password2      |
| `FeedbackForm`      | accounts  | Feedback  | name, email, subject, message              |
| `ExamForm`          | exams     | Exam      | title, description, date, end_date, total_marks, duration_minutes, pass_percentage, negative_marks, allow_retake, is_published |
| `QuestionForm`      | exams     | Question  | question_text, marks                       |
| `StudentProfileForm`| students  | StudentProfile | full_name, phone, email, profile_picture, bio |
| `TeacherProfileForm`| teachers  | TeacherProfile | full_name, phone, email, profile_picture, bio |

---

## 8. Templates (34 total)

### `apps/accounts/templates/accounts/` (18 templates)
`home.html`, `base.html`, `login.html`, `signup_admin.html`, `signup_teacher.html`, `signup_student.html`, `admin_dashboard.html`, `user_list.html`, `user_add.html`, `user_edit.html`, `contact.html`, `feedback_list.html`, `feedback_detail.html`, `feedback_delete.html`, `password_reset.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`

### `apps/exams/templates/exam/` (9 templates)
`exam_list.html`, `add_exam.html`, `edit_exam.html`, `exam_question_dashboard.html`, `question_list.html`, `add_question.html`, `edit_question.html`, `attempt_exam.html`, `teacher_exam_dashboard.html`

### `apps/students/templates/student/` (8 templates)
`student_dashboard.html`, `student_exam_list.html`, `exam_instructions.html`, `student_exam_result.html`, `student_exam_history.html`, `student_profile.html`, `edit_profile.html`, `confirm_delete_attempt.html`

### `apps/teachers/templates/teacher/` (7 templates)
`teacher_dashboard.html`, `teacher_profile.html`, `teacher_profile_detail.html`, `edit_profile.html`, `confirm_delete.html`, `view_submissions.html`, `view_student_answers.html`

### Global `templates/` (2 templates)
`404.html`, `500.html`

---

## 9. Security & Access Patterns

| Pattern                          | Implementation                                         |
| -------------------------------- | ------------------------------------------------------ |
| Role-based access                | `admin_required` decorator, `@user_passes_test`       |
| Ownership enforcement            | Teachers can only edit/delete their own exams/questions |
| CSRF protection                  | Django `CsrfViewMiddleware` (global)                   |
| Server-side timer validation     | Elapsed time checked on both attempt load and submit   |
| Time expiry enforcement          | 60-second grace period on submit; auto-complete if exceeded |
| Negative score clamping          | `max(0, marks_earned)` prevents negative total scores  |
| Profile deletion cascade         | Deleting teacher profile also deletes the user account |

---

## 10. Database Configuration

```python
# Active (MySQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'online_exam_portal_db',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# AUTH_USER_MODEL = 'accounts.User'
```

---

## 11. Migrations

- **apps.accounts:** `0001_initial` (User, Feedback), `0002_feedback_is_read`
- **apps.exams:** `0001_initial` (Exam, Question, Option, StudentExamAttempt, StudentAnswer), `0002_exam_allow_retake_...`, `0003_transfer_profiles_to_dedicated_apps`
- **apps.students:** `0001_initial` (StudentProfile, ownership transfer)
- **apps.teachers:** `0001_initial` (TeacherProfile, ownership transfer)

---

## 12. Static & Media Files

- **Static:** `static/css/theme.css` (active), `static/css/styles.css` (empty), `static/images/` (default profile, exam icons, favicon)
- **Media:** Profile pictures stored in `media/student_profiles/` and `media/teacher_profiles/` (served via `MEDIA_URL = '/media/'` in DEBUG mode)

---

## 13. Known Observations

1. `TeacherProfileForm.save()` overrides `user.role = 'teacher'` — but it saves a `TeacherProfile` instance, not a `User` instance, so this override has no effect on the User model.
2. `requirements.txt` contains Flask/SQLAlchemy dependencies that are not used by this Django project.
3. `django-rest-framework` is installed but not configured in `INSTALLED_APPS` or used in any view.
4. `python-decouple` is installed but not used — `SECRET_KEY` and DB credentials are hardcoded in `settings.py`.
5. The `signup_teacher` view references `TeacherSignupForm` which is imported mid-file in `views.py` rather than at the top.
6. `styles.css` is empty; all styling appears to rely on `theme.css` and Bootstrap.

---

## ERP Foundation Layer

### New Apps

* centers
* courses
* batches

### New Models

#### Center
* `name` (CharField)
* `code` (CharField, unique)
* `address` (TextField)
* `phone` (CharField)

#### Course
* `center` (ForeignKey to Center)
* `name` (CharField)
* `duration` (CharField)
* `fees` (DecimalField)

#### Batch
* `course` (ForeignKey to Course)
* `teacher` (ForeignKey to TeacherProfile, nullable)
* `name` (CharField)
* `start_date` (DateField)
* `end_date` (DateField)

### StudentProfile Update

* `batch` (ForeignKey to Batch, nullable)

### ERP Relationships

```
Center
└── Course
    └── Batch
        ├── TeacherProfile
        └── StudentProfile
```

### Notes

* **Exam system unchanged**: No models, views, or business logic in the `exams` app were modified.
* **Authentication unchanged**: No modifications were made to `accounts` app, auth views, templates, or the `User` model.
* **Backward compatible**: All new fields on existing models are nullable, ensuring no disruption to existing records.

### Frontend CRUD (Phase 1.5)

To expose the newly created database tables on the frontend, full CRUD screens for Center, Course, and Batch models were implemented.

#### Forms Created
* **`CenterForm`** (`apps/centers/forms.py`): ModelForm for `Center`
* **`CourseForm`** (`apps/courses/forms.py`): ModelForm for `Course`
* **`BatchForm`** (`apps/batches/forms.py`): ModelForm for `Batch` (uses HTML5 date pickers for `start_date` and `end_date`)

#### Views Created
* **Centers:** `center_list`, `center_create`, `center_update`, `center_delete` (`apps/centers/views.py`)
* **Courses:** `course_list`, `course_create`, `course_update`, `course_delete` (`apps/courses/views.py`)
* **Batches:** `batch_list`, `batch_create`, `batch_update`, `batch_delete` (`apps/batches/views.py`)

All views are secured using the `@admin_required` decorator to restrict access strictly to Admin users. Students and Teachers receive forbidden response codes.

#### URL Configurations
* **Centers:**
  * `/centers/` (name: `center_list`)
  * `/centers/add/` (name: `center_create`)
  * `/centers/<id>/edit/` (name: `center_edit`)
  * `/centers/<id>/delete/` (name: `center_delete`)
* **Courses:**
  * `/courses/` (name: `course_list`)
  * `/courses/add/` (name: `course_create`)
  * `/courses/<id>/edit/` (name: `course_edit`)
  * `/courses/<id>/delete/` (name: `course_delete`)
* **Batches:**
  * `/batches/` (name: `batch_list`)
  * `/batches/add/` (name: `batch_create`)
  * `/batches/<id>/edit/` (name: `batch_edit`)
  * `/batches/<id>/delete/` (name: `batch_delete`)

#### Templates Created
* `apps/centers/templates/centers/`: `center_list.html`, `center_form.html`, `center_confirm_delete.html`
* `apps/courses/templates/courses/`: `course_list.html`, `course_form.html`, `course_confirm_delete.html`
* `apps/batches/templates/batches/`: `batch_list.html`, `batch_form.html`, `batch_confirm_delete.html`

#### Dashboard & Navbar Integration
* Added links for Centers, Courses, and Batches to the main navbar (`base.html`) for authenticated Admin users.
* Added a new **ERP Management** cards section inside the Admin Dashboard page (`admin_dashboard.html`).


