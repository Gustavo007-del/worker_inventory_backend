from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import F
import uuid
import os

from .models import InventoryItem, AssignedItem, UsageLog, CourierShipment, CourierItem, WorkerLocation
from .serializers import (
    AssignedItemSerializer, UsageLogSerializer, InventoryItemSerializer,
    CourierShipmentSerializer, WorkerLocationSerializer,
    MemberDetailSerializer
)


# -------------------------
# UNIQUE FILE NAME GENERATOR
# -------------------------
def unique_filename(filename):
    base, ext = os.path.splitext(filename)
    return f"{uuid.uuid4().hex}{ext or '.jpg'}"


# ==================== STOCK ====================

class StockListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = InventoryItem.objects.all()
        return Response(InventoryItemSerializer(items, many=True).data)


class StockDetailView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        item = InventoryItem.objects.create(
            name=request.data.get("name"),
            total_quantity=int(request.data.get("total_quantity", 0)),
        )
        return Response(InventoryItemSerializer(item).data, status=201)

    def put(self, request, item_id):
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

        item.name = request.data.get("name", item.name)
        item.total_quantity = int(request.data.get("total_quantity", item.total_quantity))
        item.save()

        return Response(InventoryItemSerializer(item).data)

    def delete(self, request, item_id):
        try:
            InventoryItem.objects.get(id=item_id).delete()
            return Response({"message": "Item deleted"})
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)


# ==================== MEMBERS LIST ====================

class MembersListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        members = User.objects.filter(is_staff=False)
        return Response(MemberDetailSerializer(members, many=True).data)


# ==================== MEMBER DETAIL + ASSIGN ====================

class MemberDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, is_staff=False)
            return Response(MemberDetailSerializer(member).data)
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)

    def put(self, request, member_id):
        """
        Admin assigns or adjusts item quantity for member.
        Stock auto-syncs.
        """
        try:
            member = User.objects.get(id=member_id, is_staff=False)
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)

        item_id = request.data.get("item_id")
        quantity = request.data.get("quantity")

        if not item_id or quantity is None:
            return Response({"error": "item_id and quantity required"}, status=400)

        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

        new_qty = int(quantity)

        assigned, created = AssignedItem.objects.get_or_create(worker=member, item=item)
        old_qty = assigned.assigned_quantity
        diff = new_qty - old_qty

        print(f"[Assign] worker={member.username} item={item.name} old={old_qty} new={new_qty} diff={diff}")

        if diff > 0:
            # Need extra stock
            if item.total_quantity < diff:
                return Response(
                    {"error": f"Not enough stock (available={item.total_quantity}, needed={diff})"},
                    status=400
                )
            item.total_quantity = F("total_quantity") - diff
        elif diff < 0:
            # Return to stock
            item.total_quantity = F("total_quantity") + abs(diff)

        item.save(update_fields=["total_quantity"])

        assigned.assigned_quantity = new_qty
        assigned.save(update_fields=["assigned_quantity"])

        item.refresh_from_db()
        assigned.refresh_from_db()

        print(f"[Assign] Updated -> stock={item.total_quantity}, assigned={assigned.assigned_quantity}")

        return Response(AssignedItemSerializer(assigned).data)


# ==================== PROFILE (MEMBER) ====================

class MemberProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MemberDetailSerializer(request.user).data)


# ==================== ASSIGNED ITEMS ====================

class AssignedItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = AssignedItem.objects.filter(worker=request.user)
        return Response(AssignedItemSerializer(items, many=True).data)


# ==================== SUBMIT USAGE ====================

class SubmitUsageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        item_id = request.data.get("item_id")
        qty = request.data.get("quantity_used")
        photo = request.FILES.get("photo")

        if not item_id or not qty or not photo:
            return Response({"error": "Missing fields"}, status=400)

        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

        # Unique file name fix
        original = photo.name
        photo.name = unique_filename(photo.name)
        print(f"[Usage] rename {original} -> {photo.name}")

        log = UsageLog.objects.create(
            worker=request.user,
            item=item,
            quantity_used=int(qty),
            photo=photo
        )

        return Response({"message": "Submitted", "id": log.id}, status=201)


# ==================== APPROVE USAGE ====================

class PendingUsageView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        logs = UsageLog.objects.filter(is_approved=False).order_by("-timestamp")
        return Response(UsageLogSerializer(logs, many=True).data)


class ApproveUsageView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, log_id):
        try:
            log = UsageLog.objects.get(id=log_id)
        except UsageLog.DoesNotExist:
            return Response({"error": "Log not found"}, status=404)

        # approve
        log.is_approved = True
        log.save()

        # deduct from assignment
        assigned = AssignedItem.objects.get(worker=log.worker, item=log.item)
        assigned.assigned_quantity = F("assigned_quantity") - int(log.quantity_used)
        assigned.save()

        return Response({"message": "Usage approved"})


# ==================== USAGE HISTORY ====================

class UsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = UsageLog.objects.filter(worker=request.user).order_by("-timestamp")
        return Response(UsageLogSerializer(logs, many=True).data)


# ==================== COURIER ====================

class CreateCourierView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        worker_ids = request.data.get("worker_ids", [])
        items_data = request.data.get("items", [])

        if not worker_ids or not items_data:
            return Response({"error": "worker_ids and items required"}, status=400)

        shipments = []

        for wid in worker_ids:
            try:
                worker = User.objects.get(id=wid, is_staff=False)
            except User.DoesNotExist:
                continue

            shipment = CourierShipment.objects.create(worker=worker, status="pending")

            for entry in items_data:
                try:
                    item = InventoryItem.objects.get(id=entry["item_id"])
                    CourierItem.objects.create(
                        shipment=shipment,
                        item=item,
                        quantity=entry["quantity"]
                    )
                except:
                    continue

            shipments.append(shipment)

        return Response(CourierShipmentSerializer(shipments, many=True).data, status=201)


