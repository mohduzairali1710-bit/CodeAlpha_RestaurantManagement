from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import InventoryItem, MenuItem, Order, OrderItem, Recipe, Reservation


def reservation_overlaps(table, date, start_time, exclude_id=None):
    """Return whether a two-hour booking overlaps another active reservation."""
    requested_start = datetime.combine(date, start_time)
    requested_end = requested_start + timedelta(hours=2)
    nearby = Reservation.objects.filter(
        table=table,
        status=Reservation.Status.ACTIVE,
        date__range=(date - timedelta(days=1), date + timedelta(days=1)),
    )
    if exclude_id is not None:
        nearby = nearby.exclude(pk=exclude_id)

    for existing in nearby:
        existing_start = datetime.combine(existing.date, existing.start_time)
        existing_end = existing_start + timedelta(hours=2)
        if existing_start < requested_end and requested_start < existing_end:
            return True
    return False


def place_order(*, customer_name, table, requested_items):
    """Create an order and deduct all recipe ingredients as one atomic operation."""
    # Keep validation, order creation, and stock deduction atomic so failures roll back.
    with transaction.atomic():
        menu_items = {
            item.pk: item
            for item in MenuItem.objects.filter(
                pk__in=[line["menu_item_id"] for line in requested_items]
            )
        }
        missing_ids = sorted(
            {line["menu_item_id"] for line in requested_items} - set(menu_items)
        )
        if missing_ids:
            raise serializers.ValidationError(
                {"items": f"Menu item(s) not found: {', '.join(map(str, missing_ids))}."}
            )

        unavailable = [item.name for item in menu_items.values() if not item.is_available]
        if unavailable:
            raise serializers.ValidationError(
                {"items": f"Unavailable menu item(s): {', '.join(sorted(unavailable))}."}
            )

        total = sum(
            (menu_items[line["menu_item_id"]].price * line["quantity"] for line in requested_items),
            Decimal("0.00"),
        )
        ingredient_needs = {}
        for line in requested_items:
            for recipe in Recipe.objects.filter(menu_item_id=line["menu_item_id"]):
                ingredient_needs[recipe.inventory_item_id] = (
                    ingredient_needs.get(recipe.inventory_item_id, Decimal("0"))
                    + recipe.quantity_needed * line["quantity"]
                )

        inventory = {
            item.pk: item
            for item in InventoryItem.objects.select_for_update()
            .filter(pk__in=ingredient_needs)
            .order_by("pk")
        }
        shortages = []
        for item_id, needed in ingredient_needs.items():
            if item_id not in inventory:
                shortages.append(f"Inventory item {item_id} no longer exists")
            elif inventory[item_id].quantity < needed:
                item = inventory[item_id]
                shortages.append(f"{item.name} (need {needed}, have {item.quantity})")
        if shortages:
            raise serializers.ValidationError(
                {"inventory": f"Insufficient stock: {', '.join(shortages)}."}
            )

        order = Order.objects.create(
            table=table,
            customer_name=customer_name,
            total_amount=total,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    menu_item=menu_items[line["menu_item_id"]],
                    quantity=line["quantity"],
                    price=menu_items[line["menu_item_id"]].price,
                )
                for line in requested_items
            ]
        )
        for item_id, needed in ingredient_needs.items():
            inventory[item_id].quantity -= needed
            inventory[item_id].save(update_fields=["quantity"])
        return order


def cancel_order(order_id, new_status):
    """Update an order status and restore its ingredients only on first cancellation."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.status == Order.Status.CANCELLED and new_status != Order.Status.CANCELLED:
            raise serializers.ValidationError(
                {"status": "A cancelled order cannot be reopened."}
            )

        # Restore stock only on the transition into cancelled, not on repeated requests.
        if new_status == Order.Status.CANCELLED and order.status != Order.Status.CANCELLED:
            needs = {}
            for line in order.items.all():
                for recipe in Recipe.objects.filter(menu_item=line.menu_item):
                    needs[recipe.inventory_item_id] = (
                        needs.get(recipe.inventory_item_id, Decimal("0"))
                        + recipe.quantity_needed * line.quantity
                    )
            inventory = {
                item.pk: item
                for item in InventoryItem.objects.select_for_update()
                .filter(pk__in=needs)
                .order_by("pk")
            }
            for item_id, amount in needs.items():
                inventory[item_id].quantity += amount
                inventory[item_id].save(update_fields=["quantity"])

        order.status = new_status
        order.save(update_fields=["status"])
        return order
