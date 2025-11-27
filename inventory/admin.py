from django.contrib import admin
from .models import InventoryItem, AssignedItem, UsageLog

admin.site.register(InventoryItem)
admin.site.register(AssignedItem)
admin.site.register(UsageLog)
