from django.db import models


class MenuItem(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=80)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    name = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit = models.CharField(max_length=30)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="recipes")
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="recipes"
    )
    quantity_needed = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "inventory_item"], name="unique_recipe_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.menu_item} - {self.inventory_item}"


class Table(models.Model):
    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return f"Table {self.number} (capacity {self.capacity})"


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name="reservations")
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    date = models.DateField()
    start_time = models.TimeField()
    party_size = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    def __str__(self):
        return f"{self.customer_name} - table {self.table.number} on {self.date}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PREPARING = "preparing", "Preparing"
        SERVED = "served", "Served"
        CANCELLED = "cancelled", "Cancelled"

    table = models.ForeignKey(
        Table, on_delete=models.SET_NULL, related_name="orders", null=True, blank=True
    )
    customer_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.pk} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item}"
