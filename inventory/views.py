# inventory/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.db import transaction
import uuid, os

from .models import InventoryItem, AssignedItem, UsageLog
from .serializers import (
    InventoryItemSerializer, AssignedItemSerializer,
    UsageLogSerializer, MemberDetailSerializer
)

# ---------- UTILITY ----------
def unique_filename(filename):
    base, ext = os.path.splitext(filename)
    return f"{uuid.uuid4().hex}{ext or '.jpg'}"


# ==========================================
#                STOCK (Admin)
# ==========================================

class StockListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = InventoryItem.objects.all().order_by('name')
        return Response(InventoryItemSerializer(items, many=True).data)


class StockDetailView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        name = request.data.get('name')
        qty = request.data.get('total_quantity')

        if not name or qty is None:
            return Response({"error": "name and quantity required"}, status=400)

        item = InventoryItem.objects.create(name=name, total_quantity=int(qty))
        return Response(InventoryItemSerializer(item).data, status=201)

    def put(self, request, item_id):
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        item.name = request.data.get("name", item.name)
        item.total_quantity = int(request.data.get("total_quantity", item.total_quantity))
        item.save()

        return Response(InventoryItemSerializer(item).data)

    def delete(self, request, item_id):
        try:
            InventoryItem.objects.get(id=item_id).delete()
            return Response({"message": "Deleted"})
        except InventoryItem.DoesNotExist:
            return Response({"error": "Not found"}, status=404)


# ==========================================
#              MEMBERS (Admin)
# ==========================================

class MembersListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        members = User.objects.filter(is_staff=False)
        return Response(MemberDetailSerializer(members, many=True).data)

# nw
class MemberDetailView(APIView):
    """Admin: Get / Assign items to member (simple version)"""
    permission_classes = [IsAdminUser]

    def get(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, is_staff=False)
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)

        serializer = MemberDetailSerializer(member)
        return Response(serializer.data)

    def put(self, request, member_id):
        """
        Simple assigning (NO stock sync, NO diff logic):
        {
            "item_id": 1,
            "quantity": 20
        }
        """
        try:
            member = User.objects.get(id=member_id, is_staff=False)
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)

        item_id = request.data.get("item_id")
        quantity = request.data.get("quantity")

        if not item_id or quantity is None:
            return Response({"error": "item_id and quantity required"}, status=400)

        # validate quantity
        try:
            quantity = int(quantity)
        except:
            return Response({"error": "quantity must be an integer"}, status=400)

        # get item
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

        # create or update assignment
        assigned, created = AssignedItem.objects.get_or_create(
            worker=member,
            item=item
        )

        # simple save
        assigned.assigned_quantity = quantity
        assigned.save()

        print(f"[Assign] Member={member.username}, Item={item.name}, Qty={quantity}")

        return Response({
            "message": "Assigned successfully",
            "assigned_id": assigned.id,
            "assigned_quantity": assigned.assigned_quantity,
            "item": item.name,
            "member": member.username
        })


class AssignItemView(APIView):
    """Admin assigns items to a member"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        member_id = request.data.get("member_id")
        item_id = request.data.get("item_id")
        qty = request.data.get("quantity")

        if not member_id or not item_id or qty is None:
            return Response({"error": "All fields required"}, status=400)

        try:
            member = User.objects.get(id=member_id, is_staff=False)
            item = InventoryItem.objects.get(id=item_id)
        except:
            return Response({"error": "Invalid member or item"}, status=404)

        assigned, created = AssignedItem.objects.get_or_create(worker=member, item=item)
        assigned.assigned_quantity = int(qty)
        assigned.save()

        return Response(AssignedItemSerializer(assigned).data)


# ==========================================
#               MEMBER SCREENS
# ==========================================nw

class AssignItemView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        member_id = request.data.get("member_id")
        item_id = request.data.get("item_id")
        qty = request.data.get("quantity")

        # simple logic
        try:
            member = User.objects.get(id=member_id, is_staff=False)
            item = InventoryItem.objects.get(id=item_id)
        except:
            return Response({"error": "Invalid member or item"}, status=400)

        assigned, created = AssignedItem.objects.get_or_create(worker=member, item=item)
        assigned.assigned_quantity = qty
        assigned.save()

        return Response({"message": "Assigned"})



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
            return Response({"error": "Invalid item"}, status=404)

        # make filename unique
        old = photo.name
        photo.name = unique_filename(photo.name)
        print(f"upload: rename {old} → {photo.name}")

        log = UsageLog.objects.create(
            worker=request.user,
            item=item,
            quantity_used=int(qty),
            photo=photo,
        )

        return Response({"id": log.id, "message": "Uploaded"}, status=201)


class PendingUsageView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        logs = UsageLog.objects.filter(is_approved=False).order_by('-timestamp')
        return Response(UsageLogSerializer(logs, many=True).data)


class ApproveUsageView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, log_id):
        try:
            log = UsageLog.objects.get(id=log_id)
        except UsageLog.DoesNotExist:
            return Response({"error": "Log not found"}, status=404)

        print(f"[ApproveUsage] Approving log #{log_id} worker={log.worker.username} item={log.item.name} qty={log.quantity_used}")

        # Mark as approved
        log.is_approved = True
        log.save(update_fields=["is_approved"])

        # Update assigned quantity
        try:
            assigned = AssignedItem.objects.get(worker=log.worker, item=log.item)
        except AssignedItem.DoesNotExist:
            return Response({"error": "Assigned record not found"}, status=404)

        old_assigned = assigned.assigned_quantity
        new_assigned = old_assigned - int(log.quantity_used)

        print(f"[ApproveUsage] Assigned before={old_assigned}, after={new_assigned}")

        assigned.assigned_quantity = new_assigned
        assigned.save(update_fields=["assigned_quantity"])

        # Decrease main stock
        item = log.item
        old_stock = item.total_quantity
        new_stock = old_stock - int(log.quantity_used)

        print(f"[ApproveUsage] Stock before={old_stock}, after={new_stock}")

        item.total_quantity = new_stock
        item.save(update_fields=["total_quantity"])

        return Response({
            "message": "Approved & Stock Updated",
            "assigned_after": new_assigned,
            "stock_after": new_stock
        })


class UsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = UsageLog.objects.filter(worker=request.user).order_by('-timestamp')
        return Response(UsageLogSerializer(logs, many=True).data)
