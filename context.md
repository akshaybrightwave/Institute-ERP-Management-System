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

### 4.9 Attendance Management (`apps/attendance`)
* **Mark Attendance:** Custom matrix layout enabling teachers and admins to select dates and mark status.
* **Logs List:** Searchable logs by Student, Batch, and Date.

### 4.10 Fees Management (`apps/fees`)
* **Fee Structure:** Course-level fees definition.
* **Collections Ledger:** Logging system for student payment dates, methods, reference numbers, and balances.

### 4.11 Certificates Management (`apps/certificates`)
* **Eligibility Engine:** Checks batch enrollment, pending fees (0), and attendance rate (>=75%) to allow issuance.
* **CRUD Audit:** Admin operations to view, revoke, issue, or delete certificate listings.

### 4.12 Reports & Analytics (`apps/reports`)
* **Reports Dashboard:** Summary counters for institutions.
* **Segment Reports:** Searchable student, batch, teacher, attendance, fee, exam, and certificate logs reports.
* **Dashboard Analytics:** Aggregation charts for active resources, collection rates, passing rates, and issuance totals.

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
            ├── Fees (Summary / Payments)
            ├── Exam (Completed / Attempted)
            └── Certificate (Eligibility / Issued / Revoked)
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
* **Students:**
  * Enforces that students only see published exams assigned to their batch.
  * Restricts access to instruction, attempt, and submission pages; students attempting to access exams outside their batch receive a `404 Not Found` or `403 Forbidden` response.
* **Teachers:**
  * Restricts the teacher's exam list, dashboard, submissions, and detailed student answer sheets to exams assigned to batches taught by that teacher.
  * Validates access to editing, deleting, managing questions/options, or viewing details of exams; teachers accessing exams not assigned to their batches are redirected to the exam list.
* **Admins:** Retain full, unrestricted platform access.

---

## 11. ERP Phase 6 — Fees Management

### 11.1 App Structure
The `fees` app is structured as follows:
* **Models:** `apps/fees/models.py` defines the `FeePayment` model.
* **Views:** `apps/fees/views.py` contains views for listing student summaries, payment ledgers, and CRUD operations.
* **Forms:** `apps/fees/forms.py` declares the `FeePaymentForm` with bootstrap styling.
* **URLs:** `apps/fees/urls.py` configures subroutes for list, add, edit, and delete actions.
* **Templates:**
  * `apps/fees/templates/fees/fees_list.html`
  * `apps/fees/templates/fees/fee_form.html`
  * `apps/fees/templates/fees/fee_confirm_delete.html`

### 11.2 Models
* **FeePayment Model:**
  * `student` (ForeignKey → `StudentProfile`, on_delete=CASCADE)
  * `amount` (DecimalField, max_digits=10, decimal_places=2)
  * `payment_date` (DateField)
  * `payment_method` (CharField with choices `cash`, `upi`, `bank`)
  * `reference_number` (CharField, blank=True)
  * `remarks` (TextField, blank=True)
  * `created_at` (DateTimeField, auto_now_add=True)

### 11.3 URLs
* `/fees/` - `fees_list` (Fees management student summaries & payment ledger page)
* `/fees/payments/add/` - `payment_create` (Record fee payment screen)
* `/fees/payments/<int:pk>/edit/` - `payment_edit` (Edit fee payment screen)
* `/fees/payments/<int:pk>/delete/` - `payment_delete` (Confirm fee payment deletion screen)

### 11.4 Business Rules & Student Fee Calculations
* Course fees are officially tracked in the `Course` model as `fees`.
* Student fee info is calculated dynamically:
  * **Total Fee:** `student.batch.course.fees` (defaults to 0.00 if student has no batch/course assigned)
  * **Paid Amount:** Sum of all `FeePayment` records for the student
  * **Pending Amount:** `Total Fee - Paid Amount`
  * **Fee Status:**
    * `PAID`: If Pending <= 0
    * `PARTIAL`: If Paid > 0 and Pending > 0
    * `PENDING`: If Paid = 0

### 11.5 Dashboard Metrics
Added the following to the Admin Dashboard metrics:
* **Total Fee Collection:** Sum of all `amount` values across `FeePayment` records.
* **Total Pending Fees:** Sum of all students' course fees minus total fee collections.
* **Students With Pending Fees:** Count of unique students whose paid amount is less than their assigned course fees.

### 11.6 Permissions & Access Control
* **Admins:** Full access to view student fee lists, record payments, and edit/delete payments.
* **Teachers:** Read-only access to view fee summaries for students enrolled in batches taught by them.
* **Students:** Read-only access to their own fee summaries via their dashboard and profile page.

---

## 12. ERP Phase 7 — Certificates Management

### 12.1 App Structure
The `certificates` app is structured as follows:
* **Models:** `apps/certificates/models.py` defines the `Certificate` model.
* **Views:** `apps/certificates/views.py` contains views for listing, creating, detailing, revoking, and deleting certificates.
* **Forms:** `apps/certificates/forms.py` declares the `CertificateForm` for certificate generation.
* **URLs:** `apps/certificates/urls.py` configures routes for listing, creating, viewing detail, revoking, and deleting certificates.
* **Templates:**
  * `apps/certificates/templates/certificates/certificate_list.html`
  * `apps/certificates/templates/certificates/certificate_form.html`
  * `apps/certificates/templates/certificates/certificate_detail.html`
  * `apps/certificates/templates/certificates/certificate_confirm_delete.html`

### 12.2 Models
* **Certificate Model:**
  * `student` (ForeignKey → `StudentProfile`, on_delete=CASCADE)
  * `batch` (ForeignKey → `Batch`, on_delete=CASCADE)
  * `course` (ForeignKey → `Course`, on_delete=CASCADE)
  * `certificate_number` (CharField, unique=True)
  * `issue_date` (DateField)
  * `status` (CharField with choices `issued`, `revoked`, default `issued`)
  * `remarks` (TextField, blank=True)
  * `created_at` (DateTimeField, auto_now_add=True)

### 12.3 Eligibility Rules
A student is only eligible for a course completion certificate if:
1. Enrolled in a batch (`student.batch` must not be null).
2. All fees are paid: Course Fee - Total Paid Fee == 0 (`pending_amount == 0`).
3. Attendance rate >= 75%. Attendance % is calculated as: `(Present Days / Total Attendance Records) * 100` using existing Attendance records.

### 12.4 URLs
* `/certificates/` - `certificate_list` (View and search all certificates)
* `/certificates/create/` - `certificate_create` (Issue a new certificate, showing student details and validating eligibility)
* `/certificates/<int:pk>/` - `certificate_detail` (Display certificate details and print-friendly version)
* `/certificates/<int:pk>/revoke/` - `certificate_revoke` (Revoke an issued certificate)
* `/certificates/<int:pk>/delete/` - `certificate_delete` (Confirm and delete a certificate log)

### 12.5 Dashboard Metrics
Added the following to the Admin Dashboard metrics:
* **Total Certificates:** Count of all certificate logs in the system.
* **Issued Certificates:** Count of certificates with status `issued`.
* **Revoked Certificates:** Count of certificates with status `revoked`.
* **Eligible Students:** Count of unique students currently enrolled in a batch who meet both the attendance >= 75% and pending fee == 0 criteria.

### 12.6 Permissions & Access Control
* **Admins:** Full access to view, issue, revoke, and delete certificates.
* **Teachers:** Read-only access to view certificates for students assigned to batches taught by them.
* **Students:** Read-only access to view only their own certificates.

---

## 13. ERP Phase 8 — Reports & Analytics

### 13.1 App Structure
The `reports` app is structured as follows:
* **Views:** `apps/reports/views.py` contains function-based views for the reports dashboard, student reports, batch reports, teacher reports, attendance reports, fee reports, exam reports, and certificate reports.
* **URLs:** `apps/reports/urls.py` configures routes for all summary and detailed report pages.
* **Templates:**
  * `apps/reports/templates/reports/reports_dashboard.html`
  * `apps/reports/templates/reports/student_report.html`
  * `apps/reports/templates/reports/batch_report.html`
  * `apps/reports/templates/reports/teacher_report.html`
  * `apps/reports/templates/reports/attendance_report.html`
  * `apps/reports/templates/reports/fee_report.html`
  * `apps/reports/templates/reports/exam_report.html`
  * `apps/reports/templates/reports/certificate_report.html`

