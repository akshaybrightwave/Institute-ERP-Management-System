# Online Examination Portal & ERP — Project Context

## 1. Project Overview

A unified full-stack Online Examination Portal and Enterprise Resource Planning (ERP) system built using a Django monolithic architecture. The system enables Administrators, Teachers, and Students to manage centers, courses, batches, exams, users, and profiles with role-based access control.

---

## 2. Technology Stack & Architecture

* **Backend Framework:** Python 3.13, Django 5.1.4
* **Database:** MySQL 8 (`online_exam_portal_db`) via `mysqlclient` (SQLite configurations exist but are inactive)
* **ORM:** Django ORM with BigAutoField Primary Keys
* **Frontend:** HTML5, CSS3 (Vanilla CSS with `static/css/theme.css`), Bootstrap 5.3, JavaScript
* **Views & Templates:** Function Based Views (FBVs) and Django template rendering (no Django Rest Framework / APIs used for core functionality)
* **Authentication:** Django built-in authentication + custom `AbstractUser` model
* **Media Handling:** Pillow (image uploads for profile pictures)
* **Forms Helper:** `django-widget-tweaks`

---

## 3. Project Structure

The project code is organized into modular applications within the `apps/` directory:

```text
Online-Examination-Portal/
├── apps/                # Django apps package
│   ├── accounts/        # Auth, User CRUD, Admin Dashboard, Feedback
│   ├── centers/         # Center model & CRUD management
│   ├── courses/         # Course model & CRUD management
│   ├── batches/         # Batch model & CRUD management
│   ├── exams/           # Exam, Question, Option, grading & attempts management
│   ├── students/        # StudentProfile, Student Dashboard, Taking Exams
│   └── teachers/        # TeacherProfile, Teacher Dashboard, Submissions, Batch View
│
├── online_exam_portal/  # Django project configuration package
│   ├── settings.py
│   ├── urls.py          # Central routing (pointing to modular app urls)
│   ├── wsgi.py
│   └── asgi.py
│
├── static/              # Global static assets (theme.css, default images)
├── media/               # User-uploaded files (student and teacher profiles)
├── templates/           # Global templates (404.html, 500.html)
├── manage.py
└── requirements.txt
```

---

## 4. Completed Modules

### 4.1 Authentication & Authorization
* **Custom User Model:** Extends `AbstractUser` with a custom `role` field (`admin`, `teacher`, `student`).
* **Role-Based Redirects:** Redirects users upon login to their respective dashboards based on their role.
* **Access Control Decorators:** Uses `@admin_required`, `@login_required`, and `@user_passes_test` helpers to protect resources.
* **Password Reset Flow:** Standard 4-step Django email-based password reset workflow.

### 4.2 User Management
* **User CRUD:** Admin interface to list, create, edit, and delete users.
* **Admission Forms:** Refactored, responsive side-by-side grid layouts for managing student and teacher details.

### 4.3 Center Management (`apps/centers`)
* **Center Model:**
  * `name` (CharField)
  * `code` (CharField, unique)
  * `address` (TextField)
  * `phone` (CharField)
* **CRUD Screens:** Admin-only views to create, list, edit, and delete centers.

### 4.4 Course Management (`apps/courses`)
* **Course Model:**
  * `center` (ForeignKey → Center)
  * `name` (CharField)
  * `duration` (CharField)
  * `fees` (DecimalField)
* **CRUD Screens:** Admin-only views to create, list, edit, and delete courses.

### 4.5 Batch Management (`apps/batches`)
* **Batch Model:**
  * `course` (ForeignKey → Course)
  * `teacher` (ForeignKey → TeacherProfile, nullable)
  * `name` (CharField)
  * `start_date` (DateField)
  * `end_date` (DateField)
* **CRUD Screens:** Admin-only views to create, list, edit, and delete batches.

### 4.6 Student Management (`apps/students`)
* **StudentProfile Model:** Linked 1:1 to custom User model. Contains fields for full name, phone, email, profile picture, bio, and batch association.
* **Student Dashboard:** Enrolled student stats, attempts count, and exam listings.
* **Student Profile Management:** Interface for students to view and update their profile details.

