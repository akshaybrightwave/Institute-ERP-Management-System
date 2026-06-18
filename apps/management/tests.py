from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.management.models import Inquiry, Lead, CallLog, FollowUp
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
        # Student should be blocked from management dashboard
        response = self.client_student.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 403)

        # Telecaller should be blocked from ERP center list
        response = self.client_tele1.get(reverse('center_list'))
        self.assertEqual(response.status_code, 403)

        # Admin can access management dashboard
        response = self.client_admin.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Telecaller can access management dashboard
        response = self.client_tele1.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 200)

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

    def test_unauthorized_record_details_access(self):
        # Tele1 tries to view details of tele2's inquiry
        response = self.client_tele1.get(reverse('inquiry_detail', kwargs={'pk': self.inquiry2.pk}))
        self.assertEqual(response.status_code, 403)

        # Tele1 tries to edit tele2's inquiry
        response = self.client_tele1.get(reverse('inquiry_edit', kwargs={'pk': self.inquiry2.pk}))
        self.assertEqual(response.status_code, 403)

    def test_inquiry_to_lead_conversion_workflow(self):
        # Convert inquiry1 to lead
        response = self.client_tele1.post(reverse('inquiry_convert', kwargs={'pk': self.inquiry1.pk}))
        self.assertEqual(response.status_code, 302) # Redirect to lead detail

        # Verify Lead creation
        lead = Lead.objects.get(inquiry=self.inquiry1)
        self.assertEqual(lead.assigned_telecaller, self.tele1)
        self.assertEqual(lead.status, 'New')

        # Verify Inquiry status auto updated to Qualified
        self.inquiry1.refresh_from_db()
        self.assertEqual(self.inquiry1.status, 'Qualified')

        # Prevent duplicate conversion
        response = self.client_tele1.post(reverse('inquiry_convert', kwargs={'pk': self.inquiry1.pk}))
        self.assertEqual(response.status_code, 302) # Redirects to existing lead detail
