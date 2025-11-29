# E:\study\worker_inventory\worker_inventory_backend\inventory\serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import InventoryItem, AssignedItem, UsageLog, CourierShipment, CourierItem, WorkerLocation


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


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
    worker_name = serializers.CharField(source='worker.username', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = UsageLog
        fields = '__all__'


class CourierItemSerializer(serializers.ModelSerializer):
    item = InventoryItemSerializer()

    class Meta:
        model = CourierItem
        fields = ['id', 'item', 'quantity']


class CourierShipmentSerializer(serializers.ModelSerializer):
    items = CourierItemSerializer(many=True, read_only=True)
    worker = UserSerializer(read_only=True)
    worker_name = serializers.CharField(source='worker.username', read_only=True)

    class Meta:
        model = CourierShipment
        fields = ['id', 'worker', 'worker_name', 'status', 'items', 'created_at', 'sent_at', 
                  'received_at', 'received_quantity', 'received_photo', 'approved_at']


class WorkerLocationSerializer(serializers.ModelSerializer):
    worker = UserSerializer(read_only=True)
    worker_name = serializers.CharField(source='worker.username', read_only=True)

    class Meta:
        model = WorkerLocation
        fields = ['id', 'worker', 'worker_name', 'latitude', 'longitude', 'timestamp']


class MemberDetailSerializer(serializers.ModelSerializer):
    assigned_items = serializers.SerializerMethodField()
    last_location = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'assigned_items', 'last_location']

    def get_assigned_items(self, obj):
        items = AssignedItem.objects.filter(worker=obj)
        return AssignedItemSerializer(items, many=True).data

    def get_last_location(self, obj):
        location = WorkerLocation.objects.filter(worker=obj).first()
        if location:
            return WorkerLocationSerializer(location).data
        return None