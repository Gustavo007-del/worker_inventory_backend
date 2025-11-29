# E:\study\worker_inventory\worker_inventory_backend\inventory\urls.py
from django.urls import path
from .views import (
    # Stock Management
    StockListView, StockDetailView, SearchStockView,
    # Member Management
    MembersListView, MemberDetailView, MemberProfileView,
    # Assigned Items
    AssignedItemsView,
    # Usage/Approvals
    SubmitUsageView, PendingUsageView, ApproveUsageView, UsageHistoryView,
    # Courier
    CreateCourierView, SendCourierView, WorkerCourierView, ReceiveCourierView,
    AdminCourierApprovalsView, RejectCourierView,
    # Location
    SaveLocationView, WorkerLocationsView
)

urlpatterns = [
    # ========== STOCK ==========
    path('stock/', StockListView.as_view(), name='stock_list'),
    path('stock/create/', StockDetailView.as_view(), name='stock_create'),
    path('stock/<int:item_id>/update/', StockDetailView.as_view(), name='stock_update'),
    path('stock/<int:item_id>/delete/', StockDetailView.as_view(), name='stock_delete'),
    path('stock/search/', SearchStockView.as_view(), name='stock_search'),

    # ========== MEMBERS ==========
    path('members/', MembersListView.as_view(), name='members_list'),
    path('members/<int:member_id>/', MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:member_id>/update/', MemberDetailView.as_view(), name='member_update'),
    path('profile/', MemberProfileView.as_view(), name='member_profile'),

    # ========== ASSIGNED ITEMS ==========
    path('assigned-items/', AssignedItemsView.as_view()),

    # ========== USAGE / EDIT ITEMS ==========
    path('submit-usage/', SubmitUsageView.as_view()),
    path('pending-usage/', PendingUsageView.as_view()),
    path('approve-usage/<int:log_id>/', ApproveUsageView.as_view()),
    path('history/', UsageHistoryView.as_view()),

    # ========== COURIER ==========
    path('courier/create/', CreateCourierView.as_view(), name='courier_create'),
    path('courier/<int:shipment_id>/send/', SendCourierView.as_view(), name='courier_send'),
    path('courier/received/', WorkerCourierView.as_view(), name='courier_received'),
    path('courier/<int:shipment_id>/receive/', ReceiveCourierView.as_view(), name='courier_receive'),
    path('courier/approvals/', AdminCourierApprovalsView.as_view(), name='courier_approvals'),
    path('courier/<int:shipment_id>/approve/', AdminCourierApprovalsView.as_view(), name='courier_approve'),
    path('courier/<int:shipment_id>/reject/', RejectCourierView.as_view(), name='courier_reject'),

    # ========== LOCATION ==========
    path('location/save/', SaveLocationView.as_view(), name='save_location'),
    path('locations/', WorkerLocationsView.as_view(), name='worker_locations'),
]
