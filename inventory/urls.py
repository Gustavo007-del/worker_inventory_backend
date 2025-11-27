from django.urls import path
from .views import AssignedItemsView, SubmitUsageView, ApproveUsageView, UsageHistoryView
from .views import PendingUsageView, ApproveUsageView


urlpatterns = [
    path("pending-usage/", PendingUsageView.as_view()),
    path("approve-usage/<int:log_id>/", ApproveUsageView.as_view()),
    path('assigned-items/', AssignedItemsView.as_view()),
    path('submit-usage/', SubmitUsageView.as_view()),
    path('approve/<int:log_id>/', ApproveUsageView.as_view()),
    path('history/', UsageHistoryView.as_view()),
]
