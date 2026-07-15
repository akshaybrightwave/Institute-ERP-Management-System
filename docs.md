# Institute ERP Management System Documentation

## 1. Project Overview

### Purpose
The **Institute ERP Management System** (Examly) is an enterprise-grade administrative and academic platform designed to streamline operations for educational institutes, centers, and coaching academies. It manages the complete lifecycle of students, teachers, centers, batches, courses, fees, attendance, examinations, and certificates.

### Goals
* **Academic Automation**: Eliminate manual tracking of student enrollment, batches, and course schedules.
* **Examination Lifecycle Management**: Provide a robust, time-restricted online examination engine with automated grading and instant reporting.
* **Financial Oversight**: Maintain a secure ledger of student fee payments, installment tracking, and center wallets.
* **Operational Control**: Protect system actions via strict Role-Based Access Control (RBAC) across distinct dashboards.
* **Audit & Compliance**: Automate compliance checks for certificate generation based on fee clearance and attendance rates.

### Key Features
* **Center Lifecycle & Course Assignments**: Manage physical/exam centers and map courses.
* **Verified Admissions Queue**: Multi-stage verification pipeline for student admissions (Pending ➔ Approved / Cancelled).
* **Attendance & Fee Ledger**: Record-level tracking of class attendance and payment collection.
* **Online Exam Engine**: MCQ test engine with timing constraints, question randomization, auto-scoring, and negative marking.
* **Analytical Dashboards**: Segment-specific metrics, counts, and interactive visual data widgets.

### ERP Architecture
The system is built on a modular monolith pattern using Django. Shared database tables are protected through soft-delete patterns, and user access is filtered based on authentication state and user roles.

```
+---------------------------------------------------------------------------------+
|                                  ERP System                                     |
+---------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
+-------v-------+                 +-------v-------+                 +-------v-------+
|  Admin Portal |                 | Center Portal |                 | Student Portal|
+---------------+                 +---------------+                 +---------------+
```

### Technology Stack
* **Language**: Python 3.13
* **Web Framework**: Django 5.1.4
* **Database**: MySQL 8.0 (using `mysqlclient` driver)
* **Frontend**: HTML5, CSS3, JavaScript, jQuery, Bootstrap 5.3
* **Data Visualization**: Chart.js
* **Tables**: DataTables (Bootstrap 5 integration)
* **Alerts**: SweetAlert2

---

## 2. Technology Stack

| Technology / Library | Version | Purpose |
|---|---|---|
| **Python** | 3.13 | Core programming language |
| **Django** | 5.1.4 | High-level MVC/MVT web framework |
| **MySQL** | 8.0 | Relational database management system |
| **mysqlclient** | 2.2+ | Python interface to MySQL |
| **Bootstrap** | 5.3 | Styling, responsive UI layout, and utilities |
| **JavaScript / jQuery** | ES6 / 3.7+ | Client-side scripting and AJAX requests |
| **DataTables** | 1.13.7 | Enhanced, sortable, paginated, and exportable data grid views |
| **SweetAlert2** | 11 | Rich modal alert notifications for successes and confirmations |
| **Pillow** | 10.0+ | Image file validation and storage for user profile photos |
| **django-widget-tweaks** | 1.5.0 | Rendering form inputs with custom classes directly inside templates |
| **python-decouple** | 3.8 | Configuration separation (settings/environment variables) |

---

## 3. Project Architecture

### Folder Structure
The codebase follows standard Django guidelines, wrapping all business applications inside a dedicated `apps/` directory:
```text
Online-Examination-Portal/
├── apps/                    # Core business applications package
│   ├── accounts/            # Users, auth, admin dashboard, central layout
│   ├── centers/             # Registered institutes, wallet, certificates
│   ├── courses/             # Academic curricula, fee configurations
│   ├── categories/          # Classifications of courses
│   ├── batches/             # Active course groups, start/end dates, schedules
│   ├── exams/               # Exam parameters, questions, attempts, exam centres
│   ├── students/            # Student profiles, admissions queue, student dashboard
│   ├── teachers/            # Teacher profiles, class metrics, batch view
│   ├── attendance/          # Student attendance logs, matrix interface
│   ├── fees/                # Fee payment logs, payment structures
│   ├── certificates/        # Audited certificate records, revocation engine
│   ├── reports/             # Aggregation and export utilities (CSV/Excel)
│   ├── academics/           # Sessions, timetables, and occupation data
│   ├── admit_card/          # Admit card generation and layouts
│   ├── results/             # Exam marksheet logs
│   ├── study_material/      # Curated resources download area
│   └── soft_delete.py       # Global soft-delete model base class
│
├── online_exam_portal/      # Project settings, WSGI, and ASGI files
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/                  # Shared stylesheet themes, JS scripts, icons
├── media/                   # User-uploaded documents and avatar images
├── templates/               # Global templates (e.g. 404, 500 pages)
└── manage.py
```

