# Institute ERP Management System - Software Explanation

This document explains the full software flow in simple language so an admin, operator, centre user, or student can understand how the ERP works and how each section connects with the other sections.

## 1. Software Overview

Institute ERP Management System is a role-based ERP and online examination platform. The software manages the complete institute workflow:

- Admin management
- Centre management
- Student admission
- Student approval
- Student login creation
- Course and batch management
- Fee collection and receipts
- Attendance
- Study material
- Admit cards
- Results and certificates
- Online exams, questions, imports, and student exam attempts
- Student dashboard and profile
- Centre dashboard and wallet/fee system

The software works with different login roles. Each role sees only the sections that are required for that user.

Main roles:

- Admin: Controls the full ERP system.
- Centre: Handles centre-level admissions, students, fees, and assigned data.
- Student: Views personal dashboard, fee records, exams, attendance, study material, results, certificates, and profile.

## 2. Login Flow

Every user logs in from the login page.

Login is based on username and password. For students, the username is normally the Enrollment No.

Student login flow:

1. Student admission is created by admin or centre.
2. Admission appears in Pending List.
3. Admin approves the admission.
4. Approved student appears in Approved List.
5. Admin creates the student password from Approved List.
6. Student logs in using Enrollment No and the password created by admin.

This keeps the student login connected to the admission record.

## 3. Admin ERP Section

The Admin ERP section is the main control area of the software. Admin can manage master data, students, centres, fees, exams, certificates, reports, and approvals.

### 3.1 Admin Dashboard

The Admin Dashboard shows the main summary of the system.

It includes information like:

- Total admissions
- Approved admissions
- Pending admissions
- Cancelled admissions
- Total centres
- Approved centres
- Fee collections
- Exams
- Students
- Quick actions

The dashboard is used as the starting point for admin work.

### 3.2 Course Area

The Course Area is used to create and manage courses.

Admin can manage:

- Course name
- Duration
- Course fee
- Course status
- Course details

Courses are important because student admission, fees, exams, batches, and study material are connected to courses.

### 3.3 Academics

Academics stores supporting academic data.

Common academic sections include:

- Session
- Timetable
- Occupation
- Subjects

This data helps maintain academic structure and can be used while creating student admissions, batches, and schedules.

### 3.4 Exam Centre and Exam Schedule

The Exam Centre section manages exam centre records.

The Exam Schedule section is used to create and manage exam timing and schedule-related data.

This helps organize exams properly for students and centres.

### 3.5 Student Information

Student Information is one of the most important sections in the admin ERP.

It includes:

- Student ID Card
- Student Details
- Student Admission
- Passout Student
- List Student(s)
- Pending List
- Approved List
- Cancel List

#### Student Admission Flow

1. Admin or centre fills the Student Admission Form.
2. Student details are saved in the system.
3. Admission is marked as Pending.
4. Admin checks the Pending List.
5. Admin approves or cancels the admission.
6. Once approved, the student moves to Approved List.

#### Approved List Flow

Approved List shows all approved students.

From this page admin can:

- View student details
- Move student back to Pending if needed
- Create student login password

Create Password flow:

1. Admin clicks Create Password for an approved student.
2. A password creation page opens.
3. Admin enters password and confirms it.
4. Password is saved for that student login.
5. Page shows the Enrollment No and created password so admin can note it.
6. Student can log in using Enrollment No and that password.

### 3.6 Student Profile

Student Profile shows the complete student account.

It contains:

- Student photo
- Student name
- Enrollment number
- Date of birth
- Gender
- Email
- Address
- Total fee
- Remaining fee
- Overview
- Fees Record
- Change Password
- Notifications

Admin can use the student profile to check the complete student record from one place.

### 3.7 Fees Collection

Fees Collection handles student fee payments.

Admin can:

- Collect fee
- Search fee payment
- View student fee records
- Add manual payment
- Edit payment
- Delete payment
- Generate receipt
- Print or export fee records

Fee data is connected to the student profile. When a payment is added, the paid amount and remaining fee are updated.

Fee record flow:

1. Open student profile or fee collection page.
2. Click Add Payment.
3. Enter payment date, amount, fee type, transaction ID, and payment information.
4. Save payment.
5. Payment appears in Fee Record table.
6. Receipt button shows the payment receipt with the same data.
7. Remaining fee updates according to total fee minus paid amount.

