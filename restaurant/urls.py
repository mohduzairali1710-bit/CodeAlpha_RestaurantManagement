from django.urls import path

from .views import (
    AvailableTableListView,
    DailySalesReportView,
    InventoryDetailView,
    InventoryListView,
    LoginView,
    LowStockReportView,
    MenuListView,
    OrderDetailView,
    OrderListCreateView,
    OrderStatusView,
    ReservationDeleteView,
    ReservationListCreateView,
    RegisterUserView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="api-login"),
    path("register-user/", RegisterUserView.as_view(), name="api-register-user"),
    path("menu/", MenuListView.as_view(), name="menu-list"),
    path("orders/", OrderListCreateView.as_view(), name="order-list-create"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/status/", OrderStatusView.as_view(), name="order-status"),
    path("tables/available/", AvailableTableListView.as_view(), name="table-availability"),
    path("reservations/", ReservationListCreateView.as_view(), name="reservation-create"),
    path(
        "reservations/<int:pk>/",
        ReservationDeleteView.as_view(),
        name="reservation-delete",
    ),
    path("inventory/", InventoryListView.as_view(), name="inventory-list"),
    path("inventory/<int:pk>/", InventoryDetailView.as_view(), name="inventory-detail"),
    path("reports/daily-sales/", DailySalesReportView.as_view(), name="daily-sales-report"),
    path("reports/low-stock/", LowStockReportView.as_view(), name="low-stock-report"),
]