### Modular Design
Each application operates independently, mapping its own database models, view controllers, URL configurations, forms, and template folder structures. Cross-app references are managed via Django's relational mappings (ForeignKeys, ManyToManyFields).

### Django MVT Architecture & Request Flow
1. **Request Entry**: A web request hits the central `online_exam_portal/urls.py` router and matches a path.
2. **View Logic**: The request is routed to a function-based view (FBV) inside the respective app's `views.py`.
3. **Data Operations**: The view interacts with the database through model wrappers (`models.py`) subclassing `SoftDeleteModel`.
4. **Context Preparation**: The view formats query results into a dictionary context.
5. **Template Rendering**: The HTML template is rendered with the context and returned to the browser.

### Authentication Flow
1. User supplies credentials on the login screen.
2. The view queries the custom User model (extending `AbstractUser`).
3. On successful authentication, role-based checks identify the user role (`admin`, `center`, `teacher`, `student`).
4. The user is redirected to their respective role-based dashboard.

---

## 4. Installed Applications

### Accounts (`apps/accounts`)
* **Purpose**: Manages system authentication, custom user models, and the main administrator dashboard.
* **Models**: `User` (custom `AbstractUser` with a custom `role` field).
* **Views**: `login_view`, `logout_view`, `admin_dashboard`.
* **Templates**: `accounts/base.html`, `accounts/admin_dashboard.html`, `accounts/login.html`.
* **URLs**: Routing for login, logout, password resets, and user management.

### Centers (`apps/centers`)
* **Purpose**: Coordinates registered physical institutes, tracks course assignments, and logs balance transactions.
* **Models**: `Center`, `CenterCourseAssignment`, `CenterCertificate`.
* **Views**: `center_list`, `center_create`, `center_update`, `center_delete`, `center_dashboard`.
* **Templates**: `centers/center_list.html`, `centers/center_form.html`, `centers/center_dashboard.html`.
* **URLs**: Root path `/centers/` with sub-actions for editing, updating, and loading wallets.

### Students (`apps/students`)
* **Purpose**: Manages student admissions, verification queues, identity card creation, and student dashboards.
* **Models**: `StudentAdmission` (represents applicant status), `StudentProfile` (active profiles linked 1:1 to User).
* **Views**: `student_dashboard`, `student_profile`, `student_admission_view`, `student_details_view`, `student_id_card_view`, `student_pending_list`.
* **Templates**: `student/student_dashboard.html`, `student/student_profile_admin.html`, `student/student_admission.html`.
* **URLs**: Root paths for student profile management, dashboards, and admission listings.

### Teachers (`apps/teachers`)
* **Purpose**: Teacher details, classroom dashboards, and assignment mappings.
* **Models**: `TeacherProfile` (linked 1:1 to custom User model).
* **Views**: `teacher_dashboard`, `teacher_profile_view`, `teacher_batch_detail`.
* **Templates**: `teachers/teacher_dashboard.html`, `teachers/teacher_profile.html`.
* **URLs**: Routing for teacher profiles and assigned batch details.

### Courses (`apps/courses`)
* **Purpose**: Catalog of available educational curriculums, associated durations, and standard fees.
* **Models**: `Course`.
* **Views**: `course_list`, `course_create`, `course_update`, `course_delete`.
* **Templates**: `courses/course_list.html`.
* **URLs**: Curricula administration routes.

### Categories (`apps/categories`)
* **Purpose**: Organizing courses into academic classifications.
* **Models**: `Category`.
* **Views**: `category_list`, `category_create`.
* **Templates**: `categories/category_list.html`.