### 3.8 Attendance

Attendance is used to manage student attendance.

Admin or centre can:

- Mark attendance
- View attendance
- Track present and absent records

Attendance is connected with student admission records.

### 3.9 Admit Card

Admit Card section is used to create and manage admit cards for approved students.

Admin can:

- Create admit card
- View admit card list
- Print or manage admit card records

Only valid and approved student records should be used for admit cards.

### 3.10 Result

Result section manages student results.

Admin can:

- View result records
- Manage result-related data
- Connect results with student records and exams

### 3.11 Student Certificate

Student Certificate section is used to create and manage certificates.

Admin can:

- Issue certificates
- View certificate records
- Manage certificate data for students

Certificates are connected with student information and course completion.

### 3.12 Study Material

Study Material is used to upload and manage learning files for students.

Admin can:

- Upload material
- Assign material to courses or students
- Edit material
- Delete material

Students can view and download assigned study material from their student login.

### 3.13 Online Exam Section

The Online Exam Section manages exams and questions.

Admin can:

- Create exam
- View exam list
- Add questions
- Import questions from CSV
- Edit questions
- Delete questions
- Manage schedules
- Manage timers
- Publish or unpublish exams

Question flow:

1. Admin creates an exam.
2. Admin opens Questions for that exam.
3. Admin adds questions manually or imports questions by CSV.
4. Each question has options and a correct answer.
5. Student sees the exam in the student exam area if the exam is available.
6. Student attempts the exam.
7. Result is calculated and stored.

### 3.14 Assign Exam

Assign Exam is used to assign exams to students, courses, or batches depending on the system setup.

This controls which students can see and attempt an exam.

### 3.15 Student Exam(s)

Student Exam(s) shows student exam records and attempts.

Admin can review:

- Which student attempted which exam
- Exam status
- Result or score
- Attempt information

### 3.16 Center Area

Admin manages centres from Center Area.

It includes:

- Center Information
- Center Certificate
- Center Profile
- Center wallet and fee system

Admin can create centres, approve centres, view centre details, assign courses, and manage centre wallet balance.

### 3.17 Payment Area

Payment Area is used for payment settings and wallet/fee-related controls.

Admin can configure:

- Admission fees
- Centre wallet balance
- Fee system settings
- Payment records

This is connected with centre admission flow. If a centre creates a student admission and admission fee is enabled, the admission fee can be deducted from the centre wallet.

## 4. Student Section

The Student Section is the student-facing area of the software.

Student logs in using Enrollment No and password created by admin.

### 4.1 Student Dashboard

The Student Dashboard shows the student's personal summary.

It can show:

- Student profile information
- Enrollment number
- Course
- Date of birth
- Gender
- Total fee
- Remaining fee
- Fee record
- Attendance
- Exam area
- Study material
- Notifications

### 4.2 Profile

Student can view their profile details.

Profile includes:

- Name
- Email
- Mobile
- Address
- Course
- Centre
- Enrollment No
- Personal information

### 4.3 ID Card

Student can view their ID card if it is available in the system.

### 4.4 Attendance

Student can view attendance records.

This helps the student check present and absent status.

### 4.5 Admit Card

Student can view or download admit card if admin has created it.

### 4.6 Marksheet and Certificate

Student can view marksheet and certificate records if available.

### 4.7 Fee Record

Student can view fee records.

Student can see:

- Total course fee
- Paid amount
- Remaining fee
- Payment history
- Payment method
- Transaction number
- Receipt

Student should not edit or delete payments from student login. Student can only view fee information and receipt records.

### 4.8 Study Material

Student can view and download study material assigned to them or their course.

### 4.9 Exam Area

Student can see available exams.

Exam attempt flow:

1. Student opens Exam Area.
2. Student selects an available exam.
3. Student reads instructions.
4. Student starts exam.
5. Timer begins.
6. Student answers questions.
7. Student submits the exam.
8. Result is saved.
9. Student can view result or exam history.

### 4.10 Change Password

Student can change their own login password from the dashboard.

Password flow:

1. Student opens Change Password tab.
2. Student enters new password.
3. Student confirms new password.
4. System updates the password.
5. Student can use the new password on next login.

### 4.11 Notifications

Student can view notifications if any are assigned.

## 5. Centre Section

The Centre Section is used by centre users to manage centre-level work.

