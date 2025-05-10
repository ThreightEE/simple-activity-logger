from django.db import models

class ConfigChangeLog(models.Model):
    key: models.CharField = models.CharField(
        max_length=100
    )
    
    old_value: models.TextField = models.TextField(
        null=True,
        blank=True
    )
    new_value: models.TextField = models.TextField()

    changed_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering: list[str] = ['-changed_at']
        verbose_name: str = 'Config Change Log'
        verbose_name_plural: str = 'Config Change Logs'

    def __str__(self) -> str:
        return f"Change '{self.key}' at {self.changed_at.strftime('%Y-%m-%d %H:%M')}"
