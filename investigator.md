# Investigator Panel Phase Wise Guide

This document explains the Investigator Panel step by step. Complete one phase fully before starting the next phase.

## Main Purpose

Add an Investigator Panel inside the existing ERP system.

There will be two users involved:

- Admin
- Investigator

Admin will control and review all investigator data.

Investigator will enter investigation data through two forms.

## Final User Flow

1. Admin creates an Investigator user.
2. Investigator logs in.
3. Investigator opens Investigator Panel.
4. Investigator fills Recovery Report or Case Work Report.
5. Report is saved as Draft or Submitted.
6. Admin opens Investigator Panel.
7. Admin reviews submitted reports.
8. Admin approves or rejects reports.
9. Approved reports appear in final reports.
10. Admin exports student-wise, month-wise, or universal reports.

---

# Phase 1: Role and Permission Setup

Status: Completed

## Goal

Create a new role named Investigator.

## Admin Can See

- All investigators
- All recovery reports
- All case work reports
- All submitted, approved, rejected, and draft records
- Export buttons
- Approval and rejection options

## Investigator Can See

- Own dashboard
- Own recovery report form
- Own case work report form
- Own submitted reports
- Own draft and rejected reports

## Permission Rules

Admin:

- Can create Investigator users
- Can view all investigator data
- Can edit all records
- Can approve reports
- Can reject reports
- Can export all reports
- Can archive records

Investigator:

- Can add own reports
- Can view own reports
- Can edit only Draft or Rejected reports
- Cannot edit Approved reports
- Cannot see other investigators' data
- Cannot approve or reject reports
- Can export only own reports if export permission is allowed

## Phase 1 Completion Checklist

- Done: Investigator role is created.
- Done: Admin can create Investigator users.
- Done: Investigator can log in.
- Done: Investigator menu access is separate from other roles.
- Done: Admin can access Investigator Panel dashboard entry point.
- Done: Investigator can access only the Investigator Panel dashboard entry point for Phase 1.

Do not start Phase 2 until all above points are complete.

---

# Phase 2: Investigator Panel Menu Structure

Status: Completed

## Goal

Add Investigator Panel in the ERP sidebar/menu.

## Admin Menu

Admin should see:

- Investigator Dashboard
- Recovery Reports
- Case Work Reports
- Settings

Student-wise report, universal report, approval/review, and export/print should not be separate sidebar links in Phase 2. Keep them inside the correct pages later:

- Student-wise report: inside Recovery Reports or reporting area later
- Universal report: inside Recovery Reports or reporting area later
- Approval / Review: inside Settings or report detail later
- Export / Print: inside report pages later

## Investigator Menu

Investigator should see:

- My Dashboard
- Recovery Reports
- Case Work Reports

Add buttons should be inside the Recovery Reports and Case Work Reports pages, not separate sidebar links.

## Phase 2 Completion Checklist

- Done: Investigator Panel menu is visible to Admin.
- Done: Investigator Panel menu is visible to Investigator.
- Done: Admin menu has only Dashboard, Recovery Reports, Case Work Reports, and Settings.
- Done: Investigator menu has only Dashboard, Recovery Reports, and Case Work Reports.
- Done: Add buttons are kept inside report pages, not as separate sidebar links.
- Done: Unauthorized users cannot open Investigator Panel pages by URL.

Do not start Phase 3 until menu and permissions are correct.

---

# Phase 3: Master Data Setup

Status: Completed

## Goal

Create reusable dropdown data so spelling mistakes do not happen.

## Fraud Type Master

Admin should manage fraud types.

Default fraud types:

- Financial Fraud
- Mobile Fraud
- Mobile & Financial
- UPI Fraud
- Bank Fraud
- Job Fraud
- Investment Fraud
- Other

## Police Station Master

Admin should manage police stations.

Example police stations:

- Bhiwandi City Police Station
- Nijampura Police Station
- Narpoli Police Station
- Shantinagar Police Station

## Phase 3 Completion Checklist

- Done: Admin can add fraud type.
- Done: Admin can edit fraud type.
- Done: Admin can deactivate or activate fraud type.
- Done: Admin can add police station.
- Done: Admin can edit police station.
- Done: Admin can deactivate or activate police station.
- Pending for Phase 4: Recovery form uses fraud type dropdown.
- Pending for Phase 4: Recovery form uses police station dropdown.
- Pending for Phase 6: Case work form uses police station dropdown.

Do not start Phase 4 until dropdown master data is ready.

---

# Phase 4: Recovery Report Form

## Goal

Create the first form like the monthly recovery table.

## Form Fields

Required fields:

- Report number
- Report month
- Report year
- Entry date
- Student
- Police station
- Type of fraud
- Mobile recovery count
- Financial recovery amount
- Submitted by
- Submitted date
- Approval status
- Admin remarks
- Attachment upload

## Important Rules

- Report number should auto-generate.
- Example: INV-REC-2026-0001
- Student should be selected from existing student records if available.
- Mobile recovery should be a number.
- Financial recovery should be an amount.
- Total mobile recovery should calculate automatically.
- Total financial recovery should calculate automatically.
- Investigator should not type total manually.

