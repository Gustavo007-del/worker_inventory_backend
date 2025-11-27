from rest_framework import serializers
from django.contrib.auth.models import User
from .models import InventoryItem, AssignedItem, UsageLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class AssignedItemSerializer(serializers.ModelSerializer):
    item = InventoryItemSerializer()

    class Meta:
        model = AssignedItem
        fields = ['id', 'item', 'assigned_quantity']


class UsageLogSerializer(serializers.ModelSerializer):
    worker = UserSerializer(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = UsageLog
        fields = '__all__'
