from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel


class StudentProfile(SoftDeleteModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField()
    profile_picture = models.ImageField(upload_to='student_profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    batch = models.ForeignKey(
        'batches.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    course_fee_at_admission = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="The locked course fee at the time of admission approval."
    )

    class Meta:
        # Pin to the existing DB table so no ALTER TABLE is needed.
        # The table was originally created by the 'exam' app as exam_studentprofile.
        db_table = 'exam_studentprofile'

    def __str__(self):
        return self.full_name


class StudentAdmission(SoftDeleteModel):
    admission_date = models.DateField(null=True, blank=True)
    student_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=20, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    center = models.ForeignKey('centers.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')
    enrollment_no = models.CharField(max_length=100, unique=True)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')
    timetable_course = models.CharField(max_length=255, null=True, blank=True)
    whatsapp_no = models.CharField(max_length=20)
    alt_mobile = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    father_name = models.CharField(max_length=255)
    mother_name = models.CharField(max_length=255)
    family_id = models.CharField(max_length=100, null=True, blank=True)
    marital_status = models.CharField(max_length=50, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    medium = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField()
    photo = models.ImageField(upload_to='admission_photos/', null=True, blank=True)
    pincode = models.CharField(max_length=20)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    passed_exam = models.CharField(max_length=255, null=True, blank=True)
    marks_grade = models.CharField(max_length=100, null=True, blank=True)
    board = models.CharField(max_length=255, null=True, blank=True)
    passing_year = models.CharField(max_length=20, null=True, blank=True)

    # Upload Documents
    aadhar_card = models.FileField(upload_to='admission_docs/', null=True, blank=True)
    aadhar_no = models.CharField(max_length=50, null=True, blank=True)
    admission_form_doc = models.FileField(upload_to='admission_docs/', null=True, blank=True)
    family_id_doc = models.FileField(upload_to='admission_docs/', null=True, blank=True)
    marksheet_10th = models.FileField(upload_to='admission_docs/', null=True, blank=True)
    marksheet_10th_plus = models.FileField(upload_to='admission_docs/', null=True, blank=True)

    # Workflow fields
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_admission'
    )
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_admissions')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_admissions')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_studentadmission'

    def __str__(self):
        return f"{self.student_name} ({self.enrollment_no})"
