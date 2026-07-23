# Online Examination Portal ERP Workflow

## 1. Purpose

This document explains the Online Examination Portal as a connected ERP system. It is written for project presentation, developer onboarding, QA testing, business analysis, and AI-assisted maintenance.

The ERP is not only a set of sidebar pages. It is a complete academic business workflow where master data created by Admin becomes the foundation for centers, admissions, fees, attendance, exams, results, certificates, and passout records.

Core ERP chain:

```text
Master Setup -> Center Setup -> Course Assignment -> Student Admission -> Approval
-> Student Login -> Fees -> Attendance -> Documents -> Study Material
-> Exam Schedule -> Online Exam -> Result -> Certificate -> Passout
```

Every major screen either creates source data, moves a record to the next business status, or allows a role to view the record that belongs to them.

## 2. Overall ERP Architecture

The system is a Django-based ERP for an educational institute or training organization. It uses role-based access so Admin, Center, and Student users see different dashboards, modules, and records.

High-level structure:

```text
Authentication and Role Routing
-> Admin / Center / Student Dashboard
-> Master Data Modules
-> Operational Modules
-> Academic and Examination Modules
-> Documents, Reports, and Final Certification
```

Architecture responsibilities:

| Layer | Responsibility |
|---|---|
| Authentication | Validates user login and redirects by role. |
| Role Security | Restricts pages and records by Admin, Center, or Student role. |
| Master Data | Stores courses, categories, subjects, sessions, exam centers, and centers. |
| Student Operations | Manages admission, approval, student profile, login, fees, and attendance. |
| Academic Operations | Manages study material, exam schedule, admit card, online exam, and result. |
| Certification | Confirms completion conditions and generates certificates. |
| Reports | Uses existing records to support review, presentation, and audit. |

## 3. Complete Business Flow

The ERP starts when Admin prepares the institute structure. No meaningful student workflow can happen until the required master data exists.

```text
Admin Login
-> Dashboard
-> Course Category
-> Course
-> Subject
-> Arrange Subjects
-> Academic Session
-> Exam Centre
-> Center Information
-> Assign Course to Center
-> Student Admission
-> Pending Admission
-> Approval or Cancellation
-> Student Profile and Login
-> Fee Collection
-> Receipt
-> Attendance
-> Study Material
-> Exam Schedule
-> Admit Card
-> Online Exam
-> Result / Marksheet
-> Certificate
-> Passout
```

Stage meaning:

| Stage | Why It Exists | Who Performs It | Data Created | Next Module | If Skipped |
|---|---|---|---|---|---|
| Master Setup | Defines the academic structure. | Admin | Categories, courses, subjects, sessions, exam centers. | Center setup and admission. | Admissions and exams have no valid course/session data. |
| Center Setup | Creates institute branch or franchise records. | Admin | Center profile and center login linkage. | Course assignment. | Center users cannot manage students. |
| Course Assignment | Controls which center can use which course. | Admin | Center-course assignment. | Student admission. | Center cannot select or admit students into that course. |
| Student Admission | Captures applicant and course data. | Admin or Center | Pending admission record. | Approval flow. | Student does not enter the ERP lifecycle. |
| Approval | Converts an application into an active student record. | Admin | Approved admission, profile availability, login readiness. | Student login and operations. | Fees, attendance, exam, and certificate cannot reliably start. |
| Student Login | Enables self-service access. | Admin creates, Student uses. | Student user credentials. | Student dashboard. | Student cannot view personal records or attempt exams. |
| Fees | Tracks financial progress against course fee. | Admin or allowed Center. | Fee payment and receipt. | Reports, certificate eligibility. | Remaining fee stays unpaid; certificate may be blocked. |
| Attendance | Records academic participation. | Admin or Center. | Daily attendance. | Certificate eligibility and student view. | Attendance percentage cannot be proven. |
| Study Material | Provides course resources. | Admin or Center, Student views. | Course-linked material files. | Student learning and exam preparation. | Students may not receive academic content. |
| Exam Schedule | Defines subject-wise exam timetable. | Admin or Center if allowed. | Schedule rows by subject, session, course, center. | Admit card and exam planning. | Admit card and timetable are incomplete. |
| Online Exam | Runs objective exam attempts. | Admin creates, Student attempts. | Exam, questions, options, assignments, attempts, answers, score. | Result review. | Student cannot complete online assessment. |
| Result | Records marks and pass/fail status. | Admin. | Marksheet/result with subject marks. | Certificate. | Completion cannot be formally declared. |
| Certificate | Issues final proof of completion. | Admin or authorized Center. | Certificate number and certificate record. | Passout. | Student has no final completion document. |
| Passout | Marks lifecycle completion. | Admin. | Completed student state/report. | Archive/reporting. | Active and completed students remain mixed. |

## 4. Module Dependency Graph

Main academic dependency:

```text
Course Category
└── Course
    ├── Subjects
    │   └── Subject Arrangement
    ├── Course Fee
    │   └── Fee Collection
    │       └── Receipt
    ├── Center Course Assignment
    │   └── Student Admission
    │       ├── Pending / Approved / Cancelled Status
    │       ├── Student Profile
    │       ├── Student Login
    │       ├── Attendance
    │       ├── Admit Card
    │       ├── Online Exam Assignment
    │       ├── Result / Marksheet
    │       └── Certificate
    ├── Study Material
    ├── Exam Schedule
    └── Online Exams
```

Center dependency:

```text
Center
├── Assigned Courses
├── Student Admissions
├── Approved Students
├── Fee Collection
├── Attendance
├── Study Material
├── Exam Requests
├── Assigned Exams
├── Certificates, if authorized
└── Center Reports
```

Student dependency:

```text
Student Admission
├── Approval Status
├── User Account
├── Student Profile
├── Fee Payments
├── Attendance Records
├── Admit Card
├── Exam Attempts
├── Result / Marksheet
└── Certificate
```

