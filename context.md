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


## 16. ERP Phase 10.3 — Center ↔ Center Mapping

### 16.1 Relationship Implemented
* **User ↔ Center Relationship**: Added a 1:1 `OneToOneField` named `center` to the `User` model, pointing to `'centers.Center'` with `on_delete=models.SET_NULL, null=True, blank=True`. This allows a Center User to manage exactly one Center, and a Center to be optionally managed by one Center User.

### 16.2 Files Modified
* **`apps/accounts/models.py`**: Added `center` field to custom `User` model and implemented model validation in `clean()` to ensure only Center users can be assigned a Center.
* **`apps/accounts/forms.py`**: Updated `CenterSignupForm` and `CenterEditForm` to show the `center` selection dropdown (populating it with all active `Center` records).
* **`apps/accounts/templates/accounts/user_list.html`**: Modified user table rows to display the assigned center name under the username for Center users.
* **`apps/accounts/templates/accounts/user_add.html`**: Added "Assigned Center" selection row to Center creation form design.
* **`apps/accounts/templates/accounts/user_edit.html`**: Added "Assigned Center" selection row next to Role field for Center user edit form design.
* **`apps/centers/templates/centers/center_dashboard.html`**: Rendered the name of the assigned Center next to the user's dashboard role badge (or "No Center Assigned" if not mapped).

### 16.3 Database Migrations Added
* **Migration**: `apps/accounts/migrations/0004_user_center.py` adds the `center` foreign key field to the custom `User` table. Applied successfully.

### 16.4 Assignment Workflow & Validation
* Administrators can optionally assign a Center location when creating or editing a Center user.
* Model-level validation ensures non-Center users (Admins, Teachers, Students) cannot be assigned a Center location, raising a form validation error on save.

### 16.5 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```



## 17. ERP Phase 10.4 — Center Data Isolation

### 17.1 Scope & Enforcements
* **Course Isolation**: Replaced `@admin_required` decorators with `@login_required` checks, and updated querysets to filter Course list based on `request.user.center` for Center users. Restricts editing/deleting of courses belonging to other centers.
* **Batch Isolation**: Replaced `@admin_required` with `@login_required`. Filters the Batch list to only show batches of courses belonging to the assigned center. Filters `Course` and `Teacher` choice fields dynamically in the forms to only allow selecting resources valid for that Center.
* **User Management Isolation**: Replaced `@admin_required` with role-based checks. Restricts list view so Center users only see students/teachers assigned to batches in their center (along with globally unassigned ones). Denies creating/editing/deleting Admin and other Center users. Restricts assignment batch choice to the Center's batches.
* **Detail Page Security**: Enforces that direct URL detail page access to batches, courses, and student/teacher profile updates belonging to other centers returns a `403 Forbidden` response.
* **Dashboard Metrics**: Restructures the `center_dashboard` counts to show totals only for Courses, Batches, Teachers, and Students within the user's assigned Center.

### 17.2 Files Modified
* **`apps/courses/views.py`**: Added access control rules, detail page verification, and queryset filter mapping.
* **`apps/batches/views.py`**: Switched view decorators, isolated batch list and detail views, and restricted forms dropdown querysets.
* **`apps/accounts/views.py`**: Switched CRUD view decorators, applied Q-lookup filtering, added sign-up/edit form validations and choice filtering, and restricted admin/center target edits.
* **`apps/centers/views.py`**: Updated `center_dashboard` to filter metrics querysets by center.

### 17.3 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```



## 18. Teacher Dashboard UI Redesign

### 18.1 UI/UX Optimizations
* **Horizontal Profile Header**: Converted the teacher profile card into a compact horizontal header row spanning full width, displaying the photo, teacher details, and profile action buttons in a single compact bar.
* **Statistics Row**: Reorganized the 5 statistics elements into a horizontal row of equal-width compact cards directly below the profile header.
* **Assigned Batches Table**: Elevated as the primary page element, using full width with no course name truncation, larger action buttons, and better cell padding.
* **Quick Actions**: Placed in a compact horizontal row below the Batches section.
* **Exams Table Visibility Hierarchy**: Highlighted view, submissions, and question list actions as buttons, and de-emphasized the delete action by styling it as a muted text link.
* **Vertical Density**: Enabled seeing the profile header, stats row, and the entire primary Batches table above the fold on laptop screens.

### 18.2 Files Modified
* **`apps/teachers/templates/teacher/teacher_dashboard.html`**: Redesigned to support the horizontal flow and prioritization of core teaching workflows.



## 19. ERP Phase 10.5 — Center Operational Permissions