class WorkerCourierView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shipments = CourierShipment.objects.filter(worker=request.user).exclude(status="pending")
        return Response(CourierShipmentSerializer(shipments, many=True).data)


class ReceiveCourierView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, worker=request.user)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        qty = request.data.get("received_quantity")
        photo = request.FILES.get("received_photo")

        if not qty or not photo:
            return Response({"error": "Missing fields"}, status=400)

        qty = int(qty)

        # Unique filename fix
        original = photo.name
        photo.name = unique_filename(photo.name)
        print(f"[CourierReceive] {original} -> {photo.name}")

        shipment.status = "received"
        shipment.received_at = timezone.now()
        shipment.received_quantity = qty
        shipment.received_photo = photo
        shipment.save()

        return Response(CourierShipmentSerializer(shipment).data)


class AdminCourierApprovalsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        shipments = CourierShipment.objects.filter(status="received").order_by("-received_at")
        return Response(CourierShipmentSerializer(shipments, many=True).data)

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status="received")
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = "approved"
        shipment.approved_at = timezone.now()
        shipment.save()

        # Update assigned and reduce stock
        for citem in shipment.items.all():
            assigned, _ = AssignedItem.objects.get_or_create(
                worker=shipment.worker,
                item=citem.item
            )
            assigned.assigned_quantity = F("assigned_quantity") + citem.quantity
            assigned.save()

            # deduct from stock
            citem.item.total_quantity = F("total_quantity") - citem.quantity
            citem.item.save()

        return Response(CourierShipmentSerializer(shipment).data)


class RejectCourierView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status="received")
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = "rejected"
        shipment.save()
        return Response(CourierShipmentSerializer(shipment).data)


# ==================== WORKER LOCATION ====================

class SaveLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        if not latitude or not longitude:
            return Response({"error": "latitude and longitude required"}, status=400)

        loc = WorkerLocation.objects.create(
            worker=request.user,
            latitude=float(latitude),
            longitude=float(longitude),
        )

        return Response(WorkerLocationSerializer(loc).data, status=201)


class WorkerLocationsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        workers = User.objects.filter(is_staff=False)
        output = []

        for worker in workers:
            last = WorkerLocation.objects.filter(worker=worker).order_by("-timestamp").first()
            if last:
                output.append({
                    "worker_id": worker.id,
                    "worker_name": worker.username,
                    "latitude": last.latitude,
                    "longitude": last.longitude,
                    "timestamp": last.timestamp
                })

        return Response(output)
    

# ==================== COURIER OPERATIONS ====================

class CreateCourierView(APIView):
    """Admin: Create courier shipment"""
    permission_classes = [IsAdminUser]

    def post(self, request):
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
                except InventoryItem.DoesNotExist:
                    continue

                CourierItem.objects.create(
                    shipment=shipment,
                    item=item,
                    quantity=item_data['quantity']
                )

            shipments.append(shipment)

        return Response(CourierShipmentSerializer(shipments, many=True).data, status=201)


class SendCourierView(APIView):
    """Admin: Send courier shipment"""
    permission_classes = [IsAdminUser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = 'sent'
        shipment.sent_at = timezone.now()
        shipment.save()

        return Response(CourierShipmentSerializer(shipment).data)


class WorkerCourierView(APIView):
    """Worker: Get received couriers (sent or received or approved)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shipments = CourierShipment.objects.filter(worker=request.user).exclude(status='pending')
        return Response(CourierShipmentSerializer(shipments, many=True).data)


class ReceiveCourierView(APIView):
    """Worker: Receive courier and upload photo"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, worker=request.user)
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        qty = request.data.get('received_quantity')
        photo = request.FILES.get('received_photo')

        if not qty or not photo:
            return Response({"error": "received_quantity and received_photo required"}, status=400)

        try:
            qty = int(qty)
        except ValueError:
            return Response({"error": "received_quantity must be integer"}, status=400)

        original = photo.name
        photo.name = unique_filename(photo.name)
        print(f"[ReceiveCourierView] rename {original} -> {photo.name}")

        shipment.status = 'received'
        shipment.received_at = timezone.now()
        shipment.received_quantity = qty
        shipment.received_photo = photo
        shipment.save()

        return Response(CourierShipmentSerializer(shipment).data)


class AdminCourierApprovalsView(APIView):
    """Admin: Approve received courier shipments"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        shipments = CourierShipment.objects.filter(status='received')
        return Response(CourierShipmentSerializer(shipments, many=True).data)

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status='received')
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = 'approved'
        shipment.approved_at = timezone.now()
        shipment.save()

        for ci in shipment.items.all():
            assigned, _ = AssignedItem.objects.get_or_create(worker=shipment.worker, item=ci.item)
            assigned.assigned_quantity += ci.quantity
            assigned.save()

            ci.item.total_quantity -= ci.quantity
            ci.item.save()

        return Response(CourierShipmentSerializer(shipment).data)


class RejectCourierView(APIView):
    """Admin: Reject courier shipment"""
    permission_classes = [IsAdminUser]

    def post(self, request, shipment_id):
        try:
            shipment = CourierShipment.objects.get(id=shipment_id, status='received')
        except CourierShipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = 'rejected'
        shipment.save()

        return Response(CourierShipmentSerializer(shipment).data)

