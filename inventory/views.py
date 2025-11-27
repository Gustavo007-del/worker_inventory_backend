from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from django.contrib.auth.models import User

from .models import InventoryItem, AssignedItem, UsageLog
from .serializers import AssignedItemSerializer, UsageLogSerializer


# ------------------------------
# GET ASSIGNED ITEMS (Worker)
# ------------------------------
class AssignedItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        worker = request.user
        items = AssignedItem.objects.filter(worker=worker)
        serializer = AssignedItemSerializer(items, many=True)
        return Response(serializer.data)


# ------------------------------
# SUBMIT USAGE WITH PHOTO (Worker)
# ------------------------------
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


# ------------------------------
# ADMIN APPROVAL
# ------------------------------
class ApproveUsageView(APIView):
    def post(self, request, log_id):
        try:
            log = UsageLog.objects.get(id=log_id)
        except:
            return Response({"error": "Log not found"}, status=404)

        log.is_approved = True
        log.save()

        # reduce inventory assigned quantity
        assigned = AssignedItem.objects.get(worker=log.worker, item=log.item)
        assigned.assigned_quantity -= int(log.quantity_used)
        assigned.save()

        return Response({"message": "Approved & Quantity Updated"})



# ------------------------------
# WORKER VIEW HISTORY
# ------------------------------
class UsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = UsageLog.objects.filter(worker=request.user).order_by('-timestamp')
        serializer = UsageLogSerializer(logs, many=True)
        return Response(serializer.data)
    
class PendingUsageView(APIView):
    def get(self, request):
        logs = UsageLog.objects.filter(is_approved=False).order_by('-timestamp')
        serializer = UsageLogSerializer(logs, many=True)
        return Response(serializer.data)

