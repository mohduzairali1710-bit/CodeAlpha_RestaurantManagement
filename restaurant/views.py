from datetime import datetime, timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InventoryItem, MenuItem, Order, Reservation, Table
from .permissions import IsStaffUser
from .serializers import (
    InventoryItemSerializer,
    LoginSerializer,
    MenuItemSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
    RegisterUserSerializer,
    TableAvailabilityQuerySerializer,
    TableSerializer,
)
from .services import cancel_order, reservation_overlaps


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class RegisterUserView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "user": {"id": user.pk, "username": user.username}},
            status=status.HTTP_201_CREATED,
        )


class MenuListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MenuItemSerializer
    queryset = MenuItem.objects.filter(is_available=True).order_by("category", "name")


class OrderListCreateView(APIView):
    def get_permissions(self):
        return [IsStaffUser()] if self.request.method == "GET" else [AllowAny()]

    def get(self, request):
        orders = Order.objects.prefetch_related("items__menu_item").order_by("-created_at")
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = OrderSerializer
    queryset = Order.objects.prefetch_related("items__menu_item")


class OrderStatusView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, pk):
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        get_object_or_404(Order, pk=pk)
        order = cancel_order(pk, serializer.validated_data["status"])
        return Response(OrderSerializer(order).data)


class AvailableTableListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = TableAvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        date = query.validated_data["date"]
        start_time = query.validated_data["time"]
        party_size = query.validated_data["party_size"]
        tables = Table.objects.filter(capacity__gte=party_size).order_by("number")
        available = [
            table
            for table in tables
            if not reservation_overlaps(table, date, start_time)
        ]
        return Response(TableSerializer(available, many=True).data)


class ReservationListCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            if reservation_overlaps(
                data["table"], data["date"], data["start_time"]
            ):
                return Response(
                    {"detail": "The table is already reserved during that time."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            reservation = serializer.save()
        return Response(
            ReservationSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )


class ReservationDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        if reservation.status != Reservation.Status.CANCELLED:
            reservation.status = Reservation.Status.CANCELLED
            reservation.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryListView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.order_by("name")


class InventoryDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()
    http_method_names = ["patch", "options"]


class DailySalesReportView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        date_value = request.query_params.get("date")
        if not date_value:
            return Response(
                {"date": "This query parameter is required (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            date = datetime.strptime(date_value, "%Y-%m-%d").date()
            if date.isoformat() != date_value:
                raise ValueError
        except ValueError:
            return Response(
                {"date": "Enter a valid date in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end = start + timedelta(days=1)
        sales = Order.objects.filter(
            created_at__gte=start, created_at__lt=end
        ).exclude(status=Order.Status.CANCELLED)
        summary = sales.aggregate(total_sales=Sum("total_amount"), order_count=Count("id"))
        return Response(
            {
                "date": date.isoformat(),
                "total_sales": summary["total_sales"] or 0,
                "number_of_orders": summary["order_count"],
            }
        )


class LowStockReportView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.filter(
        quantity__lt=F("low_stock_threshold")
    ).order_by("name")