## 5. Role-Based Workflow

### Admin

Admin is the main controller of the ERP.

Responsibilities:

- Manage dashboard and system summaries.
- Create course categories, courses, subjects, subject order, sessions, timetables, occupations, exam centers, and exam schedules.
- Create centers and assign courses to centers.
- Review pending admissions and move students to approved, cancelled, or passout states.
- Open student profiles and manage passwords, notifications, documents, fees, receipts, attendance, admit cards, results, certificates, study material, exams, questions, assignments, and reports.

Permissions:

- Can access all ERP records.
- Can create, edit, delete, restore, approve, cancel, publish, assign, generate, and print records depending on module.
- Can see global dashboards and reports.

Restrictions:

- Should not skip prerequisite setup before operational data entry.
- Should not approve incomplete or invalid admissions.
- Should not generate final certificates unless required academic and financial conditions are satisfied.

### Center

Center manages center-level data only.

Responsibilities:

- View center dashboard.
- Use only assigned courses.
- Add student admissions for its own center.
- View center student lists.
- Collect center student fees if allowed.
- Mark attendance for center students.
- Upload or access study material if allowed.
- Request exams and view assigned exams.
- View academic records related to its own students.

Permissions:

- Can access center-specific data.
- Can work only with students connected to the logged-in center.
- Can use only courses assigned by Admin.

Restrictions:

- Cannot access another center's records.
- Cannot approve admissions unless the project explicitly allows it; standard flow keeps final approval with Admin.
- Cannot publish complete exams unless Admin has reviewed and configured the exam.

### Student

Student is a self-service role.

Responsibilities:

- Login with enrollment number and assigned password.
- View dashboard, profile, ID card, fee record, receipts, attendance, admit card, marksheet/result, certificate, study material, exam area, notifications, and password page.
- Attempt assigned online exams.

Permissions:

- Can view only personal records.
- Can start and submit assigned exams.
- Can download or view allowed documents and study material.

Restrictions:

- Cannot access Admin or Center management pages.
- Cannot view another student's data.
- Cannot edit ERP master data, fee records, attendance, result, or certificate records.

## 6. Role Matrix

| Module | Admin | Center | Student |
|---|---|---|---|
| Dashboard | Global view | Center view | Own view |
| Course Category | Full control | Usually read-only or hidden | No access |
| Course | Full control | Assigned-course view/use | Own course view |
| Subject | Full control | Assigned-course view/use | Own course subjects if shown |
| Academic Session | Full control | View/use if allowed | No management access |
| Exam Centre | Full control | View/use if allowed | Shown on admit card |
| Center Information | Full control | Own center view | Shown in profile |
| Course Assignment | Full control | View assigned courses | No access |
| Student Admission | Create/review | Create for own center | No management access |
| Pending Students | Review all | View own center if allowed | No access |
| Approved Students | Manage all | View own center | Own profile only |
| Cancelled Students | Manage all | View own center if allowed | No access |
| Fees | All students | Own center students if allowed | Own fee record |
| Receipt | Generate/view | Own center if allowed | Own receipt |
| Attendance | All students | Own center students | Own attendance |
| Admit Card | Generate/manage | View own center if allowed | Own admit card |
| Result / Marksheet | Generate/manage | View own center if allowed | Own result |
| Certificate | Generate/manage | Generate/view if authorized | Own certificate |
| Study Material | Upload/manage | Upload/view if allowed | Own course material |
| Online Exam | Create, publish, assign | Request/view assigned | Attempt assigned |
| Reports | Global reports | Center reports | No management reports |

## 7. High-Level Database Relationships

This section explains relationships only; it does not define Django models.

```text
User
├── role: admin, center, student
├── Center link for center users
└── StudentProfile link for student users

Center
├── CenterCourseAssignment
├── StudentAdmission
├── StudyMaterial
├── ExamSchedule
├── ExamCenterAssignment
└── Certificate

Course
├── Category
├── Subject
├── SubjectOrder
├── CenterCourseAssignment
├── StudentAdmission
├── StudyMaterial
├── Exam
├── ExamSchedule
└── Certificate

StudentAdmission
├── Center
├── Course
├── User account after approval
├── FeePayment
├── Attendance
├── AdmitCard
├── Result
├── Certificate
└── ExamStudentAssignment

Exam
├── Center
├── Course
├── Questions
├── Options
├── Batch assignments
├── Center assignments
├── Student assignments
├── StudentExamAttempt
└── StudentAnswer
```

Modules that reuse these relationships:

- Dashboard reads totals from centers, students, fees, attendance, exams, attempts, results, and certificates.
- Admission uses center and course data.
- Fee collection uses approved student profile/admission and course fee.
- Attendance uses student and batch/date information.
- Admit card uses student, course, center, session, and exam schedule information.
- Result uses student, session, course duration, and subjects.
- Certificate uses student, course, center, session, fees, attendance, and result/completion conditions.

## 8. Navigation Map and Screen-to-Screen Flow

### Authentication Flow

```text
Home / Login
-> User enters credentials
-> System authenticates
-> System checks user role
-> Redirects to Admin Dashboard, Center Dashboard, or Student Dashboard
```

If login fails, the user remains on login with an error. If the role is inactive, deleted, or unauthorized, access should be blocked or redirected.

### Admin Navigation Flow

```text
Admin Dashboard
-> Course Area
   -> Course Category -> Add/List/Edit/Delete
   -> Course -> Add/List/Edit/Delete
   -> Subject -> Add/List/Edit/Delete
   -> Arrange Subjects -> Save order
-> Academics
   -> Session / Timetable / Occupation
-> Exam Centre
   -> Add/List/Edit/Delete
-> Center Information
   -> Add Center -> List Center -> View/Edit/Wallet/Assign Course/Delete
-> Student Information
   -> Admission -> Pending -> Approve/Cancel -> Approved/Cancelled/Passout
-> Student Profile
   -> Overview -> Fees -> Documents -> Password -> Notifications
-> Fees
   -> Add Payment -> Receipt
-> Attendance
   -> Mark Attendance -> Student Attendance View
-> Admit Card
   -> Generate -> View/Print
-> Results
   -> Enter Marks -> Marksheet
-> Certificates
   -> Check Eligibility -> Generate -> View/Print
-> Study Material
   -> Upload -> Course Material List
-> Exam(s)
   -> Add Exam -> Add Questions -> Publish -> Assign -> Review Attempts
-> Reports
```