Centre login has limited access compared with admin. A centre user can manage only data connected to that centre.

### 5.1 Centre Dashboard

Centre Dashboard shows centre summary.

It can show:

- Centre profile
- Centre wallet balance
- Total admissions
- Approved admissions
- Pending admissions
- Cancelled admissions
- Fee collection
- Assigned courses
- Student count

### 5.2 Centre Profile

Centre Profile shows centre details.

It includes:

- Centre name
- Institute ID or centre code
- Address
- Email
- Contact details
- Registration date
- Valid upto date
- Status
- Wallet and fee system

### 5.3 Centre Wallet and Fee System

The centre wallet is used when admission fee settings are enabled.

Flow:

1. Admin loads funds into centre wallet.
2. Admin configures admission fee from fee system.
3. Centre creates student admission.
4. Admission fee is deducted from centre wallet if enabled.
5. Wallet balance is updated.

This ensures centre admissions are connected with the payment system.

### 5.4 Student Admission by Centre

Centre can fill student admission forms for students under that centre.

Centre admission flow:

1. Centre opens Student Admission.
2. Centre fills student information.
3. Centre selects course and required details.
4. Centre submits admission.
5. Admission goes to Pending List.
6. Admin approves admission.
7. Approved student appears in Approved List.
8. Admin creates student login password.

### 5.5 Centre Student Lists

Centre can view students connected to that centre.

Lists include:

- Pending students
- Approved students
- Cancelled students
- Student details

Centre should only see their own centre students.

### 5.6 Centre Fee Collection

Centre can collect and view fees for students connected to that centre depending on permission.

Fee collection connects with:

- Student profile
- Fee record
- Receipt
- Remaining fee calculation

### 5.7 Centre Study Material and Exams

Centre may access study material, exam-related sections, or assigned course data based on system permissions.

The centre should work only with assigned courses and students.

## 6. Complete Data Flow

The main software flow is:

1. Admin creates master data such as courses, subjects, sessions, and centres.
2. Admin configures fee settings and centre wallet if needed.
3. Admin or centre creates student admission.
4. Admission goes to Pending List.
5. Admin approves the admission.
6. Approved student appears in Approved List.
7. Admin creates student login password.
8. Student logs in with Enrollment No and password.
9. Admin or centre collects student fees.
10. Fee records and receipts are generated.
11. Attendance, study material, admit card, result, and certificates are managed.
12. Admin creates exams and questions.
13. Student attempts exams from student login.
14. Results and student records are updated.

## 7. How to Explain the Software to Users

Use this simple explanation:

"This software manages the full institute process from admission to exam and certificate. Admin controls all master data, students, centres, fees, exams, study material, attendance, results, and certificates. Centre users can manage their own centre admissions and related records. Students get their own dashboard where they can view profile, fee records, attendance, study material, exams, results, certificates, and notifications. Once a student admission is approved, admin creates a password for that student, and the student logs in using Enrollment No and that password."

## 8. Important Rules

- Admin has full control.
- Centre can access only centre-related data.
- Student can access only their own data.
- Student login is created after admission approval.
- Student username should be the Enrollment No.
- Fee payment should update paid amount and remaining balance.
- Receipt should show the same payment data that was entered.
- Exam questions should be added manually or imported before students attempt the exam.
- Data should not be deleted without confirmation.
- Passwords should be shared carefully with students.

## 9. Recommended Demo Flow

When explaining the software in a demo, follow this order:

1. Login as Admin.
2. Show Admin Dashboard.
3. Show Course Area.
4. Show Centre Area and wallet/fee system.
5. Show Student Admission form.
6. Submit a student admission.
7. Show Pending List.
8. Approve the student.
9. Show Approved List.
10. Create password for the approved student.
11. Open student profile and fee record.
12. Add a fee payment and show receipt.
13. Show exam list and question management.
14. Login as Student using Enrollment No and password.
15. Show student dashboard, fee record, attendance, study material, exams, and notifications.
16. Login as Centre and show centre dashboard, wallet, admissions, and centre student records.

## 10. Short Summary

This ERP connects Admin, Centre, and Student work in one system. Admin controls the complete setup and approval process. Centre manages centre-level admissions and records. Student uses the dashboard for personal records, exams, fees, study material, and certificates. The main workflow starts from admission, moves to approval, creates student login, manages fees, and finally supports exams, results, and certificates.
