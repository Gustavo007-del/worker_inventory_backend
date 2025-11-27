from django.db import models
from django.contrib.auth.models import User


class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    total_quantity = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class AssignedItem(models.Model):
    worker = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    assigned_quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.worker.username} - {self.item.name}"


class UsageLog(models.Model):
    worker = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_used = models.IntegerField()
    photo = models.ImageField(upload_to="usage_photos/")
    is_approved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.username} used {self.quantity_used} of {self.item.name}"
