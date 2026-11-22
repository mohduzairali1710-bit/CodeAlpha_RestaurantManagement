from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    InventoryItem,
    MenuItem,
    Order,
    OrderItem,
    Reservation,
    Table,
)
from .services import place_order


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ("id", "name", "description", "price", "category", "is_available")


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ("id", "number", "capacity")


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "menu_item", "menu_item_name", "quantity", "price")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "table",
            "customer_name",
            "status",
            "total_amount",
            "created_at",
            "items",
        )


class OrderLineInputSerializer(serializers.Serializer):
    menu_item = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.all(), required=False, allow_null=True
    )
    customer_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    items = OrderLineInputSerializer(many=True, allow_empty=False)

    def create(self, validated_data):
        lines = [
            {"menu_item_id": line["menu_item"], "quantity": line["quantity"]}
            for line in validated_data["items"]
        ]
        return place_order(
            customer_name=validated_data.get("customer_name", ""),
            table=validated_data.get("table"),
            requested_items=lines,
        )


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ("id", "name", "quantity", "unit", "low_stock_threshold")


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = (
            "id",
            "table",
            "customer_name",
            "phone",
            "date",
            "start_time",
            "party_size",
            "status",
        )
        read_only_fields = ("status",)


class ReservationCreateSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all())
    customer_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=30)
    date = serializers.DateField()
    start_time = serializers.TimeField()
    party_size = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["party_size"] > attrs["table"].capacity:
            raise serializers.ValidationError(
                {"party_size": "Party size exceeds the table capacity."}
            )
        return attrs

    def create(self, validated_data):
        return Reservation.objects.create(**validated_data)


class TableAvailabilityQuerySerializer(serializers.Serializer):
    date = serializers.DateField()
    time = serializers.TimeField()
    party_size = serializers.IntegerField(min_value=1)


class RegisterUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, attrs):
        user = get_user_model()(username=attrs["username"])
        try:
            password_validation.validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
