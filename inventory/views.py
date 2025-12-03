# inventory/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import uuid, os, json

from .models import InventoryItem, AssignedItem, UsageLog, Attendance
from .serializers import (
    InventoryItemSerializer, AssignedItemSerializer,
    UsageLogSerializer, MemberDetailSerializer
)


@csrf_exempt
def check_in(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username")
    lat = data.get("lat")
    lng = data.get("lng")

    user = User.objects.get(username=username)
    today = timezone.now().date()

    attendance, created = Attendance.objects.get_or_create(user=user, date=today)

    if attendance.check_in:
        return JsonResponse({"error": "Already checked in"}, status=400)

    attendance.check_in = timezone.now()
    attendance.check_in_lat = lat
    attendance.check_in_lng = lng
    attendance.save()

    return JsonResponse({"message": "Check-in successful"})


@csrf_exempt
def check_out(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username")
    lat = data.get("lat")
    lng = data.get("lng")

    user = User.objects.get(username=username)
    today = timezone.now().date()

    try:
        attendance = Attendance.objects.get(user=user, date=today)
    except Attendance.DoesNotExist:
        return JsonResponse({"error": "Not checked in today"}, status=400)

    if attendance.check_out:
        return JsonResponse({"error": "Already checked out"}, status=400)

    attendance.check_out = timezone.now()
    attendance.check_out_lat = lat
    attendance.check_out_lng = lng
    attendance.save()

    return JsonResponse({"message": "Check-out successful"})


@csrf_exempt
def today_attendance(request):
    username = request.GET.get("username")
    if not username:
        return JsonResponse({"error": "Username is required"}, status=400)
        
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
        
    today = timezone.now().date()

    try:
        att = Attendance.objects.get(user=user, date=today)
        return JsonResponse({
            "check_in": att.check_in,
            "check_in_lat": att.check_in_lat,
            "check_in_lng": att.check_in_lng,
            "check_out": att.check_out,
            "check_out_lat": att.check_out_lat,
            "check_out_lng": att.check_out_lng,
        })
    except Attendance.DoesNotExist:
        return JsonResponse({"check_in": None, "check_out": None})

# ==========================================
#        SIMPLE ASSIGNED ITEMS (Member)
# ==========================================

class AssignedItemsSimpleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        worker = request.user
        items = AssignedItem.objects.filter(worker=worker)
        serializer = AssignedItemSerializer(items, many=True)
        return Response(serializer.data)

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
        members = User.objects.all().order_by('username')
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

        worker = log.worker
        item = log.item
        used = int(log.quantity_used)

        # 1. Get assigned item
        try:
            assigned = AssignedItem.objects.get(worker=worker, item=item)
        except AssignedItem.DoesNotExist:
            return Response({"error": "Assigned record not found"}, status=404)

        assigned_before = assigned.assigned_quantity
        stock_before = item.total_quantity

        # 2. Prevent negative assigned values
        if used > assigned_before:
            return Response({
                "error": "Used quantity cannot exceed assigned quantity",
                "assigned": assigned_before,
                "used": used
            }, status=400)

        # 3. Prevent negative stock
        if used > stock_before:
            return Response({
                "error": "Stock quantity too low",
                "stock": stock_before,
                "used": used
            }, status=400)

        # 4. Approve log
        log.is_approved = True
        log.save(update_fields=["is_approved"])

        # 5. Update assigned quantity
        assigned_after = assigned_before - used
        assigned.assigned_quantity = assigned_after
        assigned.save(update_fields=["assigned_quantity"])

        # 6. Update stock quantity
        stock_after = stock_before - used
        item.total_quantity = stock_after
        item.save(update_fields=["total_quantity"])

        print("\n=== APPROVE USAGE ===")
        print(f"Worker: {worker.username}")
        print(f"Item: {item.name}")
        print(f"Used: {used}")
        print(f"Assigned: {assigned_before} -> {assigned_after}")
        print(f"Stock: {stock_before} -> {stock_after}")
        print("=====================\n")

        return Response({
            "message": "Approved successfully",
            "assigned_after": assigned_after,
            "stock_after": stock_after
        })

class UsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = UsageLog.objects.filter(worker=request.user).order_by('-timestamp')
        return Response(UsageLogSerializer(logs, many=True).data)