## Approval Status

Use these statuses:

- Draft
- Submitted
- Approved
- Rejected

## Attachment Types

Allow useful proof files:

- PDF
- Image
- Excel
- Word document

## Phase 4 Completion Checklist

- Investigator can add recovery report.
- Investigator can save as Draft.
- Investigator can Submit report.
- Submitted by is stored automatically.
- Submitted date is stored automatically.
- Report number is generated automatically.
- Admin can view all recovery reports.
- Investigator can view only own recovery reports.
- Totals are calculated automatically.
- Attachment upload works.
- Admin can approve recovery report.
- Admin can reject recovery report with remarks.

Do not start Phase 5 until Recovery Report is fully working.

---

# Phase 5: Recovery Report Listing

## Goal

Create listing page for recovery reports.

## Admin Listing

Admin should see all recovery reports with:

- Report number
- Month/year
- Student name
- Investigator name
- Police station
- Fraud type
- Mobile recovery
- Financial recovery
- Approval status
- Submitted date
- Action buttons

## Investigator Listing

Investigator should see only own recovery reports with:

- Report number
- Month/year
- Student name
- Police station
- Fraud type
- Mobile recovery
- Financial recovery
- Approval status
- Submitted date
- Action buttons

## Filters

Add filters:

- Student name
- Investigator name
- Police station
- Fraud type
- Month
- Year
- Approval status

## Action Rules

Admin:

- View
- Edit
- Approve
- Reject
- Archive
- Export

Investigator:

- View
- Edit Draft reports
- Edit Rejected reports
- Submit Draft reports
- Export own reports if allowed

## Phase 5 Completion Checklist

- Admin listing shows all records.
- Investigator listing shows only own records.
- Filters work correctly.
- Edit rules work correctly.
- Approved reports cannot be edited by Investigator.
- Rejected reports show admin remarks.

Do not start Phase 6 until listing and filters are complete.

---

# Phase 6: Case Work Report Form

## Goal

Create the second form like the Thane City Cyber Cell Report.

## Main Form Fields

Required fields:

- Report number
- Name
- Case no
- Police station
- Investigating officer
- Case status
- Entry date
- Submitted by
- Submitted date
- Approval status
- Admin remarks
- Attachment upload

## Case Status

Use these statuses:

- Pending
- In Progress
- Completed
- Closed

## Work Description Fields

Inside one case report, allow multiple work description blocks.

Each block should have:

- Work title
- Work description

Example:

Work title:
GST Case Investigation

Work description:
Assisted in investigation, verified PAN number, collected bank details, analyzed bank accounts, and prepared findings.

Second work title:
CEIR Portal

Second work description:
Managed lost mobile complaints, complaint transfers, and missing mobile complaint filing.

## Important Rules

- User can click Add More Work.
- User can remove unsaved work blocks.
- At least one work block is required before submit.
- Each work block should keep its own title and description.
- Do not store all work descriptions in one large text field.

## Phase 6 Completion Checklist

- Investigator can add case work report.
- Investigator can add multiple work titles and descriptions.
- Investigator can save as Draft.
- Investigator can Submit report.
- Submitted by is stored automatically.
- Submitted date is stored automatically.
- Report number is generated automatically.
- Admin can view all case work reports.
- Investigator can view only own case work reports.
- Admin can approve case work report.
- Admin can reject case work report with remarks.

Do not start Phase 7 until Case Work Report is fully working.

---

# Phase 7: Case Work Report Listing

## Goal

Create listing page for case work reports.

## Admin Listing

Admin should see:

- Report number
- Name
- Case no
- Police station
- Investigating officer
- Case status
- Investigator name
- Approval status
- Submitted date
- Action buttons

## Investigator Listing

Investigator should see:

- Report number
- Name
- Case no
- Police station
- Investigating officer
- Case status
- Approval status
- Submitted date
- Action buttons

## Filters

Add filters:

- Name
- Case no
- Investigator name
- Police station
- Investigating officer
- Case status
- Approval status
- Month/year

## Phase 7 Completion Checklist

- Admin listing shows all case work reports.
- Investigator listing shows only own case work reports.
- Filters work correctly.
- Admin can view full case report.
- Investigator can view own full case report.
- Approved reports cannot be edited by Investigator.
- Rejected reports show admin remarks.

Do not start Phase 8 until listing and filters are complete.

---

# Phase 8: Dashboard

## Goal

Create small dashboard for Admin and Investigator.

## Admin Dashboard Cards

Admin should see:

- Total investigators
- Total recovery reports
- Total case work reports
- Total students involved
- Total mobile recovery
- Total financial recovery
- Pending approval count
- Approved report count
- Rejected report count

## Investigator Dashboard Cards

Investigator should see only own data:

- My recovery reports
- My case work reports
- My students/cases
- My mobile recovery total
- My financial recovery total
- My pending reports
- My approved reports
- My rejected reports

## Dashboard Filters

