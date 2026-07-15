from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.management.models import Inquiry, Lead, CallLog, FollowUp, CounselingSession, VisitSheet, InquiryCallStatusHistory
import datetime

User = get_user_model()

class TelecallerModuleTests(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(username='admin_user', password='password', role='admin')
        self.tele1 = User.objects.create_user(username='tele1', password='password', role='telecaller')
        self.tele2 = User.objects.create_user(username='tele2', password='password', role='telecaller')
        self.student = User.objects.create_user(username='student_user', password='password', role='student')

        # Create clients
        self.client_admin = Client()
        self.client_tele1 = Client()
        self.client_tele2 = Client()
        self.client_student = Client()

        # Log in
        self.client_admin.login(username='admin_user', password='password')
        self.client_tele1.login(username='tele1', password='password')
        self.client_tele2.login(username='tele2', password='password')
        self.client_student.login(username='student_user', password='password')

        # Create inquiry for tele1
        self.inquiry1 = Inquiry.objects.create(
            full_name='John Doe',
            mobile_number='1234567890',
            email='john@example.com',
            city='Thane',
            course_interest='Java',
            source='Website',
            status='New',
            created_by=self.tele1
        )

        # Create inquiry for tele2
        self.inquiry2 = Inquiry.objects.create(
            full_name='Jane Smith',
            mobile_number='0987654321',
            email='jane@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Walk-In',
            status='New',
            created_by=self.tele2
        )

    def test_portal_access_restrictions(self):
        # Student should be blocked from management dashboard and admin dashboard
        response = self.client_student.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 403)
        response = self.client_student.get(reverse('management_super_admin_dashboard'))
        self.assertEqual(response.status_code, 403)

        # Telecaller should be blocked from ERP center list
        response = self.client_tele1.get(reverse('center_list'))
        self.assertEqual(response.status_code, 403)

        # Admin accessing management_dashboard should be redirected to management_super_admin_dashboard
        response = self.client_admin.get(reverse('management_dashboard'))
        self.assertRedirects(response, reverse('management_super_admin_dashboard'))

        # Admin can access admin dashboard
        response = self.client_admin.get(reverse('management_super_admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Telecaller can access management dashboard
        response = self.client_tele1.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Telecaller accessing admin dashboard should be redirected to management dashboard
        response = self.client_tele1.get(reverse('management_super_admin_dashboard'))
        self.assertRedirects(response, reverse('management_dashboard'))

    def test_inquiry_data_isolation(self):
        # Tele1 should see inquiry1 but not inquiry2
        response = self.client_tele1.get(reverse('inquiry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')

        # Tele2 should see inquiry2 but not inquiry1
        response = self.client_tele2.get(reverse('inquiry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Smith')
        self.assertNotContains(response, 'John Doe')

        # Admin should see both
        response = self.client_admin.get(reverse('inquiry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')

    def test_inquiry_directory_date_filter_matches_local_day(self):
        tz = timezone.get_current_timezone()
        selected_date = datetime.date(2026, 6, 25)
        other_date = datetime.date(2026, 6, 24)
        Inquiry.objects.filter(pk=self.inquiry1.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time(10, 30)), tz)
        )
        Inquiry.objects.filter(pk=self.inquiry2.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(other_date, datetime.time(16, 45)), tz)
        )

        response = self.client_admin.get(reverse('inquiry_list'), {'date': '2026-06-25'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')

    def test_inquiry_directory_date_filter_accepts_display_format(self):
        tz = timezone.get_current_timezone()
        selected_date = datetime.date(2026, 6, 25)
        other_date = datetime.date(2026, 6, 24)
        Inquiry.objects.filter(pk=self.inquiry1.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time(10, 30)), tz)
        )
        Inquiry.objects.filter(pk=self.inquiry2.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(other_date, datetime.time(16, 45)), tz)
        )

        response = self.client_admin.get(reverse('inquiry_list'), {'date': '25-06-2026'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')
        self.assertContains(response, 'value="2026-06-25"')

    def test_assigned_lead_inquiry_shows_in_telecaller_directory(self):
        Lead.objects.create(
            inquiry=self.inquiry2,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )

        response = self.client_tele1.get(reverse('inquiry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')

        response = self.client_tele1.get(reverse('inquiry_detail', kwargs={'pk': self.inquiry2.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Smith')

    def test_unauthorized_record_details_access(self):
        # Tele1 tries to view details of tele2's inquiry
        response = self.client_tele1.get(reverse('inquiry_detail', kwargs={'pk': self.inquiry2.pk}))
        self.assertEqual(response.status_code, 403)

        # Tele1 tries to edit tele2's inquiry
        response = self.client_tele1.get(reverse('inquiry_edit', kwargs={'pk': self.inquiry2.pk}))
        self.assertEqual(response.status_code, 403)

    def test_inquiry_to_lead_conversion_workflow(self):
        counselor = User.objects.create_user(username='counselor_user', password='password', role='counselor')

        # Convert inquiry1 to lead
        response = self.client_tele1.post(
            reverse('inquiry_convert', kwargs={'pk': self.inquiry1.pk}),
            {'assigned_counselor': counselor.pk}
        )
        self.assertEqual(response.status_code, 302) # Redirect to lead detail

        # Verify Lead creation
        lead = Lead.objects.get(inquiry=self.inquiry1)
        self.assertEqual(lead.assigned_telecaller, self.tele1)
        self.assertEqual(lead.assigned_counselor, counselor)
        self.assertEqual(lead.status, 'New')

        # Verify Inquiry status auto updated to Qualified
        self.inquiry1.refresh_from_db()
        self.assertEqual(self.inquiry1.status, 'Qualified')

        # Prevent duplicate conversion
        response = self.client_tele1.post(reverse('inquiry_convert', kwargs={'pk': self.inquiry1.pk}))
        self.assertEqual(response.status_code, 302)

    def test_telecaller_added_inquiry_remains_convertible(self):
        response = self.client_tele1.post(reverse('inquiry_add'), {
            'full_name': 'Fresh Tele Inquiry',
            'mobile_number': '7777777777',
            'email': 'fresh.tele@example.com',
            'city': 'Mumbai',
            'course_interest': 'Python',
            'source': 'Website',
            'remarks': 'Needs follow up',
            'status': 'New',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        inquiry = Inquiry.objects.get(full_name='Fresh Tele Inquiry')
        self.assertFalse(Lead.objects.filter(inquiry=inquiry).exists())
        self.assertContains(response, 'Fresh Tele Inquiry')
        self.assertContains(response, 'Convert to Lead')

    def test_admin_added_inquiry_still_creates_lead(self):
        response = self.client_admin.post(reverse('inquiry_add'), {
            'full_name': 'Fresh Admin Inquiry',
            'mobile_number': '7777777778',
            'email': 'fresh.admin@example.com',
            'city': 'Thane',
            'course_interest': 'Java',
            'source': 'Website',
            'remarks': 'Admin entry',
            'status': 'New',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        inquiry = Inquiry.objects.get(full_name='Fresh Admin Inquiry')
        self.assertTrue(Lead.objects.filter(inquiry=inquiry, assigned_by=self.admin).exists())

    def test_csv_import_workflow(self):
        # Create in-memory CSV file
        from io import BytesIO
        csv_data = "full_name,mobile_number,email,city,course_interest,source,remarks\n" \
                   "Bob CSV,9876500001,bob@csv.com,Thane,Java,Website,CSV remark\n" \
                   "Duplicate Name,1234567890,dup@csv.com,Mumbai,Python,Other,Duplicate mobile\n" \
                   "Invalid Row,,empty@csv.com,Pune,Java,Other,\n" \
                   "Bad Mobile,Too Short,invalid@csv.com,Pune,Java,Other,"
        csv_file = BytesIO(csv_data.encode('utf-8'))
        csv_file.name = 'test.csv'

        # Import using telecaller 1 client
        response = self.client_tele1.post(reverse('inquiry_import'), {'file': csv_file})
        self.assertEqual(response.status_code, 302) # Redirect to history
        
        # Verify LeadImport log
        from apps.management.models import LeadImport
        imports = LeadImport.objects.filter(uploaded_by=self.tele1)
        self.assertEqual(imports.count(), 1)
        imp = imports.first()
        self.assertEqual(imp.total_records, 4)
        self.assertEqual(imp.successful_records, 1) # Only Bob CSV is successfully imported
        self.assertEqual(imp.duplicate_records, 1)  # Duplicate mobile (matching John Doe's 1234567890)
        self.assertEqual(imp.failed_records, 2)     # Invalid Row and Bad Mobile

        # Verify Bob CSV is in database
        self.assertTrue(Inquiry.objects.filter(full_name='Bob CSV', created_by=self.tele1).exists())

    def test_xlsx_import_workflow(self):
        import openpyxl
        from io import BytesIO
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'remarks'])
        ws.append(['Alice Excel', '9876500002', 'alice@excel.com', 'Pune', 'Python', 'Website', 'Excel test remark'])
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        excel_file.name = 'test.xlsx'

        response = self.client_tele1.post(reverse('inquiry_import'), {'file': excel_file})
        self.assertEqual(response.status_code, 302)

        # Verify LeadImport log
        from apps.management.models import LeadImport
        imports = LeadImport.objects.filter(uploaded_by=self.tele1)
        self.assertEqual(imports.count(), 1)
        self.assertEqual(imports.first().successful_records, 1)

        # Verify Alice is in database
        self.assertTrue(Inquiry.objects.filter(full_name='Alice Excel', created_by=self.tele1).exists())

    def test_invalid_file_rejection(self):
        from io import BytesIO
        bad_file = BytesIO(b"dummy doc content")
        bad_file.name = 'report.pdf'

        response = self.client_tele1.post(reverse('inquiry_import'), {'file': bad_file})
        self.assertEqual(response.status_code, 200) # Form re-rendered
        self.assertContains(response, "Only CSV and Excel files are allowed.")

    def test_lead_status_choices(self):
        # Create a lead to update
        lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')
        
        # Edit lead with new status choices
        for status in ['Rejected', 'Invalid Number']:
            lead.status = status
            lead.save()
            lead.refresh_from_db()
            self.assertEqual(lead.status, status)

    def test_telecaller_call_status_choices_exclude_new_and_accepted(self):
        response = self.client_tele1.get(reverse('inquiry_list'))

        self.assertEqual(response.status_code, 200)
        choice_values = [code for code, _ in response.context['call_status_choices']]
        self.assertNotIn('NEW', choice_values)
        self.assertNotIn('ACCEPTED', choice_values)
        self.assertIn('BUSY', choice_values)
        self.assertIn('PENDING_FOLLOW_UP', choice_values)

    def test_telecaller_cannot_submit_removed_call_statuses(self):
        for removed_status in ('NEW', 'ACCEPTED'):
            response = self.client_tele1.post(
                reverse('update_call_status', kwargs={'pk': self.inquiry1.pk}),
                data=f'{{"call_status":"{removed_status}"}}',
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 400)

        response = self.client_tele1.post(
            reverse('update_call_status', kwargs={'pk': self.inquiry1.pk}),
            data='{"call_status":"BUSY"}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.inquiry1.refresh_from_db()
        self.assertEqual(self.inquiry1.call_status, 'BUSY')

    def test_repeated_call_status_updates_create_history_with_remarks(self):
        for remark in ('First ringing call', 'Second ringing call'):
            response = self.client_tele1.post(
                reverse('update_call_status', kwargs={'pk': self.inquiry1.pk}),
                data=f'{{"call_status":"NO_ANSWER","remarks":"{remark}"}}',
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)

        self.inquiry1.refresh_from_db()
        history = InquiryCallStatusHistory.objects.filter(inquiry=self.inquiry1).order_by('created_at', 'id')

        self.assertEqual(self.inquiry1.call_status, 'NO_ANSWER')
        self.assertEqual(history.count(), 2)
        self.assertEqual([item.call_status for item in history], ['NO_ANSWER', 'NO_ANSWER'])
        self.assertEqual([item.remarks for item in history], ['First ringing call', 'Second ringing call'])

    def test_telecaller_dashboard_cards_match_scoped_lists(self):
        Lead.objects.create(
            inquiry=self.inquiry1,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )
        self.inquiry1.call_status = 'BUSY'
        self.inquiry1.save(update_fields=['call_status'])

        converted_lead = Lead.objects.create(
            inquiry=self.inquiry2,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New',
            converted_at=timezone.now()
        )
        self.inquiry2.status = 'Qualified'
        self.inquiry2.call_status = 'INTERESTED'
        self.inquiry2.save(update_fields=['status', 'call_status'])

        dashboard = self.client_tele1.get(reverse('management_dashboard'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['call_outcomes']['busy'], 1)
        self.assertEqual(dashboard.context['qualified_leads']['total'], 1)

        busy_list = self.client_tele1.get(reverse('inquiry_list'), {
            'scope': 'active_contacts',
            'call_status': 'BUSY',
        })
        self.assertEqual(busy_list.status_code, 200)
        busy_ids = {inquiry.pk for inquiry in busy_list.context['page_obj'].object_list}
        self.assertIn(self.inquiry1.pk, busy_ids)
        self.assertNotIn(self.inquiry2.pk, busy_ids)

        converted_list = self.client_tele1.get(reverse('inquiry_list'), {
            'scope': 'converted_leads',
            'status': 'Qualified',
        })
        self.assertEqual(converted_list.status_code, 200)
        converted_ids = {inquiry.lead.pk for inquiry in converted_list.context['page_obj'].object_list}
        self.assertIn(converted_lead.pk, converted_ids)

    def test_telecaller_grouped_call_status_cards_and_filter(self):
        Lead.objects.create(
            inquiry=self.inquiry1,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )
        self.inquiry1.call_status = 'BUSY'
        self.inquiry1.save(update_fields=['call_status'])

        ringing_contact = Inquiry.objects.create(
            full_name='Ringing Tele Contact',
            mobile_number='9991110001',
            email='ringing.tele@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='NO_ANSWER',
            created_by=self.admin
        )
        other_contact = Inquiry.objects.create(
            full_name='Other Tele Contact',
            mobile_number='9991110002',
            email='other.tele@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='OTHER',
            created_by=self.admin
        )
        for inquiry in (ringing_contact, other_contact):
            Lead.objects.create(
                inquiry=inquiry,
                assigned_telecaller=self.tele1,
                assigned_by=self.admin,
                status='New'
            )

        dashboard = self.client_tele1.get(reverse('management_dashboard'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['call_outcomes']['busy_callback_not_connected'], 2)
        self.assertEqual(dashboard.context['call_outcomes']['other'], 1)

        response = self.client_tele1.get(reverse('inquiry_list'), {
            'queue': 'active',
            'call_status_group': 'busy_callback_not_connected',
        })
        self.assertEqual(response.status_code, 200)
        inquiry_ids = {inquiry.pk for inquiry in response.context['page_obj'].object_list}
        self.assertIn(self.inquiry1.pk, inquiry_ids)
        self.assertIn(ringing_contact.pk, inquiry_ids)
        self.assertNotIn(other_contact.pk, inquiry_ids)
        self.assertEqual(response.context['call_status_group'], 'busy_callback_not_connected')
        self.assertIn(('BUSY', 'Busy / Call Back / Not Connected'), response.context['call_status_update_choices'])

    def test_telecaller_exports_use_current_grouped_statuses(self):
        Lead.objects.create(
            inquiry=self.inquiry1,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )
        self.inquiry1.call_status = 'INVALID_NUMBER'
        self.inquiry1.save(update_fields=['call_status'])
        message_contact = Inquiry.objects.create(
            full_name='Message Call Back Contact',
            mobile_number='7777777777',
            email='message.callback@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='CALL_BACK',
            created_by=self.admin
        )
        Lead.objects.create(
            inquiry=message_contact,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )

        export_response = self.client_tele1.get(reverse('export_telecaller_dashboard_csv'), {
            'date_filter': 'all',
        })
        self.assertEqual(export_response.status_code, 200)
        export_csv = export_response.content.decode()
        self.assertIn('John Doe', export_csv)
        self.assertIn('1234567890', export_csv)
        self.assertIn('Switch Off / Wrong No. / Invalid No.', export_csv)
        self.assertNotIn('Pending Follow Up', export_csv)

        message_response = self.client_tele1.get(reverse('export_telecaller_message_numbers_csv'), {
            'date_filter': 'all',
        })
        self.assertEqual(message_response.status_code, 200)
        message_csv = message_response.content.decode()
        self.assertIn('current_status', message_csv)
        self.assertIn('Message Call Back Contact', message_csv)
        self.assertIn('7777777777', message_csv)
        self.assertIn('Busy / Call Back / Not Connected', message_csv)
        self.assertNotIn('John Doe', message_csv)
        self.assertNotIn('1234567890', message_csv)
        self.assertNotIn('Switch Off / Wrong No. / Invalid No.', message_csv)

    def test_lead_notes_timeline(self):
        # Create a lead
        lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')

        # Add notes
        self.client_tele1.post(reverse('lead_note_add', kwargs={'pk': lead.pk}), {'note': 'Call #1: Left voicemail'})
        self.client_tele1.post(reverse('lead_note_add', kwargs={'pk': lead.pk}), {'note': 'Call #2: Scheduled meeting'})

        # Verify notes timeline ordering (chronological - oldest first)
        response = self.client_tele1.get(reverse('lead_notes_list', kwargs={'pk': lead.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Call #1: Left voicemail')
        self.assertContains(response, 'Call #2: Scheduled meeting')

        from apps.management.models import LeadNote
        notes = LeadNote.objects.filter(lead=lead).order_by('created_at')
        self.assertEqual(notes.count(), 2)
        self.assertEqual(notes[0].note, 'Call #1: Left voicemail')
        self.assertEqual(notes[1].note, 'Call #2: Scheduled meeting')

    def test_followup_overdue_and_dashboard(self):
        lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')
        
        # Create overdue followup (yesterday)
        from apps.management.models import FollowUp
        overdue_date = datetime.date.today() - datetime.timedelta(days=2)
        followup = FollowUp.objects.create(
            lead=lead,
            followup_date=overdue_date,
            status='Pending',
            created_by=self.tele1
        )

        self.assertTrue(followup.is_overdue)
        self.assertEqual(followup.days_overdue, 2)
        self.assertFalse(followup.reminder_sent)

        # Check telecaller dashboard displays metrics correctly
        response = self.client_tele1.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overdue Follow-ups")
        self.assertContains(response, "⚠ Overdue Follow-Up")

    def test_flexible_column_mapping_import(self):
        from io import BytesIO
        # Example header mapping: Name, Phone, Email, Company, City
        csv_data = "Name,Phone,Email,Company,City\n" \
                   "Rahul Sharma,9876543210,rahul.sharma@example.com,TechSoft,Thane\n" \
                   "Priya Patel,9123456780,priya.patel@example.com,InnoTech,Mumbai\n"
        csv_file = BytesIO(csv_data.encode('utf-8'))
        csv_file.name = 'flexible_test.csv'

        response = self.client_tele1.post(reverse('inquiry_import'), {'file': csv_file})
        self.assertEqual(response.status_code, 302)

        # Verify LeadImport log
        from apps.management.models import LeadImport
        imports = LeadImport.objects.filter(uploaded_by=self.tele1)
        self.assertTrue(imports.exists())
        imp = imports.first()
        self.assertEqual(imp.total_records, 2)
        self.assertEqual(imp.successful_records, 2)
        self.assertEqual(imp.failed_records, 0)
        self.assertEqual(imp.duplicate_records, 0)

        # Verify Rahul Sharma and Priya Patel are in the database
        self.assertTrue(Inquiry.objects.filter(full_name='Rahul Sharma', mobile_number='9876543210', city='Thane').exists())
        self.assertTrue(Inquiry.objects.filter(full_name='Priya Patel', mobile_number='9123456780', city='Mumbai').exists())

    def test_sample_downloads(self):
        # Test download sample CSV
        response = self.client_tele1.get(reverse('download_sample_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="sample_inquiries.csv"', response['Content-Disposition'])

        # Test download sample Excel
        response = self.client_tele1.get(reverse('download_sample_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename="sample_inquiries.xlsx"', response['Content-Disposition'])

    def test_activity_timeline_and_isolation(self):
        # 1. Lead creation logs activity
        response = self.client_tele1.post(reverse('inquiry_convert', kwargs={'pk': self.inquiry1.pk}))
        self.assertEqual(response.status_code, 302)
        lead = Lead.objects.get(inquiry=self.inquiry1)
        
        # Verify LEAD_CREATED & ASSIGNED activities
        self.assertEqual(lead.activities.filter(activity_type='LEAD_CREATED').count(), 1)
        self.assertEqual(lead.activities.filter(activity_type='ASSIGNED').count(), 1)

        # 2. Lead note added logs activity
        self.client_tele1.post(reverse('lead_note_add', kwargs={'pk': lead.pk}), {'note': 'Meeting scheduled'})
        self.assertEqual(lead.activities.filter(activity_type='NOTE_ADDED').count(), 1)

        # 3. Call log added logs activity
        self.client_tele1.post(reverse('call_log_add'), {
            'lead': lead.pk,
            'call_duration': 30,
            'call_status': 'Connected',
            'remarks': 'Log test'
        })
        self.assertEqual(lead.activities.filter(activity_type='CALL_LOG_ADDED').count(), 1)

        # 4. Follow up created and completed logs activities
        self.client_tele1.post(reverse('followup_add'), {
            'lead': lead.pk,
            'followup_date': (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'status': 'Pending',
            'response': 'Followup scheduled'
        })
        self.assertEqual(lead.activities.filter(activity_type='FOLLOWUP_CREATED').count(), 1)
        
        followup = FollowUp.objects.filter(lead=lead).first()
        self.client_tele1.post(reverse('followup_complete', kwargs={'pk': followup.pk}))
        self.assertEqual(lead.activities.filter(activity_type='FOLLOWUP_COMPLETED').count(), 1)

        # 5. Verify activity feed view and isolation
        response = self.client_tele1.get(reverse('activities_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lead created from inquiry conversion')

        response = self.client_tele2.get(reverse('activities_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Lead created from inquiry conversion')

    def test_import_error_logging_and_csv_export(self):
        from io import BytesIO
        # Uploading file with validation issues (Missing Name, Missing Mobile, Duplicate, Invalid Email)
        csv_data = "Name,Phone,Email,Company,City\n" \
                   ",9876599999,test@example.com,,Mumbai\n" \
                   "John Doe,1234567890,john@example.com,,Thane\n" \
                   "Priya Patel,TooShort,priya@example.com,,Pune\n" \
                   "Alice Key,9876543211,bad_email,,Pune\n"
        csv_file = BytesIO(csv_data.encode('utf-8'))
        csv_file.name = 'errors_test.csv'

        response = self.client_tele1.post(reverse('inquiry_import'), {'file': csv_file})
        self.assertEqual(response.status_code, 302)

        from apps.management.models import LeadImport, ImportErrorLog
        imp = LeadImport.objects.filter(uploaded_by=self.tele1).first()
        self.assertEqual(imp.failed_records, 3) 
        self.assertEqual(imp.duplicate_records, 1) 
        self.assertEqual(imp.successful_records, 0)

        errors = ImportErrorLog.objects.filter(lead_import=imp)
        self.assertEqual(errors.count(), 4)
        
        self.assertTrue(errors.filter(error_message="Missing Full Name").exists())
        self.assertTrue(errors.filter(error_message="Duplicate Mobile Number").exists())
        self.assertTrue(errors.filter(error_message="Invalid Mobile Number").exists())
        self.assertTrue(errors.filter(error_message="Invalid Email").exists())

        response = self.client_tele1.get(reverse('import_errors'), {'import_id': imp.id, 'export': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, "Missing Full Name")
        self.assertContains(response, "Duplicate Mobile Number")

    def test_admin_can_delete_import_history_record(self):
        from apps.management.models import LeadImport, ImportErrorLog
        lead_import = LeadImport.objects.create(
            uploaded_by=self.tele1,
            file='lead_imports/delete_test.csv',
            total_records=1,
            failed_records=1
        )
        error = ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=2,
            error_message='Invalid Mobile Number'
        )

        response = self.client_admin.post(reverse('import_history_delete', kwargs={'pk': lead_import.pk}))
        self.assertRedirects(response, reverse('import_history'))
        self.assertFalse(LeadImport.objects.filter(pk=lead_import.pk).exists())
        self.assertFalse(ImportErrorLog.objects.filter(pk=error.pk).exists())

    def test_admin_import_pages_show_delete_controls(self):
        from apps.management.models import LeadImport, ImportErrorLog
        lead_import = LeadImport.objects.create(uploaded_by=self.tele1, file='lead_imports/render_test.csv')
        ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=2,
            error_message='Invalid Mobile Number'
        )

        response = self.client_admin.get(reverse('import_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Selected')
        self.assertContains(response, reverse('import_history_delete', kwargs={'pk': lead_import.pk}))

        response = self.client_admin.get(reverse('import_errors'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Selected')
        self.assertContains(response, 'bulkImportErrorDeleteForm')

    def test_admin_can_bulk_delete_import_history_records(self):
        from apps.management.models import LeadImport
        import_one = LeadImport.objects.create(uploaded_by=self.tele1, file='lead_imports/one.csv')
        import_two = LeadImport.objects.create(uploaded_by=self.tele2, file='lead_imports/two.csv')

        response = self.client_admin.post(reverse('import_history_bulk_delete'), {
            'imports': [import_one.pk, import_two.pk],
        })

        self.assertRedirects(response, reverse('import_history'))
        self.assertFalse(LeadImport.objects.filter(pk__in=[import_one.pk, import_two.pk]).exists())

    def test_admin_can_delete_import_error_record(self):
        from apps.management.models import LeadImport, ImportErrorLog
        lead_import = LeadImport.objects.create(uploaded_by=self.tele1, file='lead_imports/error_delete.csv')
        error = ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=3,
            error_message='Missing Full Name'
        )

        response = self.client_admin.post(reverse('import_error_delete', kwargs={'pk': error.pk}))
        self.assertRedirects(response, reverse('import_errors'))
        self.assertFalse(ImportErrorLog.objects.filter(pk=error.pk).exists())
        self.assertTrue(LeadImport.objects.filter(pk=lead_import.pk).exists())

    def test_admin_can_bulk_delete_import_error_records(self):
        from apps.management.models import LeadImport, ImportErrorLog
        lead_import = LeadImport.objects.create(uploaded_by=self.tele1, file='lead_imports/error_bulk.csv')
        error_one = ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=3,
            error_message='Missing Full Name'
        )
        error_two = ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=4,
            error_message='Invalid Email'
        )

        response = self.client_admin.post(reverse('import_error_bulk_delete'), {
            'errors': [error_one.pk, error_two.pk],
        })

        self.assertRedirects(response, reverse('import_errors'))
        self.assertFalse(ImportErrorLog.objects.filter(pk__in=[error_one.pk, error_two.pk]).exists())

    def test_telecaller_cannot_delete_import_records(self):
        from apps.management.models import LeadImport, ImportErrorLog
        lead_import = LeadImport.objects.create(uploaded_by=self.tele1, file='lead_imports/protected.csv')
        error = ImportErrorLog.objects.create(
            lead_import=lead_import,
            row_number=5,
            error_message='Protected'
        )

        response = self.client_tele1.post(reverse('import_history_delete', kwargs={'pk': lead_import.pk}))
        self.assertEqual(response.status_code, 403)
        response = self.client_tele1.post(reverse('import_error_delete', kwargs={'pk': error.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LeadImport.objects.filter(pk=lead_import.pk).exists())
        self.assertTrue(ImportErrorLog.objects.filter(pk=error.pk).exists())

    def test_lead_assignment_management(self):
        owned_lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')

        # 1. Telecaller tries to reassign - forbidden
        response = self.client_tele1.post(reverse('lead_assign'), {'lead_id': owned_lead.pk, 'telecaller': self.tele2.pk})
        self.assertEqual(response.status_code, 403)

        admin_uploaded_inquiry = Inquiry.objects.create(
            full_name='Admin Uploaded Contact',
            mobile_number='7777777777',
            email='admin-uploaded@example.com',
            city='Nashik',
            course_interest='Python',
            source='Website',
            status='New',
            created_by=self.admin
        )
        lead = Lead.objects.create(
            inquiry=admin_uploaded_inquiry,
            assigned_by=self.admin,
            status='New'
        )

        # 2. Admin assigns a fresh admin-uploaded contact to telecaller 2
        response = self.client_admin.post(reverse('lead_assign'), {'leads': [lead.pk], 'telecaller': self.tele2.pk})
        self.assertEqual(response.status_code, 302)

        lead.refresh_from_db()
        self.assertEqual(lead.assigned_telecaller, self.tele2)
        self.assertEqual(lead.assigned_by, self.admin)
        self.assertIsNotNone(lead.assigned_at)
        
        self.assertTrue(lead.activities.filter(activity_type='ASSIGNED', description__icontains="assigned to tele2 by admin").exists())

    def test_telecaller_assignment_filters_show_admin_uploaded_lifecycle_contacts(self):
        admin_uploaded_inquiry = Inquiry.objects.create(
            full_name='Fresh Admin Upload',
            mobile_number='7777777778',
            email='fresh-admin@example.com',
            city='Thane',
            course_interest='Python',
            source='Website',
            status='New',
            created_by=self.admin
        )
        queue_lead = Lead.objects.create(
            inquiry=admin_uploaded_inquiry,
            assigned_by=self.admin,
            status='New'
        )

        assigned_admin_inquiry = Inquiry.objects.create(
            full_name='Already Assigned Admin Upload',
            mobile_number='7777777779',
            email='assigned-admin@example.com',
            city='Mumbai',
            course_interest='Java',
            source='Referral',
            status='New',
            created_by=self.admin
        )
        assigned_admin_lead = Lead.objects.create(
            inquiry=assigned_admin_inquiry,
            assigned_telecaller=self.tele1,
            assigned_by=self.admin,
            status='New'
        )

        telecaller_inquiry = Inquiry.objects.create(
            full_name='Telecaller Created Contact',
            mobile_number='7777777780',
            email='tele-created@example.com',
            city='Pune',
            course_interest='UI/UX',
            source='Website',
            status='New',
            created_by=self.tele1
        )
        telecaller_lead = Lead.objects.create(
            inquiry=telecaller_inquiry,
            assigned_telecaller=self.tele1,
            status='New'
        )

        all_response = self.client_admin.get(reverse('lead_assign'), {'assigned': 'all'})
        self.assertEqual(all_response.status_code, 200)
        all_ids = {lead.pk for lead in all_response.context['page_obj'].object_list}
        self.assertIn(queue_lead.pk, all_ids)
        self.assertIn(assigned_admin_lead.pk, all_ids)
        self.assertNotIn(telecaller_lead.pk, all_ids)

        assigned_response = self.client_admin.get(reverse('lead_assign'), {'assigned': 'yes'})
        self.assertEqual(assigned_response.status_code, 200)
        assigned_ids = {lead.pk for lead in assigned_response.context['page_obj'].object_list}
        self.assertIn(assigned_admin_lead.pk, assigned_ids)
        self.assertNotIn(queue_lead.pk, assigned_ids)
        self.assertNotIn(telecaller_lead.pk, assigned_ids)

        unassigned_response = self.client_admin.get(reverse('lead_assign'), {'assigned': 'no'})
        self.assertEqual(unassigned_response.status_code, 200)
        unassigned_ids = {lead.pk for lead in unassigned_response.context['page_obj'].object_list}
        self.assertIn(queue_lead.pk, unassigned_ids)
        self.assertNotIn(assigned_admin_lead.pk, unassigned_ids)
        self.assertNotIn(telecaller_lead.pk, unassigned_ids)

    def test_bulk_lead_actions_and_isolation(self):
        lead1 = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')
        lead2 = Lead.objects.create(inquiry=self.inquiry2, assigned_telecaller=self.tele2, status='New')

        # 1. Telecaller 1 bulk updates their own lead
        response = self.client_tele1.post(reverse('lead_bulk_action'), {
            'leads': [lead1.pk],
            'action': 'Mark Interested'
        })
        self.assertEqual(response.status_code, 302)
        lead1.refresh_from_db()
        self.assertEqual(lead1.status, 'Interested')

        # 2. Telecaller 1 tries to bulk update Telecaller 2's lead - should be skipped (status remains New)
        response = self.client_tele1.post(reverse('lead_bulk_action'), {
            'leads': [lead2.pk],
            'action': 'Mark Contacted'
        })
        self.assertEqual(response.status_code, 302)
        lead2.refresh_from_db()
        self.assertEqual(lead2.status, 'New') 

    def test_lead_list_date_filter_matches_local_day(self):
        lead1 = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='New')
        lead2 = Lead.objects.create(inquiry=self.inquiry2, assigned_telecaller=self.tele1, status='New')
        tz = timezone.get_current_timezone()
        selected_date = datetime.date(2026, 6, 29)
        other_date = datetime.date(2026, 6, 28)
        Lead.objects.filter(pk=lead1.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time(9, 15)), tz)
        )
        Lead.objects.filter(pk=lead2.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(other_date, datetime.time(17, 20)), tz)
        )

        response = self.client_tele1.get(reverse('lead_list'), {'date': '29-06-2026'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')
        self.assertContains(response, 'value="2026-06-29"')

    def test_source_analytics_view(self):
        lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='Qualified')

        response = self.client_tele1.get(reverse('reports_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Website")

    def test_telecaller_performance_report(self):
        lead = Lead.objects.create(inquiry=self.inquiry1, assigned_telecaller=self.tele1, status='Qualified')
        CallLog.objects.create(lead=lead, call_duration=45, call_status='Connected', created_by=self.tele1)

        # 1. Telecaller views report (can only see own row)
        response = self.client_tele1.get(reverse('telecaller_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tele1')
        self.assertNotContains(response, 'tele2')

        # 2. Admin views report (can see all rows)
        response = self.client_admin.get(reverse('telecaller_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tele1')
        self.assertContains(response, 'tele2')

        # 3. Export CSV
        response = self.client_admin.get(reverse('telecaller_report'), {'export': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'tele1')

        # 4. Export Excel
        response = self.client_admin.get(reverse('telecaller_report'), {'export': 'excel'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class CounselorModuleTests(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(username='admin_user', password='password', role='admin')
        self.counselor1 = User.objects.create_user(username='counselor1', password='password', role='counselor')
        self.counselor2 = User.objects.create_user(username='counselor2', password='password', role='counselor')
        self.telecaller = User.objects.create_user(username='tele_user', password='password', role='telecaller')
        self.student = User.objects.create_user(username='student_user', password='password', role='student')

        # Create clients
        self.client_admin = Client()
        self.client_counselor1 = Client()
        self.client_counselor2 = Client()
        self.client_tele = Client()
        self.client_student = Client()

        # Log in
        self.client_admin.login(username='admin_user', password='password')
        self.client_counselor1.login(username='counselor1', password='password')
        self.client_counselor2.login(username='counselor2', password='password')
        self.client_tele.login(username='tele_user', password='password')
        self.client_student.login(username='student_user', password='password')

        # Create base inquiries & leads
        self.inquiry1 = Inquiry.objects.create(
            full_name='Alice Candidate',
            mobile_number='9999999991',
            email='alice@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='Qualified',
            created_by=self.telecaller
        )
        self.lead1 = Lead.objects.create(
            inquiry=self.inquiry1,
            assigned_telecaller=self.telecaller,
            assigned_counselor=self.counselor1,
            status='Qualified',
            counselor_status='NEW'
        )

        self.inquiry2 = Inquiry.objects.create(
            full_name='Bob Candidate',
            mobile_number='9999999992',
            email='bob@example.com',
            city='Pune',
            course_interest='Java',
            source='Walk-In',
            status='Qualified',
            created_by=self.telecaller
        )
        self.lead2 = Lead.objects.create(
            inquiry=self.inquiry2,
            assigned_telecaller=self.telecaller,
            assigned_counselor=self.counselor2,
            status='Qualified',
            counselor_status='NEW'
        )

    def test_counselor_portal_access_restrictions(self):
        # Counselor can access counselor dashboard
        response = self.client_counselor1.get(reverse('counselor_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Telecaller is blocked from counselor dashboard
        response = self.client_tele.get(reverse('counselor_dashboard'))
        self.assertEqual(response.status_code, 403)

        # Student is blocked from counselor dashboard
        response = self.client_student.get(reverse('counselor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_counselor_data_isolation(self):
        # Counselor 1 sees lead 1 but not lead 2
        response = self.client_counselor1.get(reverse('counselor_lead_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Candidate')
        self.assertNotContains(response, 'Bob Candidate')

        # Counselor 2 sees lead 2 but not lead 1
        response = self.client_counselor2.get(reverse('counselor_lead_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bob Candidate')
        self.assertNotContains(response, 'Alice Candidate')

        # Counselor 1 cannot view Counselor 2's lead detail
        response = self.client_counselor1.get(reverse('counselor_lead_detail', kwargs={'pk': self.lead2.pk}))
        self.assertEqual(response.status_code, 403)

    def test_counselor_lead_list_date_filter_matches_local_day(self):
        tz = timezone.get_current_timezone()
        selected_date = datetime.date(2026, 6, 29)
        other_date = datetime.date(2026, 6, 28)
        Lead.objects.filter(pk=self.lead1.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time(11, 0)), tz)
        )
        Lead.objects.filter(pk=self.lead2.pk).update(
            created_at=timezone.make_aware(datetime.datetime.combine(other_date, datetime.time(14, 30)), tz)
        )

        response = self.client_admin.get(reverse('counselor_lead_list'), {'date': '29-06-2026'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Candidate')
        self.assertNotContains(response, 'Bob Candidate')
        self.assertContains(response, 'value="2026-06-29"')

    def test_record_counseling_session_transition(self):
        # Counselor 1 records a session for Lead 1
        response = self.client_counselor1.post(reverse('counselor_session_add'), {
            'lead': self.lead1.pk,
            'session_date': '2026-06-19 12:00:00',
            'discussion_notes': 'Alice is very keen on learning Django.',
            'career_guidance_notes': 'Recommended Full Stack Python path.',
            'next_action': 'Follow up next Monday'
        })
        self.assertEqual(response.status_code, 302)

        # Verify CounselingSession created
        from apps.management.models import CounselingSession
        self.assertTrue(CounselingSession.objects.filter(lead=self.lead1, counselor=self.counselor1).exists())

        # Verify Lead state changed to COUNSELING_DONE
        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.counselor_status, 'COUNSELING_DONE')

    def test_counselor_followup_and_outcome(self):
        # Schedule follow-up
        response = self.client_counselor1.post(reverse('counselor_followup_add'), {
            'lead': self.lead1.pk,
            'followup_date': '2026-06-25',
            'status': 'Pending',
            'outcome': '',
            'response': 'Call back scheduled'
        })
        self.assertEqual(response.status_code, 302)

        # Verify FollowUp created and Lead state transitioned to FOLLOW_UP_REQUIRED
        followup = FollowUp.objects.filter(lead=self.lead1, created_by=self.counselor1).first()
        self.assertIsNotNone(followup)
        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.counselor_status, 'FOLLOW_UP_REQUIRED')

        # Mark followup as Completed
        response = self.client_counselor1.get(reverse('counselor_followup_complete', kwargs={'pk': followup.pk}))
        self.assertEqual(response.status_code, 302)
        followup.refresh_from_db()
        self.assertEqual(followup.status, 'Completed')

        # Reschedule & Mark as Missed
        followup2 = FollowUp.objects.create(
            lead=self.lead1,
            followup_date='2026-06-20',
            status='Pending',
            created_by=self.counselor1
        )
        response = self.client_counselor1.get(reverse('counselor_followup_miss', kwargs={'pk': followup2.pk}))
        self.assertEqual(response.status_code, 302)
        followup2.refresh_from_db()
        self.assertEqual(followup2.status, 'Missed')

    def test_counselor_note_timeline(self):
        # Post note
        response = self.client_counselor1.post(reverse('counselor_note_add', kwargs={'lead_pk': self.lead1.pk}), {
            'note': 'Candidate requested batch details.'
        })
        self.assertEqual(response.status_code, 302)

        # Verify note in timeline
        from apps.management.models import LeadNote
        self.assertTrue(LeadNote.objects.filter(lead=self.lead1, note='Candidate requested batch details.').exists())

    def test_counselor_lead_status_update(self):
        # Update counselor status of lead 1 to INTERESTED
        response = self.client_counselor1.post(reverse('counselor_lead_status_update', kwargs={'pk': self.lead1.pk}), {
            'counselor_status': 'INTERESTED'
        })
        self.assertEqual(response.status_code, 302)
        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.counselor_status, 'INTERESTED')

    def test_counselor_lead_list_shows_and_updates_course_without_priority(self):
        self.lead1.converted_at = timezone.now()
        self.lead1.save(update_fields=['converted_at'])

        response = self.client_counselor1.get(reverse('counselor_lead_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python')
        self.assertContains(response, 'Course')
        self.assertNotContains(response, 'Priority')

        response = self.client_counselor1.post(reverse('counselor_lead_status_update', kwargs={'pk': self.lead1.pk}), {
            'counselor_status': 'NEW',
            'course_interest': 'Cloud Security',
            'notes': 'Updated course after counseling call',
        })
        self.assertEqual(response.status_code, 302)

        self.inquiry1.refresh_from_db()
        self.lead1.refresh_from_db()
        self.assertEqual(self.inquiry1.course_interest, 'Cloud Security')
        self.assertEqual(self.lead1.counselor_status, 'NEW')

    def test_counselor_assignment_management(self):
        # Telecaller tries counselor assignment - forbidden
        response = self.client_tele.post(reverse('lead_assign_counselor'), {
            'leads': [self.lead1.pk],
            'counselor': self.counselor2.pk
        })
        self.assertEqual(response.status_code, 403)

        # Admin assigns Lead 1 to Counselor 2
        response = self.client_admin.post(reverse('lead_assign_counselor'), {
            'leads': [self.lead1.pk],
            'counselor': self.counselor2.pk
        })
        self.assertEqual(response.status_code, 302)

        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.assigned_counselor, self.counselor2)
        self.assertEqual(self.lead1.assigned_by, self.admin)
        self.assertIsNotNone(self.lead1.assigned_at)

    def test_counselor_telecalling_unassigned_filter_excludes_owned_contacts(self):
        unassigned_inquiry = Inquiry.objects.create(
            full_name='Unassigned Contact',
            mobile_number='9999999993',
            email='unassigned@example.com',
            city='Nashik',
            course_interest='Python',
            source='Website',
            status='New',
            created_by=self.admin
        )
        unassigned_lead = Lead.objects.create(
            inquiry=unassigned_inquiry,
            status='New'
        )
        telecaller_inquiry = Inquiry.objects.create(
            full_name='Telecaller Owned Contact',
            mobile_number='9999999994',
            email='owned@example.com',
            city='Surat',
            course_interest='Java',
            source='Referral',
            status='New',
            created_by=self.admin
        )
        telecaller_lead = Lead.objects.create(
            inquiry=telecaller_inquiry,
            assigned_telecaller=self.telecaller,
            assigned_by=self.admin,
            status='New'
        )

        response = self.client_admin.get(reverse('lead_assign_counselor'), {
            'assignment_type': 'telecalling',
            'assigned': 'no'
        })

        self.assertEqual(response.status_code, 200)
        lead_ids = {lead.pk for lead in response.context['page_obj'].object_list}
        self.assertIn(unassigned_lead.pk, lead_ids)
        self.assertNotIn(telecaller_lead.pk, lead_ids)
        self.assertFalse(any(
            lead.assigned_telecaller_id or lead.assigned_counselor_id
            for lead in response.context['page_obj'].object_list
        ))

    def test_counselor_telecalling_grouped_call_status_cards_and_filter(self):
        busy_contact = Inquiry.objects.create(
            full_name='Busy Group Contact',
            mobile_number='9999999995',
            email='busy@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='BUSY',
            created_by=self.admin,
        )
        ringing_contact = Inquiry.objects.create(
            full_name='Ringing Group Contact',
            mobile_number='9999999996',
            email='ringing@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='NO_ANSWER',
            created_by=self.admin,
        )
        other_contact = Inquiry.objects.create(
            full_name='Other Group Contact',
            mobile_number='9999999997',
            email='other@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='OTHER',
            created_by=self.admin,
        )

        for inquiry in (busy_contact, ringing_contact, other_contact):
            Lead.objects.create(
                inquiry=inquiry,
                assigned_counselor=self.counselor1,
                first_assigned_counselor=self.counselor1,
                assigned_by=self.admin,
                status='New',
            )

        dashboard = self.client_counselor1.get(reverse('counselor_telecalling_dashboard'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['call_outcomes']['busy_callback_not_connected'], 2)
        self.assertEqual(dashboard.context['call_outcomes']['other'], 1)

        response = self.client_counselor1.get(reverse('inquiry_list'), {
            'scope': 'counselor_telecalling',
            'call_status_group': 'busy_callback_not_connected',
        })
        self.assertEqual(response.status_code, 200)
        inquiry_ids = {inquiry.pk for inquiry in response.context['page_obj'].object_list}
        self.assertIn(busy_contact.pk, inquiry_ids)
        self.assertIn(ringing_contact.pk, inquiry_ids)
        self.assertNotIn(other_contact.pk, inquiry_ids)
        self.assertEqual(response.context['call_status_group'], 'busy_callback_not_connected')

    def test_counselor_telecalling_exports_use_current_grouped_statuses(self):
        contact = Inquiry.objects.create(
            full_name='Counselor Invalid Contact',
            mobile_number='9999999901',
            email='invalid.counselor@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='INVALID_NUMBER',
            created_by=self.admin,
        )
        Lead.objects.create(
            inquiry=contact,
            assigned_counselor=self.counselor1,
            first_assigned_counselor=self.counselor1,
            assigned_by=self.admin,
            status='New',
        )
        message_contact = Inquiry.objects.create(
            full_name='Counselor Call Back Contact',
            mobile_number='9999999902',
            email='callback.counselor@example.com',
            city='Mumbai',
            course_interest='Python',
            source='Website',
            status='New',
            call_status='CALL_BACK',
            created_by=self.admin,
        )
        Lead.objects.create(
            inquiry=message_contact,
            assigned_counselor=self.counselor1,
            first_assigned_counselor=self.counselor1,
            assigned_by=self.admin,
            status='New',
        )

        export_response = self.client_counselor1.get(reverse('export_counselor_telecalling_csv'), {
            'date_filter': 'all',
        })
        self.assertEqual(export_response.status_code, 200)
        export_csv = export_response.content.decode()
        self.assertIn('Counselor Invalid Contact', export_csv)
        self.assertIn('9999999901', export_csv)
        self.assertIn('Switch Off / Wrong No. / Invalid No.', export_csv)
        self.assertNotIn('Pending Follow Up', export_csv)

        message_response = self.client_counselor1.get(reverse('export_message_numbers_csv'), {
            'date_filter': 'all',
        })
        self.assertEqual(message_response.status_code, 200)
        message_csv = message_response.content.decode()
        self.assertIn('current_status', message_csv)
        self.assertIn('Counselor Call Back Contact', message_csv)
        self.assertIn('9999999902', message_csv)
        self.assertIn('Busy / Call Back / Not Connected', message_csv)
        self.assertNotIn('Counselor Invalid Contact', message_csv)
        self.assertNotIn('9999999901', message_csv)
        self.assertNotIn('Switch Off / Wrong No. / Invalid No.', message_csv)

    def test_counselor_reports_dashboard_and_exports(self):
        # Record counseling session & followup to populate reports
        CounselingSession.objects.create(
            lead=self.lead1,
            counselor=self.counselor1,
            discussion_notes='Guidance session notes.'
        )
        FollowUp.objects.create(
            lead=self.lead1,
            followup_date='2026-06-19',
            status='Completed',
            outcome='Interested',
            created_by=self.counselor1
        )

        # Counselor views dashboard
        response = self.client_counselor1.get(reverse('counselor_reports_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Export performance report to CSV
        response = self.client_counselor1.get(reverse('counselor_reports_dashboard'), {
            'report_type': 'performance',
            'export': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # Export conversion report to Excel
        response = self.client_counselor1.get(reverse('counselor_reports_dashboard'), {
            'report_type': 'conversion',
            'export': 'excel'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_counselor_visit_sheet_crud_and_security(self):
        # 1. Access Control: Telecaller and Student are blocked from visits list
        response = self.client_tele.get(reverse('counselor_visit_list'))
        self.assertEqual(response.status_code, 403)
        response = self.client_student.get(reverse('counselor_visit_list'))
        self.assertEqual(response.status_code, 403)

        # Counselor can access visits list
        response = self.client_counselor1.get(reverse('counselor_visit_list'))
        self.assertEqual(response.status_code, 200)

        # 2. CRUD: Counselor 1 adds a visit sheet for Lead 1
        response = self.client_counselor1.post(reverse('counselor_visit_add'), {
            'lead': self.lead1.pk,
            'visit_date': '2026-06-25',
            'visit_time': '14:30:00',
            'status': 'Scheduled',
            'remarks': 'F2F discussion on course syllabus.'
        })
        self.assertEqual(response.status_code, 302) # Redirect to visit list

        # Verify VisitSheet created in database
        visit = VisitSheet.objects.filter(lead=self.lead1, counselor=self.counselor1).first()
        self.assertIsNotNone(visit)
        self.assertEqual(visit.remarks, 'F2F discussion on course syllabus.')
        self.assertEqual(visit.created_by, self.counselor1)

        # Verify LeadActivity logged
        self.assertTrue(self.lead1.activities.filter(activity_type='NOTE_ADDED', description__icontains="scheduled candidate visit").exists())

        # 3. Data Isolation: Counselor 2 cannot view Counselor 1's visit in the list or edit it
        response = self.client_counselor2.get(reverse('counselor_visit_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Alice Candidate')

        # Counselor 2 tries to edit Counselor 1's visit sheet - forbidden
        response = self.client_counselor2.get(reverse('counselor_visit_edit', kwargs={'pk': visit.pk}))
        self.assertEqual(response.status_code, 403)

        response = self.client_counselor2.post(reverse('counselor_visit_edit', kwargs={'pk': visit.pk}), {
            'lead': self.lead1.pk,
            'visit_date': '2026-06-25',
            'visit_time': '15:00:00',
            'status': 'Visited',
            'remarks': 'Updated by counselor 2.'
        })
        self.assertEqual(response.status_code, 403)

        # Counselor 1 can edit their own visit sheet
        response = self.client_counselor1.post(reverse('counselor_visit_edit', kwargs={'pk': visit.pk}), {
            'lead': self.lead1.pk,
            'visit_date': '2026-06-25',
            'visit_time': '16:00:00',
            'status': 'Visited',
            'remarks': 'Successfully visited and discussed syllabus.'
        })
        self.assertEqual(response.status_code, 302) # Redirect
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'Visited')
        self.assertEqual(visit.visit_time, datetime.time(16, 0))

        # 4. Reports Export Security Check: Export to CSV/Excel is blocked for visit report type
        response = self.client_counselor1.get(reverse('counselor_reports_dashboard'), {
            'report_type': 'visit',
            'export': 'csv'
        })
        self.assertEqual(response.status_code, 403)

        response = self.client_counselor1.get(reverse('counselor_reports_dashboard'), {
            'report_type': 'visit',
            'export': 'excel'
        })
        self.assertEqual(response.status_code, 403)