### Batches (`apps/batches`)
* **Purpose**: Scheduling study groups for active courses and mapping teachers.
* **Models**: `Batch`.
* **Views**: `batch_list`, `batch_create`, `batch_update`, `batch_delete`.
* **Templates**: `batches/batch_list.html`.

### Exams (`apps/exams`)
* **Purpose**: Managing online exams, questions, MCQ options, grading parameters, scheduling, and independent exam centres.
* **Models**: `Exam`, `Question`, `Option`, `StudentExamAttempt`, `StudentAnswer`, `ExamSchedule`, `ExamStudentAssignment`, `ExamCentre`.
* **Views**: `exam_list`, `add_exam`, `question_list`, `attempt_exam`, `submit_exam`, `exam_centre_list`, `exam_centre_edit`.
* **Templates**: `exam/exam_list.html`, `exam/exam_instructions.html`, `exam/exam_centre_list.html`.
* **URLs**: Route groups for exam creation, schedule mapping, student attempts, and exam center CRUD.

### Attendance (`apps/attendance`)
* **Purpose**: Logs and displays classroom attendance records.
* **Models**: `Attendance`.
* **Views**: `mark_attendance`, `attendance_logs_list`, `student_my_attendance`.
* **Templates**: `attendance/mark_attendance.html`, `attendance/attendance_list.html`.

### Fees (`apps/fees`)
* **Purpose**: Handles collections, student payment ledgers, and billing summaries.
* **Models**: `FeePayment`.
* **Views**: `fee_ledger`, `record_payment`, `student_payment_setting`.
* **Templates**: `fees/fee_ledger.html`.

### Certificates (`apps/certificates`)
* **Purpose**: Evaluating eligibility rules and handling certification audits.
* **Models**: `Certificate` (relates to StudentAdmission).
* **Views**: `certificate_list`, `issue_certificate`, `revoke_certificate`.
* **Templates**: `certificates/certificate_list.html`.

### Study Material (`apps/study_material`)
* **Purpose**: File downloads area for enrolled students.
* **Models**: `StudyMaterial`.
* **Views**: `material_list`, `upload_material`.
* **Templates**: `study_material/material_list.html`.

### Results (`apps/results`)
* **Purpose**: Centralized storage and tracking of final scores and marksheets.
* **Models**: `Result`.
* **Views**: `result_list`, `result_detail`.
* **Templates**: `results/result_list.html`.

---

## 5. User Roles

The system operates four major authorization layers:

| Role | Access Permissions | Dashboard | Accessible Modules | Restricted Modules |
|---|---|---|---|---|
| **Super Admin / Admin** | Complete access to system databases, settings, and CRUD actions. | Admin Dashboard | Accounts, Centers, Students, Teachers, Courses, Batches, Exams, Fees, Certificates, Reports. | None |
| **Center** | Manage own center details, view assigned courses, track own student admissions, and query own students' exam status. | Center Dashboard | Center details, Admissions, Course assignments, Student listings, and Attempts. | Global settings, User role edits, cross-center datasets. |
| **Teacher** | Read assigned batch configurations, view enrolled students, and submit student attendance sheets. | Teacher Dashboard | Assigned Batches, Student lists, Mark Attendance. | Student Admissions, Fees ledger, Certificate issuance, System settings. |
| **Student** | Attempt assigned exams, view own exam results, download study files, and verify own attendance logs and fee status. | Student Dashboard | Exam attempts, results history, profile, attendance logs, admit cards, and payments schedule. | All administration views, CRUD actions, and dashboards of other roles. |

---

## 6. Authentication System

* **Login**: The system uses `django.contrib.auth.views.LoginView` styled inside `accounts/login.html`. It accepts a username and password, authenticates the credentials, and initializes a session.
* **Logout**: Standard logout action clearing the user session and redirecting the browser to the login screen.
* **Password Policy**: Standard Django password hashing (using PBKDF2 with SHA-256) and validation.
* **Role Detection & Redirects**: A custom login redirect view evaluates the logged-in user's role:
  ```text
  If User.role == 'admin' -> Redirect to admin_dashboard
  If User.role == 'center' -> Redirect to center_dashboard
  If User.role == 'teacher' -> Redirect to teacher_dashboard
  If User.role == 'student' -> Redirect to student_dashboard
  ```
