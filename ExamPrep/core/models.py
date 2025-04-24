from django.db import models
from django.contrib.auth.models import User

# Syllabus Model
class Syllabus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    file = models.FileField(upload_to='syllabus_files/', blank=True, null=True)  # Optional file upload
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Syllabus by {self.user.username}"

# Notes Model
class Notes(models.Model):
    syllabus = models.ForeignKey('core.Syllabus', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notes for syllabus {self.syllabus.id}"

# Quizzes Model
class Quizzes(models.Model):
    syllabus = models.ForeignKey('core.Syllabus', on_delete=models.CASCADE)
    question = models.TextField()
    options = models.JSONField()
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz for syllabus {self.syllabus.id}"
