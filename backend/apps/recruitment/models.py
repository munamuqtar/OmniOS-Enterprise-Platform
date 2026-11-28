from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from apps.organizations.models import TimeStampedModel
from apps.branches.models import Branch

def validate_resume_size(f):
    if f.size > 5 * 1024 * 1024:
        raise ValidationError("Resume must be 5 MB or smaller.")

class JobVacancy(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)
    department = models.ForeignKey("hr.Department", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="vacancies")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="vacancies")
    description = models.TextField(blank=True)
    openings = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    closing_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return self.title

class Candidate(TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="candidates")
    source = models.CharField(max_length=100, blank=True)
    summary = models.TextField(blank=True)
    resume = models.FileField(upload_to="resumes/", blank=True, null=True,
                              validators=[FileExtensionValidator(["pdf", "doc", "docx"]), validate_resume_size])

    class Meta:
        unique_together = ("email", "branch")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class RecruitmentApplication(TimeStampedModel):
    class Stage(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        EVALUATION = "evaluation", "Evaluation"
        OFFERED = "offered", "Offered"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    vacancy = models.ForeignKey(JobVacancy, on_delete=models.PROTECT, related_name="applications")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="applications")
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.APPLIED)
    rejection_reason = models.TextField(blank=True)
    interview_at = models.DateTimeField(null=True, blank=True)
    interview_location = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("candidate", "vacancy")
        indexes = [models.Index(fields=["branch", "stage"])]

class ApplicationStageHistory(TimeStampedModel):
    application = models.ForeignKey(RecruitmentApplication, on_delete=models.CASCADE, related_name="history")
    from_stage = models.CharField(max_length=12)
    to_stage = models.CharField(max_length=12)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)

class RecruitmentNote(TimeStampedModel):
    application = models.ForeignKey(RecruitmentApplication, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.TextField()