### 19.1 Permissions & Features Implemented
* **Center Course Management**: Center users can view, create, edit, and delete courses. Newly created courses automatically belong to their assigned Center. Cross-center course operations are strictly forbidden (returns `403 Forbidden`).
* **Center Batch Management**: Center users can view, create, edit, and delete batches. Form choice querysets dynamically restrict courses and teachers to the logged-in center's courses and active/unassigned teachers.
* **Center Student Management**: Center users can view, create, and edit student accounts. Batch choices are restricted to the center's own batches. Cross-center student edits/deletes are blocked.
* **Center Teacher Management**: Center users can view, create, and edit teacher accounts. Teacher assignments are restricted to center batches.
* **Attendance Access**: Center users can search, filter, and view attendance logs belonging only to their assigned Center. Center users cannot mark or edit attendance.
* **UI Action Adjustments**: Excluded the "Add Center" button from the User Management page for Center users. Conditionally hid attendance marking and day-editing links/buttons from Center users in batch list and batch detail pages.
* **Security Validation**: Validated that direct URL queries, updates, and deletes across centers return `403 Forbidden` responses.

### 19.2 Files Modified
* **`apps/accounts/templates/accounts/user_list.html`**: Restrained "Add Center" user action visibility to administrators only.
* **`apps/batches/templates/batches/batch_list.html`**: Hidden "Attendance" marking link for Center users.
* **`apps/batches/templates/batches/batch_detail.html`**: Restricted batch attendance marking actions and day-level editing columns to administrative/teacher accounts.
* **`apps/centers/templates/centers/center_dashboard.html`**: Converted informational placeholder block into a sleek "Center Management Portal" dashboard panel containing direct quick links to Courses, Batches, Users, and Attendance logs.

### 19.3 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```
* Programmatic integration verification tests executed successfully.



## 20. ERP Phase 10.6 — Center Dashboard Enhancement

### 20.1 Features & Summaries Implemented
* **Overview Metrics (Feature 1)**: Displays center-specific counts of Students, Teachers, Courses, Batches, Exams, and Certificates for the logged-in center.
* **Attendance Summary (Feature 2)**: Added an Attendance Overview card showing Total Present, Total Absent, and Attendance Percentage logs.
* **Fees Summary (Feature 3)**: Added a Fees Summary card displaying Total Fees Collected, Outstanding Balances, and Paid vs. Pending Student counts.
* **Certificate Summary (Feature 4)**: Shows total issued and revoked certificate counts, alongside a dynamic list of students currently eligible for certificates.
* **Exam Summary (Feature 5)**: Renders total, active, and completed exam counts plus total student exam attempts for the center's batches.
* **Activity Feeds (Features 6, 7, 8)**: Features three modern Bootstrap tables showcasing the latest 5 Students, latest 5 Batches, and latest 5 Upcoming Exams.
* **Quick Actions Grid (Feature 9)**: Includes prominent shortcuts to Add Student, Add Teacher, Add Batch, View Attendance, Manage Fees, and Manage Courses.
* **Performance Snapshot (Feature 10)**: Displays progress indicators tracking the center's overall Attendance Rate, Fee Collection Rate, Exam Participation Rate, and Certificate Eligibility Rate.

### 20.2 Performance Optimizations Applied
* Combined student payment aggregation and batch/course relationships into a single annotated queryset with `Coalesce` and `select_related` to eliminate N+1 query loops.
* Utilized Django's `prefetch_related('batches')` to efficiently load upcoming exam batch relationships in a single optimized hit.
* Leveraged database aggregation for attendance stats and exam potential calculation.

### 20.3 Files Modified
* **`apps/centers/views.py`**: Enhanced `center_dashboard` view to load, optimize, and calculate all operational parameters.
* **`apps/centers/templates/centers/center_dashboard.html`**: Redesigned dashboard content block with stats widgets, summaries, activity tables, quick action links, progress bars, and custom style helper blocks.

### 20.4 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```
* Programmatic dashboard context and layout rendering integration checks passed successfully.


## 21. ERP Phase 10.7 — Center Reports & Analytics

