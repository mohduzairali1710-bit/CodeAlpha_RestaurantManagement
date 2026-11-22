from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import InventoryItem, MenuItem, Order, Recipe, Reservation, Table


class RestaurantAPITests(APITestCase):
    def setUp(self):
        self.menu_item = MenuItem.objects.create(
            name="Soup",
            description="Daily soup",
            price=Decimal("8.50"),
            category="Starter",
        )
        self.inventory_item = InventoryItem.objects.create(
            name="Stock",
            quantity=Decimal("5.000"),
            unit="litre",
            low_stock_threshold=Decimal("1.000"),
        )
        Recipe.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.inventory_item,
            quantity_needed=Decimal("0.500"),
        )
        self.table = Table.objects.create(number=1, capacity=4)

    def _order_payload(self, quantity=2):
        return {
            "customer_name": "Alex",
            "items": [{"menu_item": self.menu_item.pk, "quantity": quantity}],
        }

    def test_order_deducts_recipe_inventory_and_calculates_total(self):
        response = self.client.post("/api/orders/", self._order_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("17.00"))
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.quantity, Decimal("4.000"))

    def test_order_with_insufficient_stock_changes_nothing(self):
        self.inventory_item.quantity = Decimal("0.500")
        self.inventory_item.save()

        response = self.client.post("/api/orders/", self._order_payload(quantity=2), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.quantity, Decimal("0.500"))

    def test_cancelling_order_restores_inventory_once(self):
        order_response = self.client.post("/api/orders/", self._order_payload(), format="json")
        self.assertEqual(order_response.status_code, 201)
        order_id = order_response.data["id"]
        staff = get_user_model().objects.create_user(
            username="canceller", password="test-pass", is_staff=True
        )
        self.client.force_authenticate(user=staff)

        first_cancel = self.client.patch(
            f"/api/orders/{order_id}/status/", {"status": "cancelled"}, format="json"
        )
        second_cancel = self.client.patch(
            f"/api/orders/{order_id}/status/", {"status": "cancelled"}, format="json"
        )

        self.assertEqual(first_cancel.status_code, 200)
        self.assertEqual(second_cancel.status_code, 200)
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.quantity, Decimal("5.000"))

    def test_overlapping_table_reservation_is_rejected(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="Sam",
            phone="5550100",
            date=date(2026, 12, 1),
            start_time=time(19, 0),
            party_size=2,
        )

        response = self.client.post(
            "/api/reservations/",
            {
                "table": self.table.pk,
                "customer_name": "Taylor",
                "phone": "5550101",
                "date": "2026-12-01",
                "start_time": "20:30",
                "party_size": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_low_stock_report_returns_items_below_threshold_to_staff(self):
        self.inventory_item.quantity = Decimal("0.250")
        self.inventory_item.save()
        staff = get_user_model().objects.create_user(
            username="manager", password="test-pass", is_staff=True
        )
        self.client.force_authenticate(user=staff)

        response = self.client.get("/api/reports/low-stock/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.inventory_item.pk])

    def test_registration_creates_customer_and_returns_token(self):
        response = self.client.post(
            "/api/register-user/",
            {"username": "new-customer", "password": "StrongPass!927"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])
        user = get_user_model().objects.get(username="new-customer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("StrongPass!927"))

    def test_login_returns_token_and_rejects_bad_credentials(self):
        user = get_user_model().objects.create_user(
            username="existing-customer", password="StrongPass!927"
        )

        response = self.client.post(
            "/api/login/",
            {"username": user.username, "password": "StrongPass!927"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["token"])

        failed_response = self.client.post(
            "/api/login/",
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(failed_response.status_code, 401)