### 13.2 Views & URLs
* `/reports/` - `reports_dashboard` (Summary counters of total items, dashboard of links)
* `/reports/students/` - `student_report` (Detailed report of student name, batch, course, attendance %, fee status, exams attempted, certificates count)
* `/reports/batches/` - `batch_report` (Detailed report of batch name, course, teacher, total students, attendance %, certificates issued)
* `/reports/teachers/` - `teacher_report` (Detailed report of teacher name, assigned batches, total students taught, total attendance records, total exams assigned)
* `/reports/attendance/` - `attendance_report` (Overall present/absent stats and logs with batch, student, and date filters)
* `/reports/fees/` - `fee_report` (Financial metrics for total collections, outstanding balances, paid and pending student counts with batch/student filters)
* `/reports/exams/` - `exam_report` (Summary of exam title, assigned batches, total attempts, average score %, pass percentage)
* `/reports/certificates/` - `certificate_report` (Verification tracking audit of student, batch, course, certificate number, status, issue date with batch/course/status filters)

### 13.3 Dashboard Metrics
Added the following to the Admin Dashboard metrics:
* **Active Students:** Count of students with `is_active=True`.
* **Active Teachers:** Count of teachers with `is_active=True`.
* **Active Batches:** Batches whose date range covers the current day (`start_date <= today <= end_date`).
* **Attendance Rate:** Total present logs divided by total logs.
* **Fee Collection Rate:** Total fees collected divided by total course fees of all enrolled students.
* **Exam Pass Rate:** Completed attempts achieving score >= passing threshold divided by total attempts.
* **Certificate Issuance Count:** Total number of active (non-revoked) certificates issued.

### 13.4 Permissions & Access Control
* **Admins:** Full access to view all reports, metrics, search outputs, and filters.
* **Teachers:** Read-only visibility restricted strictly to reports and details corresponding to batches explicitly assigned to them.
* **Students:** Restrict access completely (unauthorized roles are returned a `403 Forbidden` response).

---

## 14. Phase 10.1 — Center Role Foundation

### 14.1 New Role
* **Role Name:** `center`
* **Choices Configuration:** Configured in `apps.accounts.models.User.ROLE_CHOICES` alongside `admin`, `teacher`, and `student`.

### 14.2 Login Flow & Redirects
* **Authentication View:** `user_login` in `apps/accounts/views.py`.
* **Login Redirect Logic:**
  * Admin → Admin Dashboard (`admin_dashboard`)
  * Center → Center Dashboard (`center_dashboard`)
  * Teacher → Teacher Dashboard (`teacher_dashboard`)
  * Student → Student Dashboard (`student_dashboard`)

### 14.3 Dashboard Route
* **Dashboard View:** `center_dashboard` in `apps/centers/views.py` (uses `@login_required` verification).
* **Dashboard URL Route:** `/centers/dashboard/` (named `center_dashboard` in `apps/centers/urls.py`).
* **Dashboard Metrics:** Shows platform-wide metrics for:
  * Total Courses
  * Total Batches
  * Total Teachers
  * Total Students

### 14.4 Access Protection & Responsibilities
* **Access Control:** Restricted via `@login_required` and explicitly checks `if request.user.role != 'center': return redirect('login')`.
* **Responsibilities:** Serves as the basic landing area and verification hub for Center administrators.

### 14.5 Current Limitations
* **Permissions:** Center-level permissions have not been introduced yet.
* **Filtering:** Center-specific resource filtering is not yet implemented. All metrics display global platform counts for Courses, Batches, Teachers, and Students.


## 15. ERP Phase 10.2 — Center User Management

### 15.1 Files Modified
* **`apps/accounts/admin.py`**: Switched custom `User` registration to a subclass of `UserAdmin` (`CustomUserAdmin`) to fix password hashing issues in Django Admin.
* **`apps/accounts/forms.py`**: Added `CenterSignupForm` and `CenterEditForm` with password validation, role settings, and status editing.
* **`apps/accounts/views.py`**: Integrated the new forms into `user_add` and `user_edit` views; added support for filtering by `'center'` in `user_list`.
* **`apps/accounts/templates/accounts/user_list.html`**: Added `Add Center` action button and updated the role filtering dropdown options to include `Center`.
* **`apps/accounts/templates/accounts/user_add.html`**: Added Center form block design layout.
* **`apps/accounts/templates/accounts/user_edit.html`**: Added Center editing form block design (includes Role and Active Status inputs).

### 15.2 User Management Changes
* Admins can perform CRUD operations on Center users from the main User Management interface.
* Center users are listed along with Students and Teachers, and display a standard role badge.
* Role-based filtering on the user list includes "Center".

### 15.3 Center Role Support & Hashing Safety
* All newly created/edited Center users have their passwords hashed securely using Django's default hasher.
* The pre-existing Center user (`center01`)'s password was updated in the database to be properly hashed, resolving their login issue.

### 15.4 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```