### Center Navigation Flow

```text
Center Login
-> Center Dashboard
-> Assigned Courses
-> Student Admission
-> Center Student Lists
-> Fee Collection, if enabled
-> Attendance
-> Study Material, if enabled
-> Exam Request
-> Assigned Exams
-> Center Reports
```

Every center screen must filter by the logged-in center. When a center clicks a student, payment, attendance, certificate, or exam record, the opened detail page must belong to that center.

### Student Navigation Flow

```text
Student Login
-> Student Dashboard
-> Profile
-> ID Card
-> Fee Record
-> Receipt
-> Attendance
-> Study Material
-> Admit Card
-> Exam Area
-> Attempt Exam
-> Exam Result
-> Marksheet
-> Certificate
-> Change Password
```

Every student screen must filter by the logged-in student account.

## 9. Button Flow

Common buttons and redirects:

| Button / Action | Used In | Result |
|---|---|---|
| Add | Master, center, student, fee, exam, material screens | Opens a create form. |
| Save / Submit | Forms | Validates input, saves record, redirects to relevant list or next workflow page. |
| Cancel / Back | Forms | Returns to list without saving new changes. |
| View | List screens | Opens read-only or detail view for the selected record. |
| Edit | List/detail screens | Opens edit form; save returns to list/detail. |
| Delete | List/detail screens | Opens confirmation or performs soft delete; record moves out of active list. |
| Restore | Deleted lists | Reactivates soft-deleted records. |
| Assign Course | Center information | Opens course assignment screen; selected courses become available to the center. |
| Load Wallet | Center information | Opens center wallet screen; wallet balance is updated after save. |
| Approve | Pending student list | Changes admission to Approved and enables student profile/login workflow. |
| Cancel Admission | Pending student list | Changes admission to Cancelled and stores cancel reason. |
| Create Password | Approved student/profile | Creates or updates student login password. |
| Add Payment | Fees/profile | Saves fee payment and updates paid/remaining balance. |
| Receipt | Fee payment list/profile | Opens printable read-only receipt. |
| Generate Admit Card | Admit card module | Creates published admit card for approved student/session. |
| Enter Marks / Save Result | Result module | Saves marks and creates marksheet view. |
| Generate Certificate | Certificate module | Creates certificate if eligibility rules pass. |
| Add Question | Exam detail | Adds question to selected exam. |
| Add Option | Question detail | Adds answer choices and correct answer. |
| Publish Exam | Exam module | Makes exam available for assignment/attempt. |
| Assign Exam | Exam module | Links exam to center or student. |
| Start Exam | Student exam area | Opens attempt screen and starts timer. |
| Submit Exam | Exam attempt | Stores answers, calculates score, and opens result/attempt summary. |

## 10. Dashboard Flow

Dashboards are entry points, not final modules. They summarize pending work and guide users to the next page.

Admin dashboard should answer:

- How many centers, courses, students, exams, certificates, and fee records exist?
- Which admissions are pending?
- What fees are collected and pending?
- Which exams/results/certificates need action?

Center dashboard should answer:

- Which courses are assigned?
- How many center students are pending or approved?
- What center fees, attendance, exams, and study material need action?

Student dashboard should answer:

- What is my current course and center?
- What fees remain?
- What is my attendance?
- Which exams, results, admit cards, certificates, study material, and notifications are available?

## 11. Module Documentation

### Dashboard

Purpose: Give each role a starting point and summary of next actions.

Who Uses It: Admin, Center, Student.

Prerequisites: Valid login and active user role.

Navigation: Login redirects to the correct dashboard.

Workflow:

```text
Login -> Role check -> Dashboard -> Select pending action or module
```

Input: Authenticated user role.

Output: Role-specific counts, links, and workflow shortcuts.

Dependencies: Authentication, role permissions, underlying module records.

Next Module: Depends on pending work, usually admissions, fees, attendance, exams, or reports.

Common Scenarios: Admin reviews pending admissions; Center checks own students; Student checks exam/result availability.

Restrictions: Dashboard data must be filtered by role.

Related Modules: All modules.

### Course Category

Purpose: Group courses into meaningful academic categories.

Who Uses It: Admin.

Prerequisites: Admin login.

Navigation:

```text
Admin Dashboard -> Course Area -> Course Category -> Add/List/Edit/Delete
```

Workflow: Admin adds a category, saves it, and the category becomes selectable while creating courses.

Input: Category name/details.

Output: Category record.

Dependencies: None except Admin role.

Next Module: Course.

Common Scenarios: Creating categories such as diploma, certificate, undergraduate, or skill course.

Restrictions: Deleting a category should be considered carefully if courses depend on it.

Related Modules: Course, reports.

### Course

Purpose: Define the program a student enrolls in.

Who Uses It: Admin creates; Center uses assigned courses; Student views own course.

Prerequisites: Course category should exist.

Navigation:

```text
Admin Dashboard -> Course Area -> Course -> Add Course -> Save -> Course List
```

Workflow: Admin selects category, enters course name, duration, and fee, then saves. The course becomes available for subjects, center assignment, admissions, fees, study material, exams, results, and certificates.

Input: Category, course name, duration, course fee.

Output: Course record and fee baseline.

Dependencies: Category.

Next Module: Subjects and Center Course Assignment.

Common Scenarios: Add course, edit fee, view assigned centers, use course during student admission.

Restrictions: Course fee changes should not silently rewrite already admitted students if fee is stored at admission time.