* **Session Flow**: Standard cookie-based session tracking. Custom middleware (`PortalAccessMiddleware`) validates access paths on every request.

---

## 7. Module Documentation

### Center Management
* **Purpose**: Administrative master module to control operating branches.
* **Workflow**: Admin creates Center ➔ System generates Center code and links a custom User account ➔ Center logs in and accesses its dashboard.
* **Models**: `Center`, `CenterCourseAssignment`.
* **Permissions**: Admin-only write actions, Center read actions.
* **Business Rules**: Each Center must have a unique center code. Soft deletion preserves related student history.

### Student Admissions & Verification Queue
* **Purpose**: Coordinates admissions verification.
* **Workflow**: Applicant inputs admission details ➔ Record saved as `Pending` ➔ Admin reviews queue ➔ Dynamic choice to `Approve` or `Cancel` (with rejection notes).
* **Models**: `StudentAdmission`, `StudentProfile`.
* **Business Rules**: Approved students are automatically assigned login credentials. Enrollment numbers are auto-generated based on center prefixes.

### Course & Batch Scheduling
* **Purpose**: Configures academic schedules.
* **Workflow**: Admin creates Course ➔ Maps Course to one or more Centers ➔ Instantiates a Batch mapping a Course, Center, and Teacher.
* **Models**: `Course`, `Batch`.
* **Business Rules**: Course fees are configurable at the course level. Batch start and end dates determine attendance eligibility windows.

### Examination System
* **Purpose**: Secure online assessment testing.
* **Workflow**: Admin/Center creates Exam ➔ Assigns Batches/Courses ➔ Student starts test ➔ Timer ticks down ➔ Auto-submit triggered ➔ Automated grading applied (accounting for negative marking).
* **Models**: `Exam`, `Question`, `Option`, `StudentExamAttempt`.
* **Business Rules**: Student exam attempts cannot be edited once completed unless explicit admin retake parameters are enabled. Score calculations are performed server-side.

### Attendance logs
* **Purpose**: Records presence rates.
* **Workflow**: Teacher selects Batch and Date ➔ Grid updates with active students ➔ Teacher marks present/late/absent ➔ Saves to database.
* **Models**: `Attendance`.
* **Business Rules**: Attendance entries are restricted to active batch rosters.

### Fees Ledger
* **Purpose**: Manages billing ledgers.
* **Workflow**: Student pays installment ➔ Ledger logged with date and reference ➔ Outstanding balance updated.
* **Models**: `FeePayment`.
* **Business Rules**: Complete payment triggers automatic fee clearance status.

### Certificate Auditing
* **Purpose**: Evaluates candidate certificates.
* **Workflow**: Check student eligibility ➔ If attendance >= 75% and outstanding fees == 0 ➔ Issue certificate.
* **Models**: `Certificate`.

---

## 8. Database Relationships

The relational links between the primary database entities are structured as follows:

```
[Center] 1 <----- N [CenterCourseAssignment] N -----> 1 [Course]
   |                                                      |
   |                                                      |
   +------------------ 1 <----- N [Batch] <---------------+
                                    |
                                    | 1
                                    |
                                    v N
                             [StudentAdmission] 1 <----- 1 [User] <----- 1 [StudentProfile]
                                    |
                                    | 1
                                    |
                                    +----> N [StudentExamAttempt]
                                    +----> N [Certificate]
```

* **Center Course Assignment**: Many-to-Many bridge mapping courses to centers with an active flag.
* **Batch**: ForeignKey to `Course` and `Center`, securing isolated study groups.
* **Student Admission**: ForeignKey to `Course` and `Center`. Link to `User` establishes login ownership.
* **Student Exam Attempt**: ForeignKey to `User` and `Exam`, preserving test performance metadata.

---

## 9. Business Workflow

### 1. Center Setup & Enrolment Workflow
```
[Admin Creates Center]
         |
         v
[Auto-Create Center User Account]
         |
         v
[Admin Assigns Courses to Center]
         |
         v
[Center Dashboard Becomes Active]
```