### 21.1 Features Implemented
* **Reports Dashboard (Feature 1)**: Enhanced the reports dashboard to showcase Student, Attendance, Exam, Fee, and Certificate reports. Conditionally hid Teacher Reports, Batch Reports, and "Total Centers" statistics card from the dashboard view for Center role users.
* **Student Reports (Feature 2)**: Added Course and Batch selection filters, analytics summary cards (Total, Active, and Inactive students), and Course-wise/Batch-wise student breakdowns.
* **Attendance Reports (Feature 3)**: Integrated attendance percentage summaries, present/absent stats cards, and filters for Date, Batch, and Student.
* **Exam Reports (Feature 4)**: Added filters for Exam and Batch, and integrated 8 analytics summary cards showing metrics like Pass Rate, highest/lowest scores, and averages.
* **Fees Reports (Feature 5)**: Added Course/Batch/Student selectors and fee collection summaries (Total Collections, Total Outstanding, Collection Rate, Paid/Pending Student counts).
* **Certificate Reports (Feature 6)**: Added Course/Batch/Status filters and summary cards showing total, issued, revoked, and eligible student counts.
* **Export Functionality (Feature 7)**: Integrated standard, built-in Django CSV generation for all five reports using `?export=csv`. Formats and applies filters and strict center-specific security isolation.
* **Performance Optimization (Feature 8)**: Leveraged optimized aggregations (`Sum`, `Count`, `Avg`, `Max`, `Min`), select_related, and prefetch_related to load reports efficiently without N+1 query loops.
* **Analytics Summary Cards (Feature 9)**: Implemented stats cards for all report types in their respective templates.

### 21.2 Security Validations
* Enforced that Center users only see students, attendance, fee collections, exam attempts, and certificates belonging to their assigned Center.
* Restricts CSV exports to only download records for the center managed by the logged-in user.
* Direct cross-center queries and data filtering attempts are strictly isolated by database queries.

### 21.3 Files Modified
* **`apps/reports/templates/reports/reports_dashboard.html`**: Hides teacher/batch reports and total centers card from Center users.
* **`apps/reports/templates/reports/student_report.html`**: Displays course/batch select filters, breakdowns, summary cards, and Export CSV action.
* **`apps/reports/templates/reports/attendance_report.html`**: Adds Export CSV action.
* **`apps/reports/templates/reports/exam_report.html`**: Adds filters, summary cards, and Export CSV action.
* **`apps/reports/templates/reports/fee_report.html`**: Integrates Course/Batch/Student filters, 5 analytics summary cards, and Export CSV action.
* **`apps/reports/templates/reports/certificate_report.html`**: Displays summary cards and Export CSV action.

### 21.4 Validation Results
* Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```
* Programmatic data isolation and CSV export verification script `verify_reports_security.py` completed successfully, ensuring complete cross-center security isolation.


## 22. ERP Phase 10.8 — Center Fee Operations

### 22.1 Objective & Design
Implemented Center Fee Operations allowing Center role users to perform fee collection, view center-specific summaries, manage payment ledger history, and generate printable receipts.

### 22.2 Changes & Extensions
- **Forms (`apps/fees/forms.py`)**: 
  - Overrode `FeePaymentForm.__init__` to filter student querysets by `request.user.center` for Center users.
  - Implemented `clean_amount` to prevent negative and zero payment inputs.
  - Implemented `clean` method validation to block cross-center assignments and prevent overpayments against the student's outstanding course fees.
- **Views (`apps/fees/views.py`)**: 
  - Restructured `fees_list` to handle center role authorization, center-restricted ledger querysets, and calculate six fee metrics (Total Students, Collected Fees, Pending Fees, Collection % Rate, Paid Students count, Pending Students count).
  - Modified `payment_create`, `payment_update`, and `payment_delete` to enforce center-specific student limits and prevent direct URL editing or deletion of other centers' records.
  - Added new view `payment_receipt` to dynamically render fee receipt parameters.
- **URLs (`apps/fees/urls.py`)**: Registered `payments/<int:pk>/receipt/` route.
- **Templates (`apps/fees/templates/fees/`)**:
  - `fees_list.html`: Rendered metrics summary cards at the top of the Fees management interface. Restructured the list tables and action buttons to conditionally show ledger history, receipt button, edit, delete, and collection controls for Center users.
  - `fee_form.html`: Integrated a dynamic "Student Fee Summary" card. Appended a JavaScript dropdown change listener that triggers page reloads to update the fee summary dynamically.
  - `receipt.html` [NEW]: Created printable fee receipt using double-bordered styling and printable CSS media queries.

### 22.3 Security Validations
- Direct URL access validation returns `403 Forbidden` for cross-center actions on `/payments/<id>/edit/`, `/payments/<id>/delete/`, and `/payments/<id>/receipt/`.
- Programmatic validation script `verify_fees_security.py` successfully completed all negative values validation, overpayment blocks, cross-center assignments, and URL manipulation tests.

### 22.4 Validation Results
- Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```

---