Related Modules: Subject, Center, StudentAdmission, FeePayment, StudyMaterial, Exam, Result, Certificate.

### Subject and Subject Arrangement

Purpose: Define the academic papers under a course and their display/exam order.

Who Uses It: Admin; Center may view/use assigned course subjects.

Prerequisites: Course exists.

Navigation:

```text
Admin Dashboard -> Course Area -> Subject -> Add/List/Edit
Admin Dashboard -> Course Area -> Arrange Subjects -> Select Course -> Save Order
```

Workflow: Admin creates subjects with course, duration/year/semester, code, name, type, and marks. Admin then arranges subject order. This order supports timetable, admit card, marksheet, and academic sequence.

Input: Course, duration, subject code, subject name, subject type, theory marks, practical marks, order number.

Output: Subject records and subject order.

Dependencies: Course.

Next Module: Exam Schedule, Result, Admit Card.

Common Scenarios: Add Year 1 subjects, arrange semester order, edit marks.

Restrictions: Subjects should not be removed when exam schedule, result marks, or certificates already reference them unless handled safely.

Related Modules: Course, ExamScheduleSubject, ResultMarks, AdmitCard.

### Academic Session, Timetable, and Occupation

Purpose: Provide academic period and supporting reference data.

Who Uses It: Admin; Center may use if allowed.

Prerequisites: Admin login.

Navigation:

```text
Admin Dashboard -> Academics -> Session / Timetable / Occupation -> Add/Edit/Delete
```

Workflow: Admin creates active sessions and timetable data. Session records are selected in exam schedules, admit cards, results, and certificates.

Input: Session name/year, timetable details, occupation/reference data.

Output: Academic session and supporting academic records.

Dependencies: None for session creation; later modules depend on it.

Next Module: Exam Schedule, Admit Card, Result, Certificate.

Common Scenarios: Add current session, deactivate old session, edit timetable.

Restrictions: Inactive sessions should not be used for new academic outputs unless intentionally allowed.

Related Modules: ExamSchedule, AdmitCard, Result, Certificate.

### Exam Centre

Purpose: Store physical or official exam center information used in schedules and admit cards.

Who Uses It: Admin; Center may view/use if allowed; Student sees it on admit card.

Prerequisites: Admin login.

Navigation:

```text
Admin Dashboard -> Exam Centre -> Add Exam Centre -> Save -> Exam Centre List
```

Workflow: Admin creates exam center records. Exam schedule uses the selected exam center, and admit card displays it for the student.

Input: Exam center name, address, contact, code/details.

Output: Exam centre record.

Dependencies: None for creation.

Next Module: Exam Schedule and Admit Card.

Common Scenarios: Add a new exam venue, edit venue details.

Restrictions: Do not delete an exam center that is already used in published schedules without checking downstream admit cards.

Related Modules: ExamSchedule, AdmitCard.

### Center Information

Purpose: Create and maintain center or branch records.

Who Uses It: Admin creates and controls; Center views own profile.

Prerequisites: Admin login.

Navigation:

```text
Admin Dashboard -> Center Information -> Add Center -> Save Center -> List Center
```

Available actions:

- View opens center profile/detail.
- Edit opens the center edit form and returns to list/profile after save.
- Wallet opens load wallet screen and updates wallet balance.
- Assign Course opens center-course assignment.
- Delete moves the center out of active records.
- Restore returns a deleted center to active list.

Input: Center name, code, address, phone, email, owner details, validity, documents, wallet information.

Output: Center profile record.

Dependencies: None for center creation.

Next Module: Assign Courses to Center.

Common Scenarios: Add center, edit owner details, load wallet, view center certificate, restore deleted center.

Restrictions: Center users must not see records from another center.

Related Modules: User, CenterCourseAssignment, StudentAdmission, Fees, Attendance, StudyMaterial, Exams, Certificates.

### Center Course Assignment

Purpose: Control which courses a center can offer.

Who Uses It: Admin.

Prerequisites: Center and Course must exist.

Navigation:

```text
Admin Dashboard -> Center Information -> Assign Course -> Select Center -> Toggle/Select Courses -> Save
```

Workflow: Admin links courses to a center. The center can then select those courses during student admission and center-level academic work.

Input: Center, selected courses, assigned by user.

Output: Center-course assignment records.

Dependencies: Center, Course.

Next Module: Student Admission.

Common Scenarios: Add course access for a center, remove course access, verify available center courses.

Restrictions: A center should not admit students into unassigned courses.

Related Modules: Course, Center, StudentAdmission, StudyMaterial, Exams.

### Student Admission

Purpose: Start the student lifecycle by capturing identity, center, course, and document details.

Who Uses It: Admin or Center.

Prerequisites: Course, Center, and Center Course Assignment should exist.

Navigation:

```text
Admin / Center Dashboard -> Student Information -> Student Admission
-> Fill Details -> Select Center -> Select Course -> Upload Documents -> Submit
-> Pending List
```

Workflow: Admin or Center enters student data. The system saves a pending admission. The student is not fully active until Admin approves the admission.

Input: Student name, enrollment number, course, center, date of birth, gender, mobile, email, address, parent details, documents.

Output: Pending student admission.

Dependencies: Center, assigned course, uploaded documents if required.

Next Module: Approval Flow.

Common Scenarios: New admission, center-created admission, document verification, duplicate enrollment check.

Restrictions: Center can create only for its own center; student cannot self-manage admin admission records.

Related Modules: Approval, StudentProfile, Fees, Attendance, Exams, Result, Certificate.

### Approval Flow

Purpose: Convert a pending admission into an operational student or reject invalid admission data.

Who Uses It: Admin.

Prerequisites: Pending student admission.

Navigation:

```text
Admin Dashboard -> Student Information -> Pending List
-> Review Student Data -> Approve or Cancel
```

Workflow:

```text
Pending Admission
-> Admin review
-> If approved: Approved List -> Profile -> Login/password creation
-> If cancelled: Cancelled List -> Cancel reason stored
```

Input: Review decision, approval metadata, cancel reason if cancelled.

Output: Approved or cancelled admission status.

Dependencies: Complete student data, valid center, valid course.

Next Module: Student Profile and Student Login.

Common Scenarios: Approve verified student, cancel incomplete/duplicate admission, move approved student toward passout later.

Restrictions: Student operations should not proceed for cancelled records.

Related Modules: StudentProfile, User, Fees, Attendance, AdmitCard, Exams, Results, Certificates.

### Student Login and Profile

Purpose: Give approved students a central account and self-service access.

Who Uses It: Admin creates credentials; Student uses profile; Center/Admin view relevant student profile data.

Prerequisites: Approved admission.

Navigation:

```text
Approved Students -> Student Profile -> Create Password
-> Username = Enrollment No -> Student Login -> Student Dashboard
```

Workflow: After approval, the student profile becomes the central page for personal details, course, center, fee summary, payment history, documents, password, and notifications.

Input: Approved admission data, username/enrollment number, password.

Output: Student user account and accessible student dashboard.

Dependencies: Approved admission and linked user/profile.

Next Module: Fees, Attendance, Study Material, Exam, Result, Certificate.

Common Scenarios: Create password, change password, view fee summary, view documents, send notifications.

Restrictions: Student can view only own profile and cannot access management screens.

Related Modules: StudentAdmission, FeePayment, Attendance, StudyMaterial, AdmitCard, ExamAttempt, Result, Certificate.

### Fees Collection

Purpose: Track payment against the student's course fee.

Who Uses It: Admin; Center if allowed; Student views own fee record.

Prerequisites: Approved student profile and course fee.

Navigation:

```text
Admin / Center Dashboard -> Fees Collection or Student Profile
-> Select Student -> Add Payment -> Enter Amount/Date/Method/Reference/Remarks
-> Save Payment -> Fee Record -> Receipt
```

Fee formula:

```text
Total Fee = Course Fee
Paid Fee = Sum of Fee Payments
Remaining Fee = Total Fee - Paid Fee
```

Input: Student, amount, payment date, payment method, reference number, remarks.

Output: Fee payment record, updated paid amount, updated remaining amount, receipt.

Dependencies: Student profile and course fee.

Next Module: Receipt and certificate eligibility.

Common Scenarios: Cash payment, UPI payment, bank transfer, partial payment, final payment, receipt print.

Restrictions: Center fee collection must be limited to own center students; student can only view, not edit, payments.

Related Modules: StudentProfile, Course, Receipt, Reports, Certificate.

### Receipt

Purpose: Provide read-only proof of student payment.

Who Uses It: Admin, Center if allowed, Student.

Prerequisites: Saved fee payment.

Navigation:

```text
Fee Payment Saved -> Click Receipt -> Receipt Page -> Print
```

Input: Fee payment ID.

Output: Printable receipt showing student details, payment details, total fee, paid fee, and remaining fee.

Dependencies: FeePayment, StudentProfile, Course fee.

Next Module: Fee record review or certificate eligibility.

Common Scenarios: Print receipt after payment, student views receipt from fee record.

Restrictions: Receipt is read-only and must be role-filtered.

Related Modules: Fees, StudentProfile, Reports.

### Attendance

Purpose: Record student participation and support eligibility decisions.

Who Uses It: Admin, Center, Student view.

Prerequisites: Approved student; batch/date information if marking by batch.

Navigation:

```text
Admin / Center Dashboard -> Attendance
-> Select Student or Batch -> Select Date -> Mark Present/Absent -> Save
```

Student side:

```text
Student Dashboard -> Attendance -> View Own Attendance
```

Input: Student, batch if used, date, present/absent status, marked by user.

Output: Attendance record and attendance percentage.

Dependencies: Approved student and center/batch filtering.

Next Module: Certificate eligibility and reports.

Common Scenarios: Mark daily attendance, review attendance history, verify 75 percent certificate threshold where used.

Restrictions: Center sees only own students; Student sees only own records.

Related Modules: StudentAdmission, StudentProfile, Certificate, Reports.

### Study Material

Purpose: Provide course-linked learning resources to students.

Who Uses It: Admin, Center if allowed, Student.

Prerequisites: Center and Course; student must belong to a course to see related material.

Navigation:

```text
Admin / Center Dashboard -> Study Material
-> Upload Study Material -> Select Center/Course -> Save
-> Student Dashboard -> Study Material -> View/Download
```

Input: Title, file/link, center, course, uploaded by user.

Output: Course-linked material available to eligible students.

Dependencies: Center, Course, user permissions.

Next Module: Exam preparation and student learning.

Common Scenarios: Upload PDF notes, upload course resources, student downloads own course material.

Restrictions: Student should see material related to own course/center only.

Related Modules: Course, Center, StudentProfile, Exams.

### Exam Schedule

Purpose: Define the subject-wise timetable for a course, center, session, and exam centre.

Who Uses It: Admin; Center if allowed; Student sees schedule details through admit card/timetable.

Prerequisites: Center, Course, Subjects, Exam Centre, Academic Session.

Navigation:

```text
Admin / Center Dashboard -> Exam Schedule
-> Select Center -> Select Course -> Select Duration/Year/Semester
-> Select Exam Centre -> Select Academic Session
-> Enter Subject Date and Time -> Publish Schedule
```

Input: Center, course, duration, exam center, academic session, subject date/time rows.

Output: Published subject-wise schedule.

Dependencies: Course subjects, session, center, exam centre.

Next Module: Admit Card.

Common Scenarios: Create semester exam timetable, update subject time, publish final schedule.

Restrictions: Published schedules should not be changed casually after admit cards are generated.

Related Modules: Subject, AcademicSession, ExamCentre, AdmitCard.

### Admit Card

Purpose: Provide exam authorization and exam schedule details to the student.