### 4.7 Teacher Management (`apps/teachers`)
* **TeacherProfile Model:** Linked 1:1 to custom User model. Contains fields for full name, phone, email, profile picture, and bio.
* **Teacher Dashboard:** Displays metrics, exams created, submissions details, and assigned batches.
* **Teacher Profile Management:** View-only profiles and profile edit screens.

### 4.8 Examination System (`apps/exams`)
* **Data Models:**
  * **Exam:** Core exam metadata configuration.
  * **Question:** Questions linked to exams with marks.
  * **Option:** MCQ choices linked to questions with correct indicators.
  * **StudentExamAttempt:** Captures start, submit, score, and completion stats.
  * **StudentAnswer:** Links attempts to question choices.
* **Auto-Grading:** Calculated automatically upon exam submission, factoring in positive question marks and negative marking, clamped to a minimum of 0.
* **Timer Validation:** Server-side validation of elapsed time to auto-submit when remaining time runs out.
* **Analytics & Reports:** Detailed submission tracking, including exam averages, high/low scores, pass rates, and CSV exporting of submissions.

---

## 5. Integration Modules

### 5.1 Student ↔ Batch Integration
* **Relationship:** `StudentProfile` contains `batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)`.
* **Batch Assignment:** Administrators can assign and change student batch mappings via the User CRUD screens.
* **Batch Enrollment List:** The admin-facing Batch details screen displays the total count and list of enrolled students.

### 5.2 Teacher ↔ Batch Integration
* **Relationship:** `Batch` contains `teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True)`.
* **Teacher Assignment:** Administrators can assign and edit the assigned teacher on the Batch CRUD screens.
* **Dashboard Integration:** Teachers see their assigned batches list on the Teacher Dashboard, displaying Batch Name, Course Name, Start/End Dates, and total enrolled students count.
* **Teacher Batch Details:** Read-only batch details page for teachers displaying assigned course info, schedule, and table of enrolled students.
* **Teacher Profile details:** Renders the list of assigned batches and total count.
* **Security Validation:** Enforces strict ownership validation in `teacher_batch_detail` view:
  ```python
  batch = get_object_or_404(Batch, pk=pk, teacher=profile)
  ```
  This ensures teachers can only view details and student lists for batches explicitly assigned to them, returning a `404 Not Found` for unassigned batches.

---

## 6. Current ERP Hierarchy

```text
Center
└── Course
    └── Batch
        ├── Teacher (Assigned to Batch)
        └── Student (Enrolled in Batch)
            ├── Attendance (History / Records)
            └── Exam (Completed / Attempted)
```

---

## 7. Completed Dashboard Metrics

### 7.1 Admin Dashboard
* Total Centers count
* Total Courses count
* Total Batches count
* Total Students count
* Total Teachers count
* Total Exams count
* Unread feedback submissions

### 7.2 Teacher Dashboard
* Assigned Batches count
* Total Students across assigned batches
* Total Exams (created by the logged-in teacher)
* Submissions and questions counters

### 7.3 Student Dashboard
* Enrolled Exams
* Completed Attempts count
* Average Score (%)

---

## 8. Database Schema Overview
* **`accounts`:** User, Feedback models.
* **`exams`:** Exam, Question, Option, StudentExamAttempt, StudentAnswer models.
* **`students`:** StudentProfile model.
* **`teachers`:** TeacherProfile model.
* **`centers`:** Center model.
* **`courses`:** Course model.
* **`batches`:** Batch model.

---

## 9. Completed Phase: ERP Phase 4 — Exam ↔ Batch Integration

### 9.1 Data Models & Relationships
* **Exam ↔ Batch Relationship:** Integrated `batches = models.ManyToManyField('batches.Batch', blank=True, related_name='exams')` inside the `Exam` model. This allows an exam to be assigned to one or more batches.

### 9.2 Workflows & Forms
* **Create/Edit Exam:** Added the `batches` select-multiple field to the `ExamForm` form.
  * Administrators can assign any batch to the exam.
  * Teachers can only assign batches explicitly assigned to them.