## 23. ERP Phase 10.9 — Center Exam Operations & Monitoring

### 23.1 Objective & Design
Implemented Center Exam Operations & Monitoring enabling Center users to view and monitor examinations, student attempts, analytics, and CSV exports restricted exclusively to their center's scope. 

### 23.2 Changes & Extensions
- **Views (`apps/exams/views.py`, `apps/centers/views.py`, `apps/reports/views.py`)**:
  - `center_dashboard`: Enhanced to calculate and return eight exam-monitoring metrics, Top 5 Performers, Low 5 Performers, and Batch Performance analytics for the center.
  - `exam_list`: Updated to filter exams by center courses and batches, compiling metrics (`exams_data`) for the UI.
  - `exam_detail`: Configured to load detailed analytics (Average score, Highest/Lowest scores, Pass/Fail rate, and counts) and restrict access to the logged-in center.
  - `center_exam_results` [NEW]: Fetches student attempts for a specific exam under the center.
  - `center_attempts_list` [NEW]: Displays paginated and filterable student attempts list.
  - `center_attempt_detail` [NEW]: Shows student question responses, correct choices, and marks in a read-only screen.
  - `export_exam_results_csv`, `export_student_performance_csv`, `export_batch_performance_csv` [NEW]: Generates CSV exports filtered by center.
  - `exam_report` in reports: Secured parameters to prevent cross-center batch queries.
- **Templates**:
  - `center_dashboard.html`: Integrated the **Center Exam Monitoring** panel, top/low performers, batch analytics, and new quick actions shortcuts.
  - `exam_list.html`: Conditional styling for Center role to display assigned batch, attempts, avg score, and status columns while hiding editing buttons.
  - `exam_detail.html`: Displays the metrics card deck and performance analytics progress indicators.
  - `center_exam_results.html`, `center_attempts_list.html`, `attempt_detail.html` [NEW]: Created read-only dashboards and filters.
- **Navigation (`base.html`)**: Included Exams link for Center users.

### 23.3 Security Validations
- Access attempts outside the user's center return a `403 Forbidden` response for exam detail, results, attempt details, and CSV downloads.
- Programmatic validation script `verify_exams_security.py` successfully completed all isolation, read-only redirect, and URL boundary checks.

