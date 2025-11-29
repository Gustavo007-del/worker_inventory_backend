# E:\study\worker_inventory\worker_inventory_backend\inventory\views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
import json

from .models import InventoryItem, AssignedItem, UsageLog, CourierShipment, CourierItem, WorkerLocation
from .serializers import (
    AssignedItemSerializer, UsageLogSerializer, InventoryItemSerializer,
    CourierShipmentSerializer, CourierItemSerializer, WorkerLocationSerializer,
    MemberDetailSerializer
)


# ==================== STOCK MANAGEMENT ====================

class StockListView(APIView):
    """Get all items in stock (for all users)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)


class StockDetailView(APIView):
    """Admin: Create, Update, Delete stock items"""
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Create new item"""
        data = request.data
        item = InventoryItem.objects.create(
            name=data.get('name'),
            total_quantity=int(data.get('total_quantity', 0))
        )
        return Response(InventoryItemSerializer(item).data, status=201)

    def put(self, request, item_id):
        """Update item"""
        try:
            item = InventoryItem.objects.get(id=item_id)
            item.name = request.data.get('name', item.name)
            item.total_quantity = int(request.data.get('total_quantity', item.total_quantity))
            item.save()
            return Response(InventoryItemSerializer(item).data)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

    def delete(self, request, item_id):
        """Delete item"""
        try:
            item = InventoryItem.objects.get(id=item_id)
            item.delete()
            return Response({"message": "Item deleted"})
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)


class SearchStockView(APIView):
    """Search & Sort stock items"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        sort_by = request.query_params.get('sort', 'name')  # name, quantity, -quantity
        
        items = InventoryItem.objects.all()
        
        if query:
            items = items.filter(name__icontains=query)
        
        items = items.order_by(sort_by)
        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)


# ==================== MEMBER MANAGEMENT (ADMIN) ====================

class MembersListView(APIView):
    """Admin: Get all members with their details"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        members = User.objects.filter(is_staff=False)
        serializer = MemberDetailSerializer(members, many=True)
        return Response(serializer.data)


class MemberDetailView(APIView):
    """Admin: Get/Update single member details"""
    permission_classes = [IsAdminUser]

    def get(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, is_staff=False)
            serializer = MemberDetailSerializer(member)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)

    def put(self, request, member_id):
        """Admin: Update member assignment"""
        try:
            member = User.objects.get(id=member_id, is_staff=False)
            item_id = request.data.get('item_id')
            quantity = request.data.get('quantity')
            
            if not item_id or quantity is None:
                return Response({"error": "item_id and quantity required"}, status=400)
            
            item = InventoryItem.objects.get(id=item_id)
            assigned, created = AssignedItem.objects.get_or_create(worker=member, item=item)
            assigned.assigned_quantity = int(quantity)
            assigned.save()
            
            return Response(AssignedItemSerializer(assigned).data)
        except (User.DoesNotExist, InventoryItem.DoesNotExist):
            return Response({"error": "Member or Item not found"}, status=404)


# ==================== MEMBER PROFILE ====================

