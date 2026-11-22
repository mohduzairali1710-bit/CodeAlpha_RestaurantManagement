from decimal import Decimal

from django.core.management.base import BaseCommand

from restaurant.models import InventoryItem, MenuItem, Recipe, Table


class Command(BaseCommand):
    help = "Create or update sample menu, inventory, recipes, and five tables."

    def handle(self, *args, **options):
        ingredients = {
            "Chicken": ("kg", "20.000", "3.000"),
            "Rice": ("kg", "15.000", "2.000"),
            "Lettuce": ("kg", "5.000", "1.000"),
            "Tomato": ("kg", "8.000", "1.000"),
            "Cheese": ("kg", "6.000", "1.000"),
        }
        inventory = {}
        for name, (unit, quantity, threshold) in ingredients.items():
            item, _ = InventoryItem.objects.update_or_create(
                name=name,
                defaults={
                    "unit": unit,
                    "quantity": Decimal(quantity),
                    "low_stock_threshold": Decimal(threshold),
                },
            )
            inventory[name] = item

        dishes = [
            ("Chicken Rice Bowl", "Grilled chicken served over rice.", "12.50", "Main", ["Chicken", "Rice"]),
            ("Garden Salad", "Fresh lettuce and tomato salad.", "8.00", "Starter", ["Lettuce", "Tomato"]),
            ("Cheese Chicken Wrap", "Chicken and cheese in a toasted wrap.", "10.75", "Main", ["Chicken", "Cheese"]),
        ]
        recipe_quantities = {
            "Chicken": Decimal("0.200"),
            "Rice": Decimal("0.150"),
            "Lettuce": Decimal("0.100"),
            "Tomato": Decimal("0.080"),
            "Cheese": Decimal("0.050"),
        }
        for name, description, price, category, recipe_ingredients in dishes:
            menu_item, _ = MenuItem.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "price": Decimal(price),
                    "category": category,
                    "is_available": True,
                },
            )
            for ingredient in recipe_ingredients:
                Recipe.objects.update_or_create(
                    menu_item=menu_item,
                    inventory_item=inventory[ingredient],
                    defaults={"quantity_needed": recipe_quantities[ingredient]},
                )

        for number, capacity in ((1, 2), (2, 2), (3, 4), (4, 4), (5, 6)):
            Table.objects.update_or_create(number=number, defaults={"capacity": capacity})

        self.stdout.write(self.style.SUCCESS("Sample restaurant data is ready."))
