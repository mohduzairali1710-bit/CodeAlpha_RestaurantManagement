from django.contrib import admin

from .models import InventoryItem, MenuItem, Order, OrderItem, Recipe, Reservation, Table


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available")
    search_fields = ("name",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "unit", "low_stock_threshold")
    search_fields = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "inventory_item", "quantity_needed")
    list_filter = ("menu_item",)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("number", "capacity")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "table", "date", "start_time", "party_size", "status")
    list_filter = ("status", "date")
    search_fields = ("customer_name", "phone")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "table", "status", "total_amount", "created_at")
    list_filter = ("status", "created_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "menu_item", "quantity", "price")
