from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from backend.auth import hash_password
from backend.import_view import import_pricelist
from backend.models import (Category, Client, ConfirmEmailToken, Contact,
                            Order, Product, ProductInfo, Shop)


class ProfileTests(APITestCase):
    def test_create_profile(self):
        """
        Создадим новый профиль
        """
        data = {
            "first_name": "Andrey",
            "last_name": "Minin",
            "username": "MininAndrey",
            "email": "MininComp@gmail.com",
            "company": "MininCom",
            "position": "Director",
            "password": "tguthguf444",
        }
        response = self.client.post(reverse("profile"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Client.objects.get().username, data["username"])

    def test_change_profile(self):
        """
        Проведем изменения в профиле
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
        )
        data = {"first_name": "AndreyChange", "last_name": "MininChange"}
        self.client.force_authenticate(client)
        response = self.client.patch(reverse("profile"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.get().first_name, data["first_name"])
        self.assertEqual(Client.objects.get().last_name, data["last_name"])

    def test_get_profile(self):
        """
        Полученим и сравним данные профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
        )
        self.client.force_authenticate(client)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], client.first_name)
        self.assertEqual(response.json()["username"], client.username)
        self.assertEqual(response.json()["email"], client.email)

    def test_delete_profile(self):
        """
        Полученим и сравним данные профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(client)
        self.assertEqual(Client.objects.count(), 1)
        response = self.client.delete(
            reverse("profile"), data={"password": "tguthguf444"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Client.objects.count(), 0)


class ProfileContactsTests(APITestCase):
    def test_get_contacts(self):
        """
        Просмотрим контакты профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(client)
        response = self.client.get(reverse("contacts"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(response.json()["Error"], "Контакты профиля не найдены")

    def test_post_contacts(self):
        """
        Укажем контакты профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        data = {
            "city": "Moskow",
            "street": "Miraaaa",
            "house": "3555",
            "phone": "8824244419",
        }
        self.client.force_authenticate(client)
        response = self.client.post(reverse("contacts"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(response.json()["Info"], "Данные внесены")

    def test_patch_contacts(self):
        """
        Внесем изменения в контакты профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        data = {"city": "ChangeCountry"}
        self.client.force_authenticate(client)
        Contact.objects.create(
            client=client, city="Moskow", street="Miraaaa", house=3555, phone=8824244419
        )
        response = self.client.patch(reverse("contacts"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(response.json()["Info"], "Изменения внесены")
        self.assertEqual(Contact.objects.get().city, data["city"])


class LoginTests(APITestCase):
    def test_login_profile(self):
        """
        Проведем аутентификацию созданного профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        data = {"email": "MininComp@gmail.com", "password": "tguthguf444"}
        response = self.client.post(reverse("login"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["Info"], "Аутентификация прошла успешно")
        self.assertEqual(Token.objects.count(), 1)
        self.assertEqual(
            response.json()["Token"], Token.objects.get(user=client.id).key
        )

    def test_logout_profile(self):
        """
        Проведем деаутентификация созданного профиля
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        data = {"email": "MininComp@gmail.com", "password": "tguthguf444"}
        response = self.client.post(reverse("login"), data, format="json")
        self.assertEqual(Token.objects.count(), 1)
        response = self.client.get(
            reverse("logout"),
            headers={"Authorization": f'Token {response.json()["Token"]}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Token.objects.count(), 0)


class EmailTests(APITestCase):
    def test_get_email(self):
        """
        Повторим отправку токена подтверждения на электронную почту
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
        )
        self.client.force_authenticate(client)
        self.assertEqual(ConfirmEmailToken.objects.count(), 0)
        response = self.client.get(reverse("email"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["Info"], "Письмо отправлено на Вашу электронную почту"
        )

    def test_post_email(self):
        """
        Проверим подтвеждение токеном электронной почты
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
        )
        self.client.force_authenticate(client)
        confirm_email = ConfirmEmailToken.objects.create(
            client=client, key="bhirthbhgu45788745hbbrhfbvh"
        )
        data = {"email": f"{client.email}", "token": f"{confirm_email.key}"}
        response = self.client.post(reverse("email"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["Info"], "Почта подтверждена")


class ProfileShopTests(APITestCase):
    def setUp(self):
        self.profile = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey",
            email="MininComp@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(self.profile)

    def test_get_shop(self):
        """
        Узнать данные профиля магазина
        """
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Shop.objects.count(), 0)
        self.assertEqual(response.json()["Error"], "Магазин не создан")
        self.assertEqual(Client.objects.get().type, "buyer")

    def test_create_shop(self):
        """
        Создадим новый профиль магазина
        """
        data = {"name": "MoskowShop"}
        response = self.client.post(reverse("shop"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shop.objects.count(), 1)
        self.assertEqual(Shop.objects.get().name, data["name"])
        self.assertEqual(Client.objects.get().type, "shop")

    def test_patch_shop(self):
        """
        Изменим данные профиля магазина
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        data = {"url": "https://ru.stackoverflow.com/"}
        Shop.objects.create(name="MoskowShop", client=client)
        response = self.client.patch(reverse("shop"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shop.objects.get().url, data["url"])

    def test_state_shop(self):
        """
        Изменим статус профиля магазина
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        Shop.objects.create(name="MoskowShop", client=client)
        response = self.client.get(reverse("state"))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shop.objects.get().state, False)


class ShopPricelistTests(APITestCase):
    def test_get_pricelist(self):
        """
        Просмотрим список выставленных товаров
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        Shop.objects.create(name="MoskowShop", client=client)
        response = self.client.get(reverse("pricelist"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["Error"], "Товары не найдены")
        self.assertEqual(ProductInfo.objects.count(), 0)

    def test_post_pricelist(self):
        """
        Выставим список товаров
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        shop = Shop.objects.create(name="MoskowShop", client=client)
        data = {
            "categories": [
                {"id": 224, "name": "Смартфоны"},
                {"id": 15, "name": "Аксессуары"},
                {"id": 1, "name": "Flash-накопители"},
            ],
            "goods": [
                {
                    "id": 4216292,
                    "category": 224,
                    "model": "apple/iphone/xs-max",
                    "name": "Смартфон Apple iPhone XS Max 512GB (золотистый)",
                    "price": 110000,
                    "price_rrc": 116990,
                    "quantity": 14,
                    "parameters": {
                        "Диагональ (дюйм)": 6.5,
                        "Разрешение (пикс)": "2688x1242",
                        "Встроенная память (Гб)": 512,
                        "Цвет": "золотистый",
                    },
                }
            ],
        }
        response = self.client.post(reverse("pricelist"), data=data, format="json")
        response_import = import_pricelist(data, shop.id)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.json()["Info"],
            "Список товаров отправлен на загрузку. Ожидайте сообщения на электронную почту",
        )
        self.assertEqual(response_import, True)
        self.assertEqual(ProductInfo.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 3)

    def test_delete_pricelist(self):
        """
        Просмотрим список выставленных товаров
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        Shop.objects.create(name="MoskowShop", client=client)
        response = self.client.delete(
            reverse("pricelist"), data={"password": "tguthguf444"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BasketTests(APITestCase):
    def test_get_basket(self):
        """
        Просмотрим содержимое корзины
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(client)
        response = self.client.get(reverse("basket"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(response.json()["Info"], "Ваша корзина пуста")

    def test_post_basket(self):
        """
        Добавим в содержимое корзины
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(client)
        shop = Shop.objects.create(name="MoskowShop", client=client)
        category = Category.objects.create(id=224, name="Смартфоны")
        product = Product.objects.create(
            name="Смартфон Apple iPhone XS Max 512GB (золотистый)", category=category
        )
        product_info = ProductInfo.objects.create(
            product=product,
            shop=shop,
            external_id=234,
            model="apple/iphone/xs-max",
            price=110000,
            price_rrc=116990,
            quantity=14,
        )
        response = self.client.post(
            reverse("basket"),
            data={"items": [{"product_info": 1, "quantity": 7}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(response.json()["Info"], "Создано объектов - 1")


class OrdersTests(APITestCase):
    def test_get_order(self):
        """
        Просмотрим выставленные заказы покупателя
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
        )
        self.client.force_authenticate(client)
        response = self.client.get(reverse("buy"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(response.json()["Info"], "Вы еще не успели сделать заказ")

    def test_get_order_shop(self):
        """
        Просмотрим выставленные заказы для магазина
        """
        client = Client.objects.create(
            first_name="Andrey",
            last_name="Minin",
            username="MininAndrey1",
            email="MininComp1@gmail.com",
            company="MininCom",
            position="Director",
            password=hash_password("tguthguf444"),
            is_active=True,
            type="shop",
        )
        self.client.force_authenticate(client)
        Shop.objects.create(name="MoskowShop", client=client)
        response = self.client.get(reverse("orders"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(response.json()["Info"], "Заказов нет")
