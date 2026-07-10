from django.db import models
from apps.soft_delete import SoftDeleteModel


class Center(SoftDeleteModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    # Owner Information
    owner_name = models.CharField(max_length=255, null=True, blank=True)
    head_qualification = models.CharField(max_length=255, null=True, blank=True)
    owner_dob = models.DateField(null=True, blank=True)
    pan_number = models.CharField(max_length=50, null=True, blank=True)

    prefix_roll_no = models.CharField(max_length=50, null=True, blank=True)
    valid_upto = models.DateField(null=True, blank=True)

    aadhar_number = models.CharField(max_length=50, null=True, blank=True)

    # Address Information
    state = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=20, null=True, blank=True)

    # Infrastructure Details
    staff_count = models.IntegerField(default=0)
    classrooms_count = models.IntegerField(default=0)
    computers_count = models.IntegerField(default=0)
    space_sqft = models.IntegerField(default=0)
    has_reception = models.BooleanField(default=False)
    has_staff_room = models.BooleanField(default=False)
    has_water_supply = models.BooleanField(default=False)
    has_toilet = models.BooleanField(default=False)

    # Contact Information
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    # Documents
    owner_image = models.ImageField(upload_to='centers/owners/', null=True, blank=True)
    aadhar_doc = models.FileField(upload_to='centers/docs/', null=True, blank=True)
    signature_doc = models.ImageField(upload_to='centers/docs/', null=True, blank=True)
    logo_doc = models.ImageField(upload_to='centers/logos/', null=True, blank=True)
    address_proof = models.FileField(upload_to='centers/docs/', null=True, blank=True)
    agreement_doc = models.FileField(upload_to='centers/docs/', null=True, blank=True)

    # Wallet
    wallet_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    def __str__(self):
        return self.name


class CenterCourseAssignment(models.Model):
    """
    Explicit through-model replacing the simple ManyToManyField.
    """
    center = models.ForeignKey(
        'Center',
        on_delete=models.CASCADE,
        related_name='course_assignments'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    is_active = models.BooleanField(default=True)
    assigned_date = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='course_assignments_made'
    )

    class Meta:
        unique_together = ('center', 'course')
        ordering = ['-assigned_date']

    def __str__(self):
        return f"{self.center.name} \u2192 {self.course.name}"


class CenterCertificate(SoftDeleteModel):
    center = models.ForeignKey(
        'Center',
        on_delete=models.CASCADE,
        related_name='center_certificates'
    )
    certificate_number = models.CharField(max_length=100, unique=True)
    issue_date = models.DateField()
    valid_upto = models.DateField(null=True, blank=True)
    certificate_status = models.CharField(max_length=50, default='Active')

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_center_certificates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centers_centercertificate'

    def __str__(self):
        return f"{self.certificate_number} - {self.center.name}"