* **Batch Details:** Both Admin Batch Detail and Teacher Batch Detail pages display a list of all exams assigned to that batch.
* **Exam Details:** Added an Exam Detail view and page (`/exams/<int:exam_id>/`) visible to Admins and Teachers, showing:
  * Exam core settings and information.
  * Assigned batches.
  * Student count (unique students enrolled in the assigned batches).
  * Attempt count (total student attempts).

### 9.3 Security & Role-Based Access Control
* **Students:**
  * Enforces that students only see published exams assigned to their batch.
  * Restricts access to instruction, attempt, and submission pages; students attempting to access exams outside their batch receive a `404 Not Found` or `403 Forbidden` response.
* **Teachers:**
  * Restricts the teacher's exam list, dashboard, submissions, and detailed student answer sheets to exams assigned to batches taught by that teacher.
  * Validates access to editing, deleting, managing questions/options, or viewing details of exams; teachers accessing exams not assigned to their batches are redirected to the exam list.
* **Admins:** Retain full, unrestricted platform access.

### 9.4 Dashboard Metrics Updates
* **Admin Dashboard:**
  * `Total Exams` (All exams on the platform)
  * `Active Exams` (Exams currently published)
  * `Batch Assigned Exams` (Exams assigned to at least one batch)
* **Teacher Dashboard:**
  * `My Exams` (Exams assigned to the teacher's batches)
  * `My Batches` (Batches assigned to the teacher)
  * `Students Covered` (Total student count across the teacher's batches)
* **Student Dashboard:**
  * `Enrolled Exams` (Count of published exams assigned specifically to the student's batch)

---

## 10. ERP Phase 5 — Attendance Management

### 10.1 Attendance App Structure
The `attendance` app is structured as follows:
* **Models:** `apps/attendance/models.py` defines the `Attendance` model.
* **Views:** `apps/attendance/views.py` contains Function Based Views for marking batch attendance and displaying the filtered attendance list.
* **URLs:** `apps/attendance/urls.py` configures routes for list and marking views.
* **Templates:**
  * `apps/attendance/templates/attendance/mark_attendance.html`
  * `apps/attendance/templates/attendance/attendance_list.html`

### 10.2 Attendance Model
The `Attendance` model tracks student attendance status per batch and date:
* `batch` (ForeignKey → `Batch`, on_delete=CASCADE)
* `student` (ForeignKey → `StudentProfile`, on_delete=CASCADE)
* `date` (DateField)
* `status` (CharField with choices `present`, `absent`)
* `marked_by` (ForeignKey → `TeacherProfile`, null=True, blank=True, on_delete=models.SET_NULL)
* `created_at` (DateTimeField, auto_now_add=True)
* Unique Constraint: `unique_together = ('student', 'date')` to prevent duplicate attendance logs.

### 10.3 URLs Added
* `/attendance/` - `attendance_list` (Attendance Management list page)
* `/attendance/mark/<int:batch_id>/` - `mark_attendance` (Mark attendance screen)

### 10.4 Views & Logic
* `attendance_list(request)`: Filters and displays attendance logs. Admins can view all batches/students. Teachers can only view attendance for students and batches assigned to them.
* `mark_attendance(request, batch_id)`: Renders table of students in the batch for a selected date. Performs `update_or_create` on submit. Validates that teachers can only mark attendance for their assigned batches.

### 10.5 Templates & UI Components
* **Mark Attendance:** Responsive table featuring Bootstrap `.btn-check` styled toggle buttons (green for Present, red for Absent), "Mark All Present", "Mark All Absent" helper controls, and a date picker.
* **Attendance List:** Filter bar with search controls by Batch, Student, and Date, plus a table displaying student names, batches, date, soft success/danger badges for status, and the marking teacher.

### 10.6 Permissions & Access Control
* **Admins:** Full access to view all attendance, search/filter, and mark attendance for any batch.
* **Teachers:** Access restricted to marking and viewing attendance only for their assigned batches.
* **Students:** Restriced from viewing the main attendance management list. Can view their own percentage, present/absent counts, and 5 most recent records on their profile page.