Add filters:

- Month
- Year
- Approval status

## Phase 8 Completion Checklist

- Admin dashboard counts all data.
- Investigator dashboard counts only own data.
- Mobile recovery total is correct.
- Financial recovery total is correct.
- Pending approval count is correct.
- Month/year filter works.

Do not start Phase 9 until dashboard numbers are correct.

---

# Phase 9: Student-wise Report

## Goal

Admin should see full investigation data for one student.

## Student-wise Report Should Show

- Student details
- Recovery reports for that student
- Case work reports linked to that student if available
- Mobile recovery total
- Financial recovery total
- Police station details
- Fraud types
- Approval status

## Filters

Add filters:

- Student
- Month
- Year
- Approval status

## Phase 9 Completion Checklist

- Admin can select student.
- Student recovery data appears correctly.
- Student case work data appears correctly if linked.
- Totals are correct.
- Export student-wise report works.

Do not start Phase 10 until student-wise report is complete.

---

# Phase 10: Universal Report

## Goal

Create one final report page where Admin can see all approved investigation data.

## Universal Report Should Show

- All approved recovery reports
- All approved case work reports
- Month-wise data
- Investigator-wise data
- Student-wise data
- Police-station-wise data
- Fraud-type-wise data

## Filters

Add filters:

- Month
- Year
- Investigator
- Student
- Police station
- Fraud type
- Case status

## Important Rule

By default, Universal Report should show only Approved data.

Admin can optionally filter Draft, Submitted, or Rejected data if needed.

## Phase 10 Completion Checklist

- Universal Report shows approved data by default.
- Filters work correctly.
- Month-wise report matches first image format.
- Case work report matches second image format.
- Totals are correct.

Do not start Phase 11 until universal report is accurate.

---

# Phase 11: Export and Print

## Goal

Add export buttons.

## Export Types

Recovery Report:

- Excel export
- PDF export
- Print

Case Work Report:

- PDF export
- Print

Student-wise Report:

- Excel export
- PDF export
- Print

Universal Report:

- Excel export
- PDF export
- Print

## Admin Export Permission

Admin can export:

- All data
- Student-wise data
- Month-wise data
- Investigator-wise data
- Police-station-wise data
- Universal report

## Investigator Export Permission

Investigator can export:

- Own recovery reports
- Own case work reports

Only allow this if required by business rule.

## Phase 11 Completion Checklist

- Recovery Excel export works.
- Recovery PDF export works.
- Case Work PDF export works.
- Student-wise export works.
- Universal export works.
- Export respects user permissions.
- Investigator cannot export other investigators' data.

Do not start Phase 12 until exports are working.

---

# Phase 12: Final Testing

## Goal

Test the full workflow from login to export.

## Test As Admin

Check:

- Admin can create Investigator.
- Admin can see Investigator Panel.
- Admin can see all records.
- Admin can approve report.
- Admin can reject report with remarks.
- Admin can export all reports.
- Admin dashboard totals are correct.

## Test As Investigator

Check:

- Investigator can log in.
- Investigator can see only own panel.
- Investigator can add Recovery Report.
- Investigator can add Case Work Report.
- Investigator can add multiple work descriptions.
- Investigator can submit report.
- Investigator can edit Draft reports.
- Investigator can edit Rejected reports.
- Investigator cannot edit Approved reports.
- Investigator cannot see other investigators' data.

## Final Completion Checklist

- Role permissions are correct.
- Forms are correct.
- Listings are correct.
- Dashboard is correct.
- Student-wise report is correct.
- Universal report is correct.
- Export is correct.
- Approval workflow is correct.
- Attachments work.
- No unauthorized data is visible.

---

# Recommended Database Tables

Use this only when implementation starts.

## investigator_recovery_reports

Suggested fields:

- id
- report_number
- report_month
- report_year
- entry_date
- student_id
- police_station_id
- fraud_type_id
- mobile_recovery_count
- financial_recovery_amount
- submitted_by_id
- submitted_at
- approval_status
- admin_remarks
- attachment
- is_archived
- created_at
- updated_at

## investigator_case_reports

Suggested fields:

- id
- report_number
- name
- case_no
- police_station_id
- investigating_officer
- case_status
- entry_date
- submitted_by_id
- submitted_at
- approval_status
- admin_remarks
- attachment
- is_archived
- created_at
- updated_at

## investigator_case_work_items

Suggested fields:

- id
- case_report_id
- work_title
- work_description
- sort_order
- created_at
- updated_at

## investigator_fraud_types

Suggested fields:

- id
- name
- is_active
- created_at
- updated_at

## investigator_police_stations

Suggested fields:

- id
- name
- is_active
- created_at
- updated_at

---

# Strict Rule For Development

Do not build everything together.

Follow this order:

1. Role
2. Menu
3. Master data
4. Recovery form
5. Recovery listing
6. Case work form
7. Case work listing
8. Dashboard
9. Student-wise report
10. Universal report
11. Export
12. Final testing

After each phase, test and confirm. Then start the next phase.