Who Uses It: Admin generates; Student views; Center may view if allowed.

Prerequisites: Approved student, academic session, exam schedule, exam center.

Navigation:

```text
Admin Dashboard -> Admit Card -> Select Approved Student -> Generate Admit Card
-> View / Print Admit Card
Student Dashboard -> Admit Card -> View Own Admit Card
```

Input: Student, session, exam schedule/status.

Output: Published admit card with student, course, center, exam center, and subject-wise schedule.

Dependencies: StudentAdmission, Course, Center, AcademicSession, ExamSchedule.

Next Module: Online Exam or offline exam/result entry.

Common Scenarios: Generate admit card for approved student, print admit card, student downloads/view card.

Restrictions: Cancelled or unapproved students should not receive admit cards.

Related Modules: StudentProfile, ExamSchedule, Result.

### Online Exam

Purpose: Create, publish, assign, and evaluate online exams.

Who Uses It: Admin creates and assigns; Center requests and views assigned exams; Student attempts assigned exams.

Prerequisites: Course, questions, options, schedule/timing rules, published status, assignment.

Navigation:

```text
Admin Dashboard -> Exam(s)
-> Add Exam -> Select Course/Center -> Set Duration/Timer/Start-End Time
-> Save Exam -> Add Questions -> Add Options -> Mark Correct Answer
-> Publish Exam -> Assign Exam to Center or Student
```

Student attempt:

```text
Student Dashboard -> Exam Area -> View Assigned Exam
-> Start Exam -> Timer Starts -> Answer Questions -> Submit Exam
-> Result Calculated
```

Input: Exam title, course, center, duration, timing, questions, options, correct answer, assignments.

Output: Published exam, student assignment, attempt, answers, calculated score.

Dependencies: Course, Center, Student, Question, Option, assignment, publish status.

Next Module: Exam result review and final result/marksheet.

Common Scenarios: Create exam, add MCQs, publish, assign to one center, assign to specific students, student attempts, score appears.

Restrictions: Student should not see unpublished or unassigned exams; Center request is not a complete exam until Admin completes setup.

Related Modules: Course, Center, StudentAdmission, Result, Reports.

### Center Exam Request

Purpose: Allow Center to request an exam from Admin.

Who Uses It: Center submits; Admin reviews.

Prerequisites: Center login and assigned course.

Navigation:

```text
Center Dashboard -> Exam(s) -> Request
-> Select Course -> Enter Message -> Submit Request
Admin Dashboard -> Exam List / Requests -> Review Request
-> Edit Exam Details -> Add Timer/Schedule/Questions -> Publish -> Assign
```

Input: Center, course, message/request details.

Output: Exam request for Admin review.

Dependencies: Center and assigned course.

Next Module: Admin exam setup.

Common Scenarios: Center asks Admin to create a course exam.

Restrictions: Request alone should not appear to students as an active exam.

Related Modules: Online Exam, Exam Assignment, Course, Center.

### Result and Marksheet

Purpose: Record academic performance and generate student marksheet.

Who Uses It: Admin creates; Student views; Center may view center records if allowed.

Prerequisites: Approved student, session, course, subjects, marks or exam outcome.

Navigation:

```text
Admin Dashboard -> Result -> Select Student -> Enter Marks -> Save Result
-> Marksheet Generated
Student Dashboard -> Marksheet -> View Own Result
```

Input: Student, session, duration/year/semester, subject marks, pass/fail status, issue date.

Output: Result record and marksheet.

Dependencies: StudentAdmission, AcademicSession, Subject, Course.

Next Module: Certificate.

Common Scenarios: Enter subject marks, print marksheet, student views own result.

Restrictions: Student cannot edit marks; Center must not access other centers' marks.

Related Modules: Subjects, Exams, Certificate.

### Certificate

Purpose: Issue final proof that the student has completed the course requirements.

Who Uses It: Admin; Center if authorized; Student views own certificate.

Prerequisites: Approved student, student profile, course/session, fee status, attendance, result, course completion rules.

Navigation:

```text
Admin Dashboard -> Student Certificate -> Select Student
-> Check Eligibility -> Generate Certificate -> View / Print
Student Dashboard -> Certificate -> View Own Certificate
```

Eligibility can depend on:

- Approved admission.
- Student account/profile.
- Course completion.
- Fees clearance.
- Attendance condition.
- Result/pass condition.

Input: Student, session, course duration, issue date, created by user.

Output: Certificate with certificate number.

Dependencies: StudentProfile, Course, Center, AcademicSession, FeePayment, Attendance, Result.

Next Module: Passout.

Common Scenarios: Generate certificate after all dues are clear, block certificate if attendance or fee condition fails, student views certificate.

Restrictions: Certificate should not be generated for unapproved/cancelled students or students missing required eligibility.

Related Modules: Fees, Attendance, Result, StudentProfile, Reports.

### Reports

Purpose: Provide operational and presentation-level summaries.

Who Uses It: Admin, Center if allowed.

Prerequisites: Underlying module data.

Navigation:

```text
Dashboard -> Reports -> Select Report Type / Filters -> View or Export
```

Input: Date range, center, course, status, student, fee, attendance, exam, result, certificate filters.

Output: Report view/export.

Dependencies: All transactional modules.

Next Module: Business review, audit, or presentation.

Common Scenarios: Pending admissions report, fee collection report, attendance report, exam/result report, certificate report.

Restrictions: Center reports must be scoped to own center.

Related Modules: All modules.

## 12. Data Flow

### Student Admission Data Flow

```text
Student Admission Form
-> Pending Admission Record
-> Admin Review
-> Approved Admission
-> Student Profile
-> Student User Account
-> Student Login Enabled
-> Fee Collection Enabled
-> Attendance Enabled
-> Study Material Visibility
-> Exam Assignment Enabled
-> Result Generation
-> Certificate Eligibility
```

If cancelled:

