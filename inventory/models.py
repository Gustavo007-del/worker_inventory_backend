# E:\study\worker_inventory\worker_inventory_backend\inventory\models.py
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


class CourierShipment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courier_shipments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_quantity = models.IntegerField(default=0, null=True, blank=True)
    received_photo = models.ImageField(upload_to="courier_received/", null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Courier to {self.worker.username} - {self.status}"


class CourierItem(models.Model):
    shipment = models.ForeignKey(CourierShipment, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"


class WorkerLocation(models.Model):
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.username} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']