from django.db import models
from django.contrib.auth.models import User
from Innovation_WebApp.models import Events

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Events, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # New field for replies. A comment with a non-null parent is a reply.
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )

    def __str__(self):
        return f"{self.user} - {self.content[:20]}"
    
    