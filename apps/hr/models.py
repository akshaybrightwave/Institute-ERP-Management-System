from django.conf import settings
from django.db import models
from django.utils import timezone


class Candidate(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('new', 'New Candidate'),
        ('called', 'Called'),
        ('no_response', 'No Response'),
        ('follow_up_pending', 'Follow-up Pending'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('joined', 'Joined'),
        ('on_hold', 'On Hold'),
    )
    SOURCE_CHOICES = (
        ('naukri', 'Naukri.com'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Referral'),
        ('walk_in', 'Walk-in'),
        ('website', 'Website'),
        ('campus', 'Campus'),
        ('other', 'Other'),
    )

    full_name = models.CharField(max_length=160)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    dob = models.DateField(null=True, blank=True)
    mobile = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    qualification = models.CharField(max_length=180, blank=True)
    experience = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    current_company = models.CharField(max_length=180, blank=True)
    skills = models.TextField(blank=True)
    current_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    applying_position = models.CharField(max_length=160)
    department = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, blank=True)
    assigned_hr = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_candidates',
        limit_choices_to={'role': 'hr'},
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    resume = models.FileField(upload_to='hr/resumes/', blank=True)
    photo = models.ImageField(upload_to='hr/candidates/', blank=True)

    date_added = models.DateField(default=timezone.localdate)
    last_call_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_created_candidates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return self.full_name

    @property
    def latest_follow_up(self):
        return self.followups.order_by('-follow_up_date', '-follow_up_time').first()

    @property
    def next_follow_up(self):
        now_date = timezone.localdate()
        return self.followups.filter(follow_up_date__gte=now_date).order_by('follow_up_date', 'follow_up_time').first()

    @property
    def latest_activity(self):
        return self.activities.order_by('-created_at').first()


class FollowUp(models.Model):
    TYPE_CHOICES = (
        ('call', 'Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
    )
    OUTCOME_CHOICES = (
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('call_later', 'Call Later'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('no_response', 'No Response'),
    )

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='followups')
    follow_up_date = models.DateField()
    follow_up_time = models.TimeField()
    follow_up_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    remarks = models.TextField(blank=True)
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES, blank=True)
    completed = models.BooleanField(default=False)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_followups',
        limit_choices_to={'role': 'hr'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['follow_up_date', 'follow_up_time']

    def __str__(self):
        return f"{self.candidate} - {self.get_follow_up_type_display()}"

    @property
    def is_overdue(self):
        return not self.completed and self.follow_up_date < timezone.localdate()


class Interview(models.Model):
    TYPE_CHOICES = (
        ('hr', 'HR Round'),
        ('technical', 'Technical Round'),
        ('final', 'Final Round'),
    )
    DECISION_CHOICES = (
        ('pending', 'Pending'),
        ('select', 'Select'),
        ('reject', 'Reject'),
        ('hold', 'Hold'),
    )

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    interviewer = models.CharField(max_length=160)
    date = models.DateField()
    time = models.TimeField()
    meeting_link = models.URLField(blank=True)
    venue = models.CharField(max_length=220, blank=True)
    communication = models.PositiveSmallIntegerField(null=True, blank=True)
    technical_skills = models.PositiveSmallIntegerField(null=True, blank=True)
    confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    overall_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending')
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_interviews',
        limit_choices_to={'role': 'hr'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.candidate} - {self.get_interview_type_display()}"


class CandidateNote(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.candidate}"


class CandidateActivity(models.Model):
    ACTIVITY_CHOICES = (
        ('created', 'Candidate Added'),
        ('call', 'Call Completed'),
        ('followup', 'Follow-up Added'),
        ('interview', 'Interview Scheduled'),
        ('feedback', 'Interview Conducted'),
        ('status', 'Status Changed'),
        ('note', 'Note Added'),
        ('document', 'Document Updated'),
    )

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PlacementCompany(models.Model):
    name = models.CharField(max_length=180, blank=True)
    industry = models.CharField(max_length=140, blank=True)
    contact_person = models.CharField(max_length=140, blank=True)
    designation = models.CharField(max_length=140, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    package_offered = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='hr/placement/companies/', blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='placement_companies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', '-updated_at']

    def __str__(self):
        return self.name or f"Company #{self.pk}"

    @property
    def students_sent_count(self):
        return self.placement_assignments.count()

    @property
    def selected_count(self):
        return self.placement_assignments.filter(final_status__in=['selected', 'joined']).count()

    @property
    def rejected_count(self):
        return self.placement_assignments.filter(final_status='rejected').count()

    @property
    def joined_count(self):
        return self.placement_assignments.filter(final_status='joined').count()

    @property
    def placement_rate(self):
        sent = self.students_sent_count
        return round((self.selected_count / sent) * 100, 1) if sent else 0


class PlacementDrive(models.Model):
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    company = models.ForeignKey(
        PlacementCompany,
        on_delete=models.CASCADE,
        related_name='drives',
        null=True,
        blank=True,
    )
    job_role = models.CharField(max_length=160, blank=True)
    drive_date = models.DateField(null=True, blank=True)
    package = models.CharField(max_length=100, blank=True)
    eligibility_criteria = models.TextField(blank=True)
    venue = models.CharField(max_length=220, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='placement_drives',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['drive_date', '-updated_at']

    def __str__(self):
        company = self.company.name if self.company and self.company.name else 'Placement Drive'
        return f"{company} - {self.job_role or 'Role'}"

    @property
    def assignments_count(self):
        return self.assignments.count()

    @property
    def appeared_count(self):
        return self.assignments.filter(interview_status__in=['appeared', 'selected', 'rejected']).count()

    @property
    def selected_count(self):
        return self.assignments.filter(final_status__in=['selected', 'joined']).count()


class PlacementStudentAssignment(models.Model):
    INTERVIEW_STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('appeared', 'Appeared'),
        ('absent', 'Absent'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    )
    FINAL_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('joined', 'Joined'),
    )

    company = models.ForeignKey(PlacementCompany, on_delete=models.CASCADE, related_name='placement_assignments', null=True, blank=True)
    drive = models.ForeignKey(PlacementDrive, on_delete=models.SET_NULL, related_name='assignments', null=True, blank=True)
    student = models.ForeignKey('students.StudentProfile', on_delete=models.SET_NULL, related_name='placement_assignments', null=True, blank=True)
    student_name = models.CharField(max_length=160, blank=True)
    course_name = models.CharField(max_length=160, blank=True)
    percentage_or_cgpa = models.CharField(max_length=40, blank=True)
    skills = models.TextField(blank=True)
    interview_status = models.CharField(max_length=20, choices=INTERVIEW_STATUS_CHOICES, default='scheduled')
    final_status = models.CharField(max_length=20, choices=FINAL_STATUS_CHOICES, default='pending')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='placement_assignments_created')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.student:
            return self.student.full_name
        return self.student_name or f"Student #{self.pk}"

    @property
    def display_course(self):
        if self.student and self.student.batch and self.student.batch.course:
            return self.student.batch.course.name
        return self.course_name


class PlacementInterview(models.Model):
    STATUS_CHOICES = PlacementStudentAssignment.INTERVIEW_STATUS_CHOICES

    company = models.ForeignKey(PlacementCompany, on_delete=models.SET_NULL, related_name='placement_interviews', null=True, blank=True)
    drive = models.ForeignKey(PlacementDrive, on_delete=models.SET_NULL, related_name='placement_interviews', null=True, blank=True)
    assignment = models.ForeignKey(PlacementStudentAssignment, on_delete=models.CASCADE, related_name='interviews', null=True, blank=True)
    interview_round = models.CharField(max_length=140, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=220, blank=True)
    interviewer = models.CharField(max_length=160, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='placement_interviews_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time', '-updated_at']

    def __str__(self):
        return f"{self.assignment or 'Interview'} - {self.interview_round or self.get_status_display()}"


class PlacementOffer(models.Model):
    OFFER_STATUS_CHOICES = (
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('pending', 'Pending'),
    )
    JOINING_STATUS_CHOICES = (
        ('joined', 'Joined'),
        ('not_joined', 'Not Joined'),
        ('awaiting', 'Awaiting Joining'),
    )

    assignment = models.OneToOneField(PlacementStudentAssignment, on_delete=models.CASCADE, related_name='offer', null=True, blank=True)
    company = models.ForeignKey(PlacementCompany, on_delete=models.SET_NULL, related_name='offers', null=True, blank=True)
    offered_package = models.CharField(max_length=100, blank=True)
    offer_status = models.CharField(max_length=20, choices=OFFER_STATUS_CHOICES, default='pending')
    joining_status = models.CharField(max_length=20, choices=JOINING_STATUS_CHOICES, default='awaiting')
    joining_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='placement_offers_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Offer - {self.assignment or self.company}"


class PlacementActivity(models.Model):
    ACTIVITY_CHOICES = (
        ('company', 'Company Added'),
        ('drive', 'Drive Created'),
        ('assignment', 'Students Assigned'),
        ('interview', 'Interview Scheduled'),
        ('offer', 'Offer Updated'),
        ('result', 'Result Published'),
    )

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    company = models.ForeignKey(PlacementCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    drive = models.ForeignKey(PlacementDrive, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ProjectCompany(models.Model):
    name = models.CharField(max_length=180, blank=True)
    industry = models.CharField(max_length=140, blank=True)
    contact_person = models.CharField(max_length=140, blank=True)
    designation = models.CharField(max_length=140, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    project_value = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='hr/projects/companies/', blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_companies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', '-updated_at']

    def __str__(self):
        return self.name or f"Project Company #{self.pk}"

    @property
    def employees_sent_count(self):
        return self.project_assignments.count()

    @property
    def selected_count(self):
        return self.project_assignments.filter(final_status__in=['selected', 'allocated']).count()

    @property
    def rejected_count(self):
        return self.project_assignments.filter(final_status='rejected').count()

    @property
    def allocated_count(self):
        return self.project_assignments.filter(final_status='allocated').count()

    @property
    def project_rate(self):
        sent = self.employees_sent_count
        return round((self.allocated_count / sent) * 100, 1) if sent else 0


class ProjectDrive(models.Model):
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    company = models.ForeignKey(
        ProjectCompany,
        on_delete=models.CASCADE,
        related_name='drives',
        null=True,
        blank=True,
    )
    project_name = models.CharField(max_length=180, blank=True)
    role_required = models.CharField(max_length=160, blank=True)
    drive_date = models.DateField(null=True, blank=True)
    project_value = models.CharField(max_length=100, blank=True)
    eligibility_criteria = models.TextField(blank=True)
    venue = models.CharField(max_length=220, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_drives',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['drive_date', '-updated_at']

    def __str__(self):
        company = self.company.name if self.company and self.company.name else 'Project Drive'
        return f"{company} - {self.project_name or self.role_required or 'Project'}"

    @property
    def assignments_count(self):
        return self.assignments.count()

    @property
    def appeared_count(self):
        return self.assignments.filter(interview_status__in=['appeared', 'selected', 'rejected']).count()

    @property
    def selected_count(self):
        return self.assignments.filter(final_status__in=['selected', 'allocated']).count()

    @property
    def allocated_count(self):
        return self.assignments.filter(final_status='allocated').count()


class ProjectEmployeeAssignment(models.Model):
    INTERVIEW_STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('appeared', 'Appeared'),
        ('absent', 'Absent'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    )
    FINAL_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('allocated', 'Allocated'),
        ('released', 'Released'),
    )

    company = models.ForeignKey(ProjectCompany, on_delete=models.CASCADE, related_name='project_assignments', null=True, blank=True)
    drive = models.ForeignKey(ProjectDrive, on_delete=models.SET_NULL, related_name='assignments', null=True, blank=True)
    employee = models.ForeignKey('ExternalEmployee', on_delete=models.SET_NULL, related_name='project_assignments', null=True, blank=True)
    employee_name = models.CharField(max_length=160, blank=True)
    employee_code = models.CharField(max_length=30, blank=True)
    department = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=140, blank=True)
    skills = models.TextField(blank=True)
    interview_status = models.CharField(max_length=20, choices=INTERVIEW_STATUS_CHOICES, default='scheduled')
    final_status = models.CharField(max_length=20, choices=FINAL_STATUS_CHOICES, default='pending')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_assignments_created')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.employee:
            return self.employee.full_name
        return self.employee_name or f"Employee #{self.pk}"

    @property
    def display_designation(self):
        if self.employee and self.employee.designation:
            return self.employee.designation
        return self.designation


class ProjectInterview(models.Model):
    STATUS_CHOICES = ProjectEmployeeAssignment.INTERVIEW_STATUS_CHOICES

    company = models.ForeignKey(ProjectCompany, on_delete=models.SET_NULL, related_name='project_interviews', null=True, blank=True)
    drive = models.ForeignKey(ProjectDrive, on_delete=models.SET_NULL, related_name='project_interviews', null=True, blank=True)
    assignment = models.ForeignKey(ProjectEmployeeAssignment, on_delete=models.CASCADE, related_name='interviews', null=True, blank=True)
    interview_round = models.CharField(max_length=140, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=220, blank=True)
    interviewer = models.CharField(max_length=160, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_interviews_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time', '-updated_at']

    def __str__(self):
        return f"{self.assignment or 'Project Interview'} - {self.interview_round or self.get_status_display()}"


class ProjectAllocation(models.Model):
    ALLOCATION_STATUS_CHOICES = (
        ('allocated', 'Allocated'),
        ('not_allocated', 'Not Allocated'),
        ('awaiting', 'Awaiting Allocation'),
        ('released', 'Released'),
    )

    assignment = models.OneToOneField(ProjectEmployeeAssignment, on_delete=models.CASCADE, related_name='allocation', null=True, blank=True)
    company = models.ForeignKey(ProjectCompany, on_delete=models.SET_NULL, related_name='allocations', null=True, blank=True)
    billing_rate = models.CharField(max_length=100, blank=True)
    allocation_status = models.CharField(max_length=20, choices=ALLOCATION_STATUS_CHOICES, default='awaiting')
    allocation_date = models.DateField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_allocations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Allocation - {self.assignment or self.company}"


class ProjectActivity(models.Model):
    ACTIVITY_CHOICES = (
        ('company', 'Company Added'),
        ('drive', 'Project Drive Created'),
        ('assignment', 'Employees Assigned'),
        ('interview', 'Interview Scheduled'),
        ('allocation', 'Allocation Updated'),
        ('result', 'Result Published'),
    )

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    company = models.ForeignKey(ProjectCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    drive = models.ForeignKey(ProjectDrive, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ExternalEmployee(models.Model):
    BRANCH_CHOICES = (
        ('thane', 'Dcodetech Thane'),
        ('nashik', 'Dcodetech Nashik'),
    )
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    EMPLOYMENT_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('probation', 'Probation'),
        ('notice', 'Notice Period'),
        ('inactive', 'Inactive'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='external_employee_profile')
    branch = models.CharField(max_length=20, choices=BRANCH_CHOICES)
    employee_id = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='hr/external/employees/', blank=True)
    department = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=140, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    reporting_manager = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    scheduled_login_time = models.TimeField(null=True, blank=True)
    scheduled_logout_time = models.TimeField(null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=80, blank=True)
    monthly_attendance = models.PositiveSmallIntegerField(default=0)
    late_count = models.PositiveSmallIntegerField(default=0)
    leave_balance = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    resume = models.FileField(upload_to='hr/external/documents/resumes/', blank=True)
    offer_letter = models.FileField(upload_to='hr/external/documents/offers/', blank=True)
    aadhaar = models.FileField(upload_to='hr/external/documents/aadhaar/', blank=True)
    pan = models.FileField(upload_to='hr/external/documents/pan/', blank=True)
    bank_details = models.FileField(upload_to='hr/external/documents/bank/', blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='external_employees_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['branch', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"


class ExternalAttendanceLog(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        ('half_day', 'Half Day'),
        ('wfh', 'WFH'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    )

    employee = models.ForeignKey(ExternalEmployee, on_delete=models.CASCADE, related_name='attendance_logs')
    date = models.DateField(default=timezone.localdate)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    working_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    late_minutes = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    location_ip = models.CharField(max_length=80, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='external_attendance_marked')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'employee__full_name']
        unique_together = (('employee', 'date'),)

    def __str__(self):
        return f"{self.employee} - {self.date} - {self.get_status_display()}"

    @property
    def working_hours_display(self):
        if self.working_hours in (None, ''):
            return '-'
        total_minutes = int(self.working_hours * 60)
        return f'{total_minutes // 60:02d}h {total_minutes % 60:02d}m'
