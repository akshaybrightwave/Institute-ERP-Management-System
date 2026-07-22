# Online Examination Portal and ERP System Documentation

## 1. Project Overview

This project is a web-based Online Examination Portal with ERP features for an educational institute or training organization. It helps manage institute operations such as courses, centers, student admissions, fee collection, attendance, admit cards, results, certificates, study material, and online exams.

The system is built using Django and follows a role-based workflow. Different users can access different parts of the ERP according to their role.

Main purpose:

- Manage academic and administrative work in one system.
- Allow Admin to control all ERP data.
- Allow Center users to manage their assigned students and courses.
- Allow Students to view their own records, fees, exams, documents, and results.

## 2. Technology Stack

| Area | Technology |
|---|---|
| Backend | Python, Django |
| Database | MySQL |
| Frontend | HTML, CSS, Bootstrap 5, JavaScript |
| Template Engine | Django Templates |
| Authentication | Django Authentication with Custom User Model |
| File Uploads | Django Media Handling |
| Forms | Django Forms and ModelForms |

## 3. User Roles

### Admin

Admin has full ERP access. Admin can create and manage master data, students, centers, fees, exams, attendance, results, certificates, and study material.

Admin responsibilities:

- Manage courses and subjects.
- Manage centers.
- Assign courses to centers.
- Approve or cancel student admissions.
- Collect and manage student fees.
- Generate admit cards, ID cards, results, and certificates.
- Create and manage online exams.
- Assign exams to centers and students.
- View global reports and dashboard data.

### Center

Center user manages only the data related to their own center. A center cannot access another center's students or records.

Center responsibilities:

- Add or manage students under the center.
- View assigned courses.
- Collect fees for center students.
- Manage attendance for center students.
- Request exams from admin.
- View assigned exams.
- Manage center-level student records.

### Student

Student has limited self-service access. Student can only view their own information and documents.

Student access:

- Profile details.
- Fee record and receipts.
- Attendance.
- Admit card.
- Marksheet/result.
- Certificate.
- Study material.
- Assigned online exams.

## 4. Main ERP Modules

### 4.1 Dashboard

The dashboard shows summary cards according to user role.

Admin dashboard shows complete ERP data.

Center dashboard shows center-specific data.

Student dashboard shows student-specific data.

### 4.2 Course Management

Course management is used to create academic courses.

Course data includes:

- Course category.
- Course name.
- Duration.
- Course fee.

Example:

Course: BSc Computer Science  
Duration: 3 Years  
Fee: 45000

### 4.3 Subject Management

Subjects are connected with courses. Each subject belongs to a course and a selected course duration such as Year 1, Year 2, Semester 1, or Semester 2.

Subject data includes:

- Course.
- Duration/semester/year.
- Subject code.
- Subject name.
- Subject type.
- Theory marks.
- Practical marks.

### 4.4 Arrange Subjects

Arrange Subjects is used to set the order of subjects inside a course. This order can be useful when showing timetable, admit card subjects, or academic sequence.

Example:

1. Programming in C
2. Data Structures
3. Python

### 4.5 Center Management

Center Management stores institute center details.

Center data includes:

- Center name.
- Center code.
- Address.
- Phone.
- Email.
- Owner details.
- Validity date.
- Documents.
- Wallet balance.

### 4.6 Course Assignment to Center

Admin assigns courses to centers. After assignment, the center can work only with those assigned courses.

Flow:

Admin creates course  
Admin creates center  
Admin assigns course to center  
Center can use assigned course for students

### 4.7 Student Admission

Student admission is used to enter student details into the ERP.

Admission data includes:

- Student name.
- Enrollment number.
- Course.
- Center.
- Date of birth.
- Gender.
- Mobile number.
- Email.
- Address.
- Parent details.
- Documents.
- Admission status.

Admission statuses:

- Pending
- Approved
- Cancelled

### 4.8 Student Profile

After admission approval, the student profile becomes the main student account page.

Student profile shows:

- Personal details.
- Course details.
- Center details.
- Fee summary.
- Documents.
- Fee record.
- Notifications.

### 4.9 Fees Collection

Fees Collection manages student payments.

Fee calculation:

Total Course Fee = Course fee  
Paid Fee = Sum of all student payments  
Remaining Fee = Total Course Fee - Paid Fee

Fee payment data includes:

- Student.
- Amount.
- Payment date.
- Payment method.
- Reference number.
- Remarks.

Supported payment methods:

- Cash.
- UPI.
- Bank Transfer.

### 4.10 Fee Receipt

After payment collection, receipt can be generated. The receipt shows student details, payment details, amount paid, total fee, paid fee, and remaining balance.

Receipt is useful for:

- Student proof of payment.
- Admin record.
- Center record.
- Printing or downloading payment proof.

### 4.11 Attendance

Attendance module is used to mark and view student attendance.

Attendance data includes:

- Student.
- Date.
- Status.
- Marked by.

Status:

- Present.
- Absent.

### 4.12 Admit Card

Admit card is generated for students. It can include student details, course details, center details, and exam schedule information.

Admit card is useful before exams.

### 4.13 Result and Marksheet

Result module stores student marks and performance.

Marksheet shows:

- Student details.
- Course.
- Duration/year/semester.
- Marks obtained.
- Maximum marks.
- Result status.

### 4.14 Certificate

Certificate module is used after course completion. Certificate can be generated for eligible students.

Certificate usually depends on:

- Student course completion.
- Fees status.
- Attendance/result condition.

### 4.15 Study Material

Study Material module allows course-related material to be uploaded and shown to students.

Students can view study material related to their course.

### 4.16 Online Exam

Online Exam module manages MCQ-based exams.

Exam data includes:

- Exam title.
- Course.
- Duration.
- Start date/time.
- End date/time.
- Total questions.
- Pass percentage.
- Publish status.

Online exam flow:

Admin creates exam  
Admin adds questions  
Admin publishes exam  
Admin assigns exam to center/student  
Student attempts exam  
System calculates result

### 4.17 Exam Request

Center can request an exam from Admin.

Flow:

Center requests exam  
Admin reviews request  
Admin edits exam details if needed  
Admin approves/publishes exam  
Exam can be assigned to students

## 5. Complete ERP Data Flow

This is the main project flow:

```text
Admin Login
-> Create Course Category
-> Create Course
-> Create Subjects
-> Arrange Subjects
-> Create Center
-> Assign Course to Center
-> Add Student Admission
-> Approve Student
-> Student Profile Created
-> Collect Fee
-> Generate Fee Receipt
-> Mark Attendance
-> Generate Admit Card
-> Create Result/Marksheet
-> Generate Certificate
-> Upload Study Material
-> Create and Assign Online Exam
-> Student Attempts Exam
-> Student Views Result
```

## 6. Role-Based Data Flow

### Admin Flow

```text
Login as Admin
-> Dashboard
-> Manage master data
-> Manage centers
-> Manage students
-> Manage fees
-> Manage exams
-> Manage documents
-> View reports
```

### Center Flow

```text
Login as Center
-> Center Dashboard
-> View assigned courses
-> Add/manage center students
-> Collect student fees
-> Manage attendance
-> Request exam
-> View assigned exams
```

### Student Flow

```text
Login as Student
-> Student Dashboard
-> View profile
-> View fee record
-> Download receipt
-> View attendance
-> View admit card
-> View result/marksheet
-> View certificate
-> Access study material
-> Attempt assigned exams
```

## 7. Important Database Models

| Model | Purpose |
|---|---|
| User | Stores login user and role |
| Center | Stores center/institute branch details |
| CenterCourseAssignment | Connects centers with assigned courses |
| Course | Stores course name, duration, and fee |
| Subject | Stores subjects under a course |
| SubjectOrder | Stores subject display/order sequence |
| StudentAdmission | Stores admission form and approval status |
| StudentProfile | Stores approved student profile |
| FeePayment | Stores student fee payment records |
| Attendance | Stores attendance records |
| Exam | Stores online exam/request data |
| Question | Stores exam questions |
| Option | Stores MCQ options |
| StudentExamAttempt | Stores student exam attempt |
| StudentAnswer | Stores selected answers |
| ExamSchedule | Stores subject-wise exam schedule |
| ExamScheduleSubject | Stores subject date/time for schedule |

## 8. Authentication and Permission System

The project uses Django authentication with a custom user model.

Each user has a role. The role decides which pages and data the user can access.

Security rules:

- Admin can access complete ERP data.
- Center can access only center-related data.
- Student can access only own records.
- Unauthorized users are blocked.
- Deleted or inactive users cannot continue active sessions.

## 9. Demo Presentation Flow

For a professional demo, use this order:

1. Login as Admin.
2. Show Admin Dashboard.
3. Show Course Management.
4. Show Center Management.
5. Show Course Assignment to Center.
6. Show Student Admission.
7. Approve student.
8. Open Student Profile.
9. Add fee payment.
10. Show fee receipt.
11. Show attendance.
12. Show admit card.
13. Show result/marksheet.
14. Show certificate.
15. Show study material.
16. Show online exam creation and assignment.
17. Login as Student and show student output.
18. Login as Center and show center-limited data.

## 10. Local Setup Guide

Open terminal in the project root folder where `manage.py` exists.

Create virtual environment:

```powershell
python -m venv venv
```

Activate virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run migrations:

```powershell
python manage.py migrate
```

Run server:

```powershell
python manage.py runserver
```

Open in browser:

```text
http://127.0.0.1:8000/
```

## 11. Environment Configuration

The project can use `.env` file for environment-based settings.

Common values:

```text
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_NAME=online_exam_portal_db
DATABASE_USER=root
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=3306
```

For production, use secure values and set `DEBUG=False`.

## 12. Deployment Notes

Before public deployment, check:

- `DEBUG=False`
- Correct `ALLOWED_HOSTS`
- Correct `CSRF_TRUSTED_ORIGINS`
- Production database configured
- Static files collected
- Media files configured
- HTTPS enabled
- Secure cookies enabled
- Database migrations applied

Useful commands:

```powershell
python manage.py check
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic
```

## 13. Testing Checklist

Use this checklist before demo:

- Admin login works.
- Center login works.
- Student login works.
- Course create/edit/list works.
- Subject create/edit/list works.
- Center create/edit/list works.
- Course assignment works.
- Student admission works.
- Student approval works.
- Fee payment works.
- Fee receipt opens correctly.
- Attendance works.
- Admit card opens correctly.
- Result/marksheet opens correctly.
- Certificate opens correctly.
- Study material opens correctly.
- Exam create/edit works.
- Question add/edit works.
- Exam assignment works.
- Student can attempt assigned exam.
- Student result calculates correctly.

## 14. Future Enhancements

Possible future improvements:

- Payment gateway integration.
- SMS notifications.
- Email notifications.
- Advanced reports and analytics.
- Student mobile app.
- Parent portal.
- Bulk student import.
- Certificate QR verification.
- Online fee payment.
- Backup and restore system.

## 15. Conclusion

This ERP system provides a complete institute management workflow. It connects academic setup, center management, student admission, fees, attendance, documents, results, certificates, study material, and online exams in one role-based Django application.

The project is useful for educational institutes, coaching centers, training centers, and online examination businesses that need both ERP management and exam functionality in a single platform.