### 23.4 Validation Results
- Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```


## 24. ERP Phase 10.10 — Center Attendance Operations

### 24.1 Objective & Architecture
Implemented Center Attendance Operations allowing Center role users to perform individual and batch attendance creation, edit attendance logs, view center-specific metrics, and download filtered report CSV files. All operations are strictly isolated to the user's assigned Center.

### 24.2 Key Implementations
- **Form Configuration (`apps/attendance/forms.py`) [NEW]**:
  - Implements `AttendanceForm` with dynamic queryset filtering on `student` and `batch` fields based on `request.user.center`.
  - Performs validation checks on `student.batch == batch`, center isolation, and uniqueness constraint checks on `(student, date)` pairs to prevent integrity errors.
- **Views (`apps/attendance/views.py`, `apps/reports/views.py`, `apps/centers/views.py`)**:
  - `attendance_list`: Update queryset and filters to restrict Center users to their own center. Integrates bulk attendance percentage calculations per page and CSV export support (`?export=csv`). Enforces URL parameter validation (returns `403 Forbidden` for other centers' batches/students).
  - `mark_attendance`: Expanded access to `center` role, validating that the batch course belongs to the user's center (otherwise returns `403 Forbidden`).
  - `attendance_create` [NEW]: Renders individual creation form with live reloading using GET parameter `?student=<id>` to dynamically query student summary metrics and auto-select batch.
  - `attendance_edit` [NEW]: Validates that the attendance record belongs to the center, rendering individual edit view.
  - `attendance_report` in reports: Supports filtering by Course, Batch, Student, Start Date, and End Date, with strict center boundary verification on query parameters.
  - `center_dashboard` in centers: Calculates and returns five metrics: Total Students, Present Today, Absent Today, Monthly Attendance %, and Students Below 75% Overall Attendance.
- **Templates**:
  - `attendance_list.html`: Adds Course and Attendance % columns, Mark Attendance and Export CSV header actions, and conditional Actions column (Edit Day, Edit Record) for the `center` role.
  - `attendance_form.html` [NEW]: Renders a premium interface with Left column: Student Summary Card and Right column: Form fields. Includes JavaScript logic to reload page on student selection.
  - `batch_list.html` and `batch_detail.html`: Restores Attendance buttons and actions for Center users.
  - `attendance_report.html` in reports: Integrates Course filter dropdown, Start/End Date datepickers, and Course column in log table.
  - `center_dashboard.html` in centers: Renders **Center Attendance Monitoring** card deck and quick actions shortcuts (Attendance Management and Attendance Reports).

### 24.3 Security & Isolation Controls
- Restricts queryset bounds using `request.user.center` filtering.
- Direct URL manipulation on `/attendance/<pk>/edit/`, `/attendance/mark/<batch_id>/`, and report filters throw a `403 Forbidden` response for unauthorized cross-center targets.
- Programmatic testing script `verify_attendance_security.py` successfully validated all form validation errors, duplicate entries blocks, cross-center parameter constraints, and URL boundary checks.


## 25. ERP Phase 10.10.1 — Attendance Navigation & Redirect Fixes

### 25.1 Objective
Resolve navigation and redirect bugs identified in the Center Attendance operations flow for Center role users.

### 25.2 Root Causes & Applied Fixes
- **Attendance Reports Back Button**: In `apps/reports/templates/reports/attendance_report.html`, the back button was hardcoded to `/reports/` (`reports_dashboard`), redirecting Center users to the main Reports & Analytics dashboard. Fixed by introducing role-aware template checking (`request.user.role == 'center'`) to redirect them back to the Center Dashboard (`center_dashboard`).
- **Mark Attendance Back Button**: In `apps/attendance/templates/attendance/mark_attendance.html`, the back button defaulted to `teacher_batch_detail` for non-Admin users, which redirected Center users to the Login page due to teacher-role validations. Fixed by allowing Center users to route to the correct `batch_detail` page.
- **Mark Attendance Cancel Button**: The form lacked a cancel pathway. Added a Cancel button beside "Save Attendance" linking directly back to `attendance_list`.
- **Authentication Protection**: Verified all individual create/edit/list views are decorated with `@login_required` (specifically `attendance_create`).

### 25.3 Validation Results
- Django system check:
  ```text
  System check identified no issues (0 silenced).
  ```
- Validation script `verify_navigation_fixes.py` successfully executed and verified all redirect routes and auth checks.


# Phase 11.1 — Tele Caller CRM Operations

## Overview

The Tele Caller module provides complete inquiry, lead, call tracking, follow-up management, reporting, and performance monitoring functionality within the Management Portal.

The module is accessible only to:

* Super Admin
* Tele Caller

through role-based access controls and portal isolation middleware.

---

## Features Implemented

### Inquiry Management

Implemented capabilities:

* Create Inquiry
* Edit Inquiry
* Delete Inquiry
* Inquiry Details
* Inquiry Search
* Inquiry Filters
* Inquiry Status Tracking

Inquiry information includes:

* Inquiry Number
* Student Name
* Mobile Number
* Email
* Interested Course
* Source
* Status
* Remarks

---

### Lead Management

Implemented capabilities:

* Inquiry to Lead Conversion
* Lead Tracking
* Lead Status Management
* Lead Assignment
* Lead Notes
* Lead Activity Tracking

---

### Call Management

Implemented capabilities:

* Call Logging
* Call Outcome Tracking
* Call Duration Recording
* Tele Caller Remarks

---

### Follow-Up Management

Implemented capabilities:

* Schedule Follow-Ups
* Pending Follow-Ups
* Completed Follow-Ups
* Overdue Follow-Ups
* Reminder Tracking

---

### Reports & Analytics

Implemented reports:

* Inquiry Reports
* Lead Reports
* Follow-Up Reports
* Tele Caller Performance Reports

Export formats:

* CSV Export
* Excel Export

---

## Security & Access Control

Implemented controls:

* PortalAccessMiddleware
* Role-Based Access Control
* Queryset-Level Filtering
* URL Manipulation Protection
* HTTP 403 Forbidden Responses for Unauthorized Access

Users can only access records permitted by their assigned role.

---

## Navigation Structure

Management Portal

├── Dashboard

├── Tele Caller

│ ├── Inquiries

│ ├── Leads

│ ├── Call Logs

│ ├── Follow-Ups

│ └── Reports

├── Counselor

└── HR

---

## Verification Results

Verified functionality:

* Inquiry lifecycle management
* Lead conversion workflow
* Call tracking workflow
* Follow-up workflow
* Reporting and exports
* Role security enforcement
* Portal isolation middleware

---

## Completion Status

Module Status: Completed

Production Readiness: Production Ready

Completion Percentage: 100%

---

## Notes

This module forms the first business workflow inside the Management Portal and serves as the lead-generation layer before Counselor admission processing and ERP student onboarding.