```text
Pending Admission Record -> Admin Cancellation -> Cancelled List -> No student operations
```

### Fee Data Flow

```text
Course Fee
-> Student Course Fee at Admission/Profile
-> Fee Payment
-> Paid Fee Aggregation
-> Remaining Fee Calculation
-> Receipt
-> Reports
-> Certificate Fee Eligibility
```

### Attendance Data Flow

```text
Approved Student
-> Attendance Date
-> Present/Absent Record
-> Attendance History
-> Attendance Percentage
-> Student View
-> Certificate Attendance Eligibility
```

### Exam Data Flow

```text
Course + Subjects
-> Exam Schedule and/or Online Exam
-> Questions and Options
-> Publish Exam
-> Assign Exam to Center/Student
-> Student Attempt
-> Answers Stored
-> Score Calculated
-> Result / Report Review
```

### Certification Data Flow

```text
Approved Student
-> Course/Session
-> Fee Status
-> Attendance Status
-> Result Status
-> Eligibility Check
-> Certificate Generated
-> Student Certificate View
-> Passout / Completion Reporting
```

## 13. Feature Dependency Matrix

| Feature | Required Before Use | What Breaks If Missing |
|---|---|---|
| Course | Category recommended | Course cannot be grouped cleanly. |
| Subject | Course | Timetable, admit card, marksheet subject details are incomplete. |
| Subject Order | Course and subjects | Academic sequence is unclear. |
| Center | Admin setup | Center login and center data cannot operate. |
| Assign Course | Center and course | Center cannot admit students into the course. |
| Student Admission | Center, course | Student lifecycle cannot begin. |
| Approval | Pending admission | Student profile/login/fees/attendance/exams should not proceed. |
| Student Login | Approved admission | Student cannot access dashboard or attempt exams. |
| Fee Payment | Approved student and course fee | Receipt and fee eligibility cannot be calculated. |
| Attendance | Approved student | Attendance history and eligibility cannot be calculated. |
| Study Material | Course and center | Student cannot receive course-specific material. |
| Exam Schedule | Course, subjects, session, exam center | Admit card timetable is incomplete. |
| Admit Card | Approved student and schedule/session | Student lacks exam authorization document. |
| Online Exam | Course, questions, publish status, assignment | Student cannot attempt exam. |
| Result | Student, session, subjects/marks | Marksheet and certificate flow are blocked. |
| Certificate | Approved student, fees, attendance, result/completion | Final course document cannot be issued. |

## 14. Page Flow

### Admission to Certificate Screen Flow

```text
Dashboard
-> Student Admission
-> Pending List
-> Approve
-> Approved Students
-> Student Profile
-> Create Password
-> Fees Collection
-> Receipt
-> Attendance
-> Study Material
-> Exam Schedule
-> Admit Card
-> Online Exam
-> Result / Marksheet
-> Certificate
-> Passout
```

Each transition has a business reason:

- Pending List exists because admission data must be reviewed before activation.
- Approved Students exists because only approved records should enter fees, attendance, exams, and certificates.
- Student Profile exists because it centralizes the student's operational data.
- Receipt follows fee payment because it is proof of transaction.
- Attendance and results support eligibility and academic progress.
- Certificate is the final output, not an isolated document.

### Center Information Screen Flow

```text
Center Information
-> Add Center
-> Save Center
-> Center appears in List Center
-> View / Edit / Wallet / Assign Course / Delete
```

Action outcomes:

- View opens center profile and related summary.
- Edit updates center master data.
- Wallet updates center balance.
- Assign Course controls course access for that center.
- Delete removes center from active operations.
- Restore returns the center to active operations.

### Exam Screen Flow

```text
Exam List
-> Add Exam
-> Save Exam
-> Exam Detail/List
-> Add Questions
-> Add Options
-> Publish
-> Assign to Center/Student
-> Student Exam Area
-> Start Attempt
-> Submit
-> Score/Result
```

## 15. Approval Flow

Admission statuses:

- Pending: New admission created but not yet accepted.
- Approved: Admission verified and operational modules can use it.
- Cancelled: Admission rejected; reason should be stored.
- Passout: Student completed course lifecycle.

Approval decision rules:

- Verify student identity and documents.
- Confirm center and course selection.
- Confirm enrollment number uniqueness.
- Confirm required contact and guardian fields.
- Approve only when the student is ready for ERP operations.
- Cancel with reason when the record should not continue.

Approval output:

```text
Approved Student -> Student Profile -> Login Password -> Fees/Attendance/Exam/Result/Certificate
Cancelled Student -> Cancelled List -> No active ERP workflow
```

## 16. Security Flow

```text
User Login
-> Authenticate credentials
-> Check active/deleted status
-> Read user role
-> Redirect to matching dashboard
-> Filter every query by role
-> Block unauthorized direct URL access
```

Security rules:

- Admin can access all ERP records.
- Center can access only records related to its own center.
- Student can access only records linked to its own user/profile/admission.
- Inactive or deleted users should not access the system.
- Direct URL access must not bypass role checks.
- Detail, edit, delete, receipt, admit card, marksheet, certificate, and exam attempt pages must validate ownership.

## 17. End-to-End Student Lifecycle

```text
Admission
-> Pending Review
-> Approval
-> Enrollment
-> Student Login
-> Profile
-> Fee Payments
-> Receipt
-> Attendance
-> Study Material
-> Admit Card
-> Online Exam
-> Result / Marksheet
-> Certificate
-> Course Completion
-> Passout
```

Lifecycle explanation:

1. Student enters the ERP through admission.
2. Pending status protects the system from using unverified data.
3. Admin approval activates the student for operational modules.
4. Student login allows self-service access.
5. Fees track financial progress.
6. Attendance records participation.
7. Study material supports learning.
8. Admit card authorizes exam participation.
9. Online exam or result entry records academic performance.
10. Certificate confirms completion.
11. Passout separates completed students from active students.

## 18. End-to-End Center Lifecycle

