# inventory/urls.py
from django.urls import path
from .views import (
    StockListView, StockDetailView,
    MembersListView, MemberDetailView, AssignItemView,
    AssignedItemsSimpleView,
    SubmitUsageView, PendingUsageView, ApproveUsageView, UsageHistoryView
)

urlpatterns = [
    # Stock
    path('stock/', StockListView.as_view()),
    path('stock/create/', StockDetailView.as_view()),
    path('stock/<int:item_id>/update/', StockDetailView.as_view()),
    path('stock/<int:item_id>/delete/', StockDetailView.as_view()),

    # Members
    path('members/', MembersListView.as_view()),
    path('members/<int:member_id>/', MemberDetailView.as_view()),
    path('assign/', AssignItemView.as_view(), name='assign_item'),

    # Member screens
    path('assigned-items/', AssignedItemsSimpleView.as_view()),
    path('submit-usage/', SubmitUsageView.as_view()),
    path('pending-usage/', PendingUsageView.as_view()),
    path('approve-usage/<int:log_id>/', ApproveUsageView.as_view()),
    path('history/', UsageHistoryView.as_view()),

    path("attendance/check-in/", views.check_in),
    path("attendance/check-out/", views.check_out),
    path("attendance/today/", views.today_attendance),
]
