from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from marketplace.models import Farm, Product, ProductCategory, UserProfile


class Command(BaseCommand):
    help = "Seed the marketplace with sample products for Vegetables, Fruits, and Meat."

    VEGETABLES = [
        ("Tomatoes", Decimal("120.00"), Decimal("150.00")),
        ("Potatoes", Decimal("90.00"), Decimal("200.00")),
        ("Carrots", Decimal("110.00"), Decimal("120.00")),
        ("Cucumbers", Decimal("80.00"), Decimal("120.00")),
        ("Onions", Decimal("70.00"), Decimal("180.00")),
        ("Garlic", Decimal("250.00"), Decimal("75.00")),
        ("Spinach", Decimal("95.00"), Decimal("60.00")),
        ("Lettuce", Decimal("85.00"), Decimal("50.00")),
        ("Cabbage", Decimal("100.00"), Decimal("90.00")),
        ("Eggplant", Decimal("115.00"), Decimal("95.00")),
        ("Zucchini", Decimal("105.00"), Decimal("88.00")),
        ("Bell Peppers", Decimal("160.00"), Decimal("72.00")),
        ("Pumpkins", Decimal("75.00"), Decimal("210.00")),
        ("Turnips", Decimal("68.00"), Decimal("140.00")),
        ("Peas", Decimal("145.00"), Decimal("66.00")),
        ("Broccoli", Decimal("180.00"), Decimal("55.00")),
        ("Cauliflower", Decimal("165.00"), Decimal("58.00")),
        ("Green Beans", Decimal("155.00"), Decimal("62.00")),
        ("Radishes", Decimal("78.00"), Decimal("84.00")),
        ("Sweet Potatoes", Decimal("130.00"), Decimal("150.00")),
        ("Celery", Decimal("98.00"), Decimal("64.00")),
        ("Leeks", Decimal("125.00"), Decimal("70.00")),
        ("Parsley", Decimal("60.00"), Decimal("48.00")),
        ("Beetroot", Decimal("88.00"), Decimal("76.00")),
        ("Okra", Decimal("175.00"), Decimal("52.00")),
    ]

    FRUITS = [
        ("Apples", Decimal("180.00"), Decimal("120.00")),
        ("Bananas", Decimal("140.00"), Decimal("80.00")),
        ("Oranges", Decimal("150.00"), Decimal("105.00")),
        ("Grapes", Decimal("200.00"), Decimal("82.00")),
        ("Strawberries", Decimal("340.00"), Decimal("34.00")),
        ("Pears", Decimal("175.00"), Decimal("76.00")),
        ("Peaches", Decimal("210.00"), Decimal("64.00")),
        ("Plums", Decimal("190.00"), Decimal("58.00")),
        ("Watermelons", Decimal("95.00"), Decimal("260.00")),
        ("Melons", Decimal("110.00"), Decimal("180.00")),
        ("Lemons", Decimal("130.00"), Decimal("74.00")),
        ("Mangoes", Decimal("320.00"), Decimal("46.00")),
        ("Pineapples", Decimal("280.00"), Decimal("40.00")),
        ("Kiwis", Decimal("260.00"), Decimal("52.00")),
        ("Pomegranates", Decimal("230.00"), Decimal("57.00")),
        ("Apricots", Decimal("205.00"), Decimal("49.00")),
        ("Cherries", Decimal("390.00"), Decimal("28.00")),
        ("Blueberries", Decimal("450.00"), Decimal("22.00")),
        ("Raspberries", Decimal("470.00"), Decimal("20.00")),
        ("Avocados", Decimal("310.00"), Decimal("36.00")),
        ("Papayas", Decimal("250.00"), Decimal("44.00")),
        ("Guavas", Decimal("220.00"), Decimal("51.00")),
        ("Tangerines", Decimal("160.00"), Decimal("86.00")),
        ("Dates", Decimal("350.00"), Decimal("60.00")),
        ("Figs", Decimal("270.00"), Decimal("42.00")),
    ]

    MEAT = [
        ("Chicken", Decimal("550.00"), Decimal("80.00")),
        ("Beef", Decimal("1200.00"), Decimal("55.00")),
        ("Lamb", Decimal("1450.00"), Decimal("40.00")),
        ("Turkey", Decimal("780.00"), Decimal("45.00")),
        ("Goat Meat", Decimal("1320.00"), Decimal("35.00")),
        ("Rabbit", Decimal("980.00"), Decimal("24.00")),
        ("Duck", Decimal("860.00"), Decimal("28.00")),
        ("Veal", Decimal("1380.00"), Decimal("32.00")),
        ("Mutton", Decimal("1490.00"), Decimal("25.00")),
        ("Beef Steak", Decimal("1650.00"), Decimal("30.00")),
        ("Chicken Wings", Decimal("620.00"), Decimal("38.00")),
        ("Chicken Breast", Decimal("690.00"), Decimal("44.00")),
        ("Ground Beef", Decimal("1180.00"), Decimal("34.00")),
        ("Lamb Chops", Decimal("1720.00"), Decimal("20.00")),
        ("Sausages", Decimal("840.00"), Decimal("27.00")),
        ("Turkey Breast", Decimal("930.00"), Decimal("26.00")),
        ("Goat Chops", Decimal("1410.00"), Decimal("22.00")),
        ("Drumsticks", Decimal("570.00"), Decimal("36.00")),
        ("Beef Ribs", Decimal("1360.00"), Decimal("18.00")),
        ("Liver", Decimal("760.00"), Decimal("21.00")),
        ("Minced Lamb", Decimal("1290.00"), Decimal("19.00")),
        ("Whole Chicken", Decimal("530.00"), Decimal("42.00")),
        ("Turkey Wings", Decimal("820.00"), Decimal("24.00")),
        ("Veal Cutlets", Decimal("1520.00"), Decimal("16.00")),
        ("Premium Beef Cubes", Decimal("1580.00"), Decimal("17.00")),
    ]

    IMAGE_MAP = {
        "Vegetables": "Screenshot_2026-04-21_165602.png",
        "Fruits": "5994600638488185887.jpg",
        "Meat": "c01f992cfe001354a1541a122c1a2bdd.jpg",
    }

    def handle(self, *args, **options):
        farmers = list(User.objects.filter(userprofile__user_type="farmer").order_by("id"))
        if not farmers:
            self.stdout.write(self.style.WARNING("No farmer users found. Creating demo farmers."))
            farmers = self._create_demo_farmers()

        farms = self._ensure_farms(farmers)
        created_total = 0

        created_total += self._seed_category("Vegetables", self.VEGETABLES, farmers, farms)
        created_total += self._seed_category("Fruits", self.FRUITS, farmers, farms)
        created_total += self._seed_category("Meat", self.MEAT, farmers, farms)

        self.stdout.write(self.style.SUCCESS(f"Catalog ready. Created {created_total} products."))

    def _create_demo_farmers(self):
        demo_users = []
        for username in ["farmer_alpha", "farmer_bravo", "farmer_charlie"]:
            user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
            if created:
                user.set_password("password123")
                user.is_active = True
                user.save()
            UserProfile.objects.get_or_create(user=user, defaults={"user_type": "farmer", "is_validated": True})
            demo_users.append(user)
        return demo_users

    def _ensure_farms(self, farmers):
        farms = {}
        for index, farmer in enumerate(farmers, start=1):
            farm = Farm.objects.filter(farmer=farmer).first()
            if not farm:
                farm = Farm.objects.create(
                    farmer=farmer,
                    name=f"{farmer.username.title()} Farm",
                    city="Algiers",
                    wilaya="Alger",
                    location="Regional farm zone",
                    area_hectares=Decimal("4.50") + Decimal(index),
                    description="Sample seeded farm for marketplace catalog products.",
                )
            farms[farmer.id] = farm
        return farms

    def _seed_category(self, category_name, items, farmers, farms):
        category, _ = ProductCategory.objects.get_or_create(name=category_name, defaults={"is_active": True})
        image_name = self.IMAGE_MAP[category_name]
        image_relative_path = f"products/{image_name}"
        created_count = 0

        for index, (name, price, quantity) in enumerate(items):
            farmer = farmers[index % len(farmers)]
            farm = farms[farmer.id]
            product, created = Product.objects.get_or_create(
                name=name,
                category=category,
                defaults={
                    "farmer": farmer,
                    "farm": farm,
                    "description": f"{name} supplied by {farmer.username} from {farm.name}. Fresh stock ready for buyers.",
                    "quantity": quantity,
                    "unit": "kg",
                    "price_per_unit": price,
                    "available": True,
                    "image": image_relative_path if self._image_exists(image_name) else "",
                },
            )
            if not created:
                changed = False
                if product.farmer_id != farmer.id:
                    product.farmer = farmer
                    changed = True
                if product.farm_id != farm.id:
                    product.farm = farm
                    changed = True
                if product.price_per_unit != price:
                    product.price_per_unit = price
                    changed = True
                if product.quantity != quantity:
                    product.quantity = quantity
                    changed = True
                if product.category_id != category.id:
                    product.category = category
                    changed = True
                if not product.description:
                    product.description = f"{name} supplied by {farmer.username} from {farm.name}. Fresh stock ready for buyers."
                    changed = True
                if not product.image and self._image_exists(image_name):
                    product.image = image_relative_path
                    changed = True
                if changed:
                    product.available = True
                    product.save()
            else:
                created_count += 1
        return created_count

    def _image_exists(self, image_name):
        media_path = Path("media") / "products" / image_name
        return media_path.exists()