class MemberProfileView(APIView):
    """Member: Get own profile (read-only)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MemberDetailSerializer(request.user)
        return Response(serializer.data)


# ==================== ASSIGNED ITEMS (EXISTING) ====================

class AssignedItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        worker = request.user
        items = AssignedItem.objects.filter(worker=worker)
        serializer = AssignedItemSerializer(items, many=True)
        return Response(serializer.data)


# ==================== SUBMIT USAGE / EDIT ITEMS ====================

class SubmitUsageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        worker = request.user
        item_id = request.data.get('item_id')
        quantity_used = request.data.get('quantity_used')
        photo = request.FILES.get('photo')

        if not item_id or not quantity_used or not photo:
            return Response({"error": "Missing required fields"}, status=400)

        item = InventoryItem.objects.get(id=item_id)

        log = UsageLog.objects.create(
            worker=worker,
            item=item,
            quantity_used=quantity_used,
            photo=photo
        )

        return Response({"message": "Submitted, waiting for approval"})


# ==================== USAGE APPROVALS (EXISTING) ====================

class PendingUsageView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        logs = UsageLog.objects.filter(is_approved=False).order_by('-timestamp')
        serializer = UsageLogSerializer(logs, many=True)
        return Response(serializer.data)


class ApproveUsageView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, log_id):
        try:
            log = UsageLog.objects.get(id=log_id)
        except UsageLog.DoesNotExist:
            return Response({"error": "Log not found"}, status=404)

        log.is_approved = True
        log.save()

        # Reduce inventory assigned quantity
        assigned = AssignedItem.objects.get(worker=log.worker, item=log.item)
        assigned.assigned_quantity -= int(log.quantity_used)
        assigned.save()

        return Response({"message": "Approved & Quantity Updated"})


# ==================== USAGE HISTORY ====================

class UsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = UsageLog.objects.filter(worker=request.user).order_by('-timestamp')
        serializer = UsageLogSerializer(logs, many=True)
        return Response(serializer.data)


# ==================== COURIER OPERATIONS ====================

class CreateCourierView(APIView):
    """Admin: Create courier shipment for one or more workers"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Expected format:
        {
            "worker_ids": [1, 2, 3],
            "items": [
                {"item_id": 1, "quantity": 5},
                {"item_id": 2, "quantity": 10}
            ]
        }
        """
        worker_ids = request.data.get('worker_ids', [])
        items_data = request.data.get('items', [])

        if not worker_ids or not items_data:
            return Response({"error": "worker_ids and items required"}, status=400)

        shipments = []
        for worker_id in worker_ids:
            try:
                worker = User.objects.get(id=worker_id, is_staff=False)
            except User.DoesNotExist:
                continue

            shipment = CourierShipment.objects.create(worker=worker, status='pending')

            for item_data in items_data:
                try:
                    item = InventoryItem.objects.get(id=item_data['item_id'])
                    CourierItem.objects.create(
                        shipment=shipment,
                        item=item,
                        quantity=item_data['quantity']
                    )
                except InventoryItem.DoesNotExist:
                    continue

            shipments.append(shipment)

        serializer = CourierShipmentSerializer(shipments, many=True)
        return Response(serializer.data, status=201)


class SendCourierView(APIView):
    """Admin: Send courier shipment to workers"""
    permission_classes = [IsAdminUser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id)
            shipment.status = 'sent'
            shipment.sent_at = timezone.now()
            shipment.save()
            return Response(CourierShipmentSerializer(shipment).data)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)


class WorkerCourierView(APIView):
    """Worker: Get received couriers"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shipments = CourierShipment.objects.filter(worker=request.user).exclude(status='pending')
        serializer = CourierShipmentSerializer(shipments, many=True)
        return Response(serializer.data)


class ReceiveCourierView(APIView):
    """Worker: Receive courier, upload photo and quantity"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, worker=request.user)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        received_quantity = request.data.get('received_quantity')
        received_photo = request.FILES.get('received_photo')

        if not received_quantity or not received_photo:
            return Response({"error": "received_quantity and received_photo required"}, status=400)

        shipment.status = 'received'
        shipment.received_at = timezone.now()
        shipment.received_quantity = int(received_quantity)
        shipment.received_photo = received_photo
        shipment.save()

        return Response(CourierShipmentSerializer(shipment).data)


class AdminCourierApprovalsView(APIView):
    """Admin: Approve received couriers"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        shipments = CourierShipment.objects.filter(status='received').order_by('-received_at')
        serializer = CourierShipmentSerializer(shipments, many=True)
        return Response(serializer.data)

    def post(self, request, shipment_id):
        """Approve courier"""
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status='received')
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        # Update shipment status
        shipment.status = 'approved'
        shipment.approved_at = timezone.now()
        shipment.save()

        # Update worker's assigned items (increase quantity)
        for courier_item in shipment.items.all():
            assigned, created = AssignedItem.objects.get_or_create(
                worker=shipment.worker,
                item=courier_item.item
            )
            assigned.assigned_quantity += courier_item.quantity
            assigned.save()

            # Decrease from total inventory
            courier_item.item.total_quantity -= courier_item.quantity
            courier_item.item.save()

        return Response(CourierShipmentSerializer(shipment).data)


class RejectCourierView(APIView):
    """Admin: Reject received courier"""
    permission_classes = [IsAdminUser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status='received')
            shipment.status = 'rejected'
            shipment.save()
            return Response(CourierShipmentSerializer(shipment).data)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)


# ==================== LOCATION TRACKING ====================

class SaveLocationView(APIView):
    """Worker: Save/Update location"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if latitude is None or longitude is None:
            return Response({"error": "latitude and longitude required"}, status=400)

        location = WorkerLocation.objects.create(
            worker=request.user,
            latitude=float(latitude),
            longitude=float(longitude)
        )

        return Response(WorkerLocationSerializer(location).data, status=201)


class WorkerLocationsView(APIView):
    """Admin: Get all worker last locations"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        workers = User.objects.filter(is_staff=False)
        locations = []
        
        for worker in workers:
            last_location = WorkerLocation.objects.filter(worker=worker).first()
            if last_location:
                locations.append({
                    'worker_id': worker.id,
                    'worker_name': worker.username,
                    'latitude': last_location.latitude,
                    'longitude': last_location.longitude,
                    'timestamp': last_location.timestamp
                })

        return Response(locations)