```text
Admin creates Center
-> Admin verifies center details
-> Admin assigns courses
-> Center login/dashboard becomes useful
-> Center admits students into assigned courses
-> Admin approves those students
-> Center manages own students, fees, attendance, materials, and exam requests
-> Center views own reports and academic records
```

If a center has no assigned courses, it cannot run the admission workflow correctly. If center filtering fails, the ERP exposes cross-center data and violates role security.

## 19. End-to-End Exam Lifecycle

```text
Course and Subjects Ready
-> Exam Centre and Session Ready
-> Exam Schedule Created
-> Admit Card Generated
-> Online Exam Created
-> Questions and Options Added
-> Correct Answers Marked
-> Exam Published
-> Exam Assigned
-> Student Attempts Exam
-> Answers Stored
-> Score Calculated
-> Result / Marksheet Created
-> Certificate Eligibility Updated
```

Important exam rules:

- Center exam request is only a request.
- Admin must complete exam setup before students can attempt it.
- Students should see only published and assigned exams.
- Timer and start/end time control exam availability.
- Attempt data must be stored before score/result can be reviewed.

## 20. Real User Journeys

### Admin Journey

```text
Login
-> Admin Dashboard
-> Master Setup
-> Center Setup
-> Course Assignment
-> Student Approval
-> Fee/Attendance Monitoring
-> Exam Management
-> Result Management
-> Certificate Generation
-> Reports
```

Admin's journey is control-focused. Admin creates the structure, validates records, publishes academic outputs, and reviews the whole ERP.

### Center Journey

```text
Login
-> Center Dashboard
-> View Assigned Courses
-> Admit Students
-> Track Own Student Lists
-> Collect Fees, if allowed
-> Mark Attendance
-> Upload/View Study Material, if allowed
-> Request Exams
-> View Assigned Exams
-> Review Center Records
```

Center's journey is operations-focused. The center works inside boundaries created by Admin.

### Student Journey

```text
Login
-> Student Dashboard
-> Profile
-> Fee Record and Receipt
-> Attendance
-> Study Material
-> Admit Card
-> Exam Area
-> Attempt Exam
-> Exam Result
-> Marksheet
-> Certificate
```

Student's journey is self-service-focused. The student views personal academic and financial progress and attempts assigned exams.

## 21. Full Demo Workflow

Use this order for project demo:

1. Login as Admin.
2. Show Admin Dashboard.
3. Add Course Category.
4. Add Course.
5. Add Subjects.
6. Arrange Subjects.
7. Add Academic Session and Exam Centre.
8. Add Center.
9. Assign Course to Center.
10. Add Student Admission.
11. Show Pending List.
12. Approve Student.
13. Create Student Login Password.
14. Open Student Profile.
15. Add Fee Payment.
16. Show Receipt.
17. Mark Attendance.
18. Upload Study Material.
19. Create Exam Schedule.
20. Generate Admit Card.
21. Create Online Exam.
22. Add Questions and Options.
23. Publish Exam.
24. Assign Exam.
25. Login as Student.
26. Show Student Dashboard.
27. Show Fee Record and Receipt.
28. Show Attendance and Study Material.
29. Show Admit Card.
30. Attempt Exam.
31. Show Exam Result.
32. Login as Admin.
33. Enter Result / Marksheet.
34. Generate Certificate.
35. Login as Center.
36. Show Center Dashboard and center-specific data.
37. Show that Center cannot access another center's records.
38. Show that Student cannot access another student's records.

## 22. Manual Testing Checklist

Check these flows before final presentation:

- Admin login works and redirects to Admin Dashboard.
- Center login works and redirects to Center Dashboard.
- Student login works and redirects to Student Dashboard.
- Role-based direct URL protection works.
- Course category add/list/edit/delete works.
- Course add/list/edit/delete works.
- Subject add/list/edit/delete works.
- Arrange subject order saves and displays correctly.
- Academic session add/list/edit/status works.
- Exam centre add/list/edit/delete works.
- Center add/list/edit/profile/wallet/delete/restore works.
- Course assignment to center works.
- Center sees only assigned courses.
- Student admission saves from Admin.
- Student admission saves from Center for own center only.
- Pending list shows new admission.
- Admin approval works.
- Admin cancellation stores reason.
- Approved student moves to approved list.
- Cancelled student moves to cancelled list.
- Student profile opens.
- Student password creation works.
- Student login works with enrollment number.
- Student dashboard shows only personal data.
- Fee payment saves.
- Paid fee updates.
- Remaining fee updates.
- Receipt opens and prints.
- Attendance saves.
- Student attendance view works.
- Study material uploads.
- Student can view/download own course material.
- Exam schedule saves subject-wise date and time.
- Admit card opens and includes student/course/center/exam center/schedule.
- Online exam creation works.
- Question creation works.
- Option creation and correct answer selection works.
- Exam publish works.
- Exam assignment works.
- Student can see only assigned published exam.
- Student can attempt exam.
- Timer and submit flow work.
- Exam result calculates correctly.
- Result/marksheet opens.
- Certificate eligibility is checked.
- Certificate opens and prints.
- Center sees only own center data.
- Student sees only own data.
- Reports use correct role filters.

## 23. Final ERP Summary

The ERP begins with Admin master setup. Courses, subjects, academic sessions, exam centers, and centers form the foundation. Admin assigns courses to centers. Admin or Center creates student admission. Admin reviews and approves the admission. After approval, the student profile and login become active.

Once active, the student moves through fees, receipts, attendance, study material, admit card, online exam, result, marksheet, certificate, and passout. Each later module depends on the correctness of earlier modules.

Final workflow:

```text
Admin Setup
-> Center Setup
-> Course Assignment
-> Student Admission
-> Approval
-> Student Login
-> Fees
-> Attendance
-> Study Material
-> Exam Schedule
-> Admit Card
-> Online Exam
-> Result
-> Certificate
-> Passout
```