### 2. Student Admission & Examination Workflow
```
[Student Registration Form Submitted] ---> (Status: Pending)
                                                  |
                                                  v
                                      [Admin Reviews Queue]
                                                  |
                               +------------------+------------------+
                               |                                     |
                       (Status: Approved)                   (Status: Cancelled)
                               |                                     |
                               v                                     v
                 [Generate Enrollment No]                    [Log Rejection Notes]
                               |
                               v
               [Auto-Create Student Login]
                               |
                               v
                  [Assign Student to Batch]
                               |
                               v
                  [Attempt Assigned Exams]
                               |
                               v
                 [Auto-Grade Exam Submission]
                               |
                               v
              [Audit Fees & Attendance Checks]
                               |
                               v
                  [Issue Final Certificate]
```

---

## 10. Dashboard Documentation

### Admin Dashboard
* **KPI Cards**: Total Centers, Total Active Batches, Total Enrolled Students, Total Exams Created, Global Collections.
* **Sidebar**: User CRUD, Center Information, Course Mapping, Admissions Queue, Batch Scheduler, Certificates Audit, Reports.
* **Widgets**: Dynamic collection charts (Chart.js) and recent registration tables.

### Center Dashboard
* **KPI Cards**: Active Students Count, Assigned Courses, Wallet Balance, Exam Submissions.
* **Sidebar**: Student Admissions, Wallet Top-up, Course Mappings, Exam Monitoring.
* **Widgets**: Quick Student Search and course enrollment graphs.

### Student Dashboard
* **KPI Cards**: Assigned Exams, Total Attempts, Cumulative Average Score, Cleared Fee Percentage.
* **Sidebar**: Profile page, Exam Listing, Marks History, Fee Ledger, Download Admit Cards.
* **Widgets**: Exam Guidelines, Upcoming Schedules, and Payment Status indicators.

---

## 11. URL Structure

| Prefix Path | Responsible Application | Target Routing Actions |
|---|---|---|
| `/accounts/` | `accounts` | Login, logout, user creation, password modification, admin control screens. |
| `/centers/` | `centers` (Overridden) | Maps dynamically to the Admin Exam Centre CRUD. |
| `/centers/info-list/`| `centers` | Primary list of Center Information profiles. |
| `/students/` | `students` | Admission requests, verified students grid, profile updating. |
| `/courses/` | `courses` | Class curricula configurations and fee listings. |
| `/batches/` | `batches` | Batch date intervals and assigned instructors. |
| `/exams/` | `exams` | Exam metadata creation, question editing, and grading configurations. |
| `/exam-centres/` | `exams` | Dedicated exam centre settings and CRUD actions. |
| `/attendance/` | `attendance` | Classroom mark sheets and student logs query. |
| `/fees/` | `fees` | Billing ledger and payment updates. |
| `/certificates/` | `certificates` | Verification listings and revocation. |

---

## 12. Security

* **Authentication**: Enforced on all views via Django's `@login_required` decorator or middleware.
* **Authorization (RBAC)**: Role checks prevent unauthorized requests (e.g. students accessing `/centers/` will trigger a redirect or 403 Forbidden).
* **Cross-Site Request Forgery (CSRF)**: Every POST request form includes `{% csrf_token %}` tokens.
* **Input Sanitization**: Handled by Django's form processing system to sanitize strings and escape HTML tags.
* **Data Isolation**: Center-specific views query filtering:
  ```python
  Center.objects.filter(center_user=request.user)
  ```
  This restricts center managers from querying data from other registered centers.
* **Soft Delete**: Deletions flag records as `is_deleted = True` and write a `deleted_at` timestamp. This retains the data in the database and keeps relational structures intact.

---

## 13. Coding Standards

* **Naming Conventions**: Models use `PascalCase` syntax. Variable names and view actions use `snake_case` patterns. Database tables use standard prefixing (e.g., `centers_centercertificate`).
* **Views Pattern**: Function-Based Views (FBVs) manage routing logic to keep workflows explicit.
* **Database Queries**: Avoid querying within loops. Prefetch related entities to minimize DB queries.
* **Transactions**: Modifying database records is wrapped in transaction blocks:
  ```python
  from django.db import transaction
  with transaction.atomic():
      # database writes
  ```
* **Error Handling**: Use `get_object_or_404` helper decorators for safe object retrieval. Form validations use built-in model validations before running save operations.

---

## 14. Performance Optimizations

* **Query Prefetching**: Uses `.select_related()` (for single ForeignKeys) and `.prefetch_related()` (for ManyToManyFields) to load related models in one query.
* **Pagination**: Lists are paginated using Django's standard `Paginator` helper class (10–15 items per page) to optimize render times.
* **Server-Side DataTables**: Large data grids load records dynamically via AJAX calls, reducing initial HTML rendering overhead.

---

## 15. Third-party Libraries

* **Pillow**: Required for processing user image uploads (avatars/documents).
* **django-widget-tweaks**: Permits tweaking Bootstrap CSS attributes directly inside HTML templates.
* **python-decouple**: Keeps environment configurations (secret keys, database credentials) separate from code.
* **mysqlclient**: High-performance C-wrapper driver connecting Django to MySQL databases.

---

## 16. Current Features

* [x] Custom Role-Based Authentication (Admin, Center, Teacher, Student)
* [x] Student Admissions Pipeline & Verification Queue
* [x] Center Management & Course Mappings
* [x] Batch Scheduling & Teacher Assignments
* [x] Fee Collections Ledger
* [x] Verification checks for Certificate Eligibility
* [x] Exam Creation Engine (MCQ format, negative markings, timing limits)
* [x] Student ID Card and Admit Card Generation
* [x] Center Wallet Transaction Ledger
* [x] Soft Delete Pattern (`is_deleted` flag query filters)

---

## 17. Future Scope

* **REST API Layer**: Add Django REST Framework (DRF) interfaces for integration with external portals or mobile apps.
* **Payment Gateway**: Integrate third-party payment gateways (e.g. Razorpay, Stripe) for automated payment logging.
* **Auto-Proctoring**: Implement face recognition and window-blur alerts on the examination engine.
* **Dynamic PDF Templates**: Drag-and-drop builder for custom certificate template designs.
* **Notification System**: Add SMS and WhatsApp API alert integrations for transaction records and exam releases.

---

## 18. Deployment Guide

### Environment Setup
Create a `.env` file in the project root:
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=erp.yourdomain.com
DB_NAME=online_exam_portal_db
DB_USER=production_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=3306
```

### Production Checklist
1. Install package requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Generate Django database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Gather static assets into the configured root directory:
   ```bash
   python manage.py collectstatic --noinput
   ```
4. Verify deployment settings:
   ```bash
   python manage.py check --deploy
   ```
5. Configure WSGI servers (e.g., Gunicorn or uWSGI) behind a Nginx reverse proxy.

---

## 19. Backup & Restore

### Database Backup
Export the MySQL database to a compressed SQL file:
```bash
mysqldump -u erp_user -p online_exam_portal_db | gzip > db_backup_$(date +%F).sql.gz
```

### Database Restore
Restore data from a SQL backup:
```bash
gunzip < db_backup_2026-07-14.sql.gz | mysql -u erp_user -p online_exam_portal_db
```

### Media Backup
Archive the user-uploaded media files:
```bash
tar -czf media_backup_$(date +%F).tar.gz media/
```

---

## 20. Troubleshooting

### ValueError: "Cannot query X: Must be Y instance"
* **Cause**: Attempting to query a model using a string or a different model instance on a ForeignKey filter.
* **Solution**: Ensure your query filter targets the correct model instance:
  ```python
  # Wrong
  Attendance.objects.filter(student=profile)
  # Correct
  Attendance.objects.filter(student=admission)
  ```

### Static / Media Files Not Found (404)
* **Cause**: Incorrect web server configurations or missing run commands in production.
* **Solution**: In development, ensure `DEBUG = True` is active. In production, configure Nginx to serve the `static/` and `media/` directories directly.

### Migration Conflict Errors
* **Cause**: Out-of-sync database schemas or local changes conflicting with previous migration files.
* **Solution**: Inspect the migrations table using `python manage.py showmigrations` and roll back or merge migrations using `python manage.py makemigrations --merge`.

---

## 21. Developer Notes

### Reusable Abstractions
- **SoftDeleteModel**: Inherit from `apps.soft_delete.SoftDeleteModel` to enable soft-delete support. All queries using `.objects` default to filtering out soft-deleted records. Use `.all_objects` to query all records.

### Development Guidelines
- **No Direct Schema Updates**: Never update database tables manually. Always use Django migrations.
- **Access Controls**: Every new view must be decorated with appropriate permissions (e.g. `@admin_required`, `@login_required`) to prevent unauthorized access.
