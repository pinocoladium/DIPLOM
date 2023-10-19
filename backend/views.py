import datetime

from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.db.models import F, Q, Sum
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from backend.auth import check_password, generate_password, hash_password
from backend.models import (Category, Client, ConfirmEmailToken, Contact,
                            Order, OrderItem, ProductInfo, Shop)
from backend.serializers import (CategorySerializer, ClientSerializer,
                                 ContactsSerializer, OrderItemSerializer,
                                 OrderSerializer, ProductInfoSerializer,
                                 ShopAllSerializer, ShopSerializer)
from backend.tasks import celery_send_note, celery_import_pricelist


class ProfileClient(APIView):
    """
    Для управления профилем пользователя сервиса
    """

    # узнать данные профиля пользователя
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                ClientSerializer(Client.objects.get(id=request.user.id)).data
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # зарегистрировать нового пользователя
    def post(self, request, *args, **kwargs):
        if {"first_name", "last_name", "email"}.issubset(request.data):
            if "type" in request.data.keys() and request.data["type"] == "shop":
                return Response(
                    {"Status": False, "Errors": "Создание магазина сейчас недоступно"}
                )
            if "is_active" in request.data.keys():
                request.data["is_active"] = False
            if "password" not in request.data.keys():
                password = generate_password()
            hashed_password = hash_password(password)
            client_serializer = ClientSerializer(data=request.data)
            if client_serializer.is_valid():
                try:
                    client = client_serializer.save()
                except IntegrityError as error:
                    return Response({"Status": False, "Errors": str(error)})
                else:
                    Client.objects.filter(id=client.id).update(password=hashed_password)
                    celery_send_note.delay("email_confirmation", (client.email, client.id))
                    return Response(
                        {"status": True, "email": client.email, "password": password}
                    )
            return Response({"Status": False, "Errors": client_serializer.errors})
        return Response(
            {"Status": False, "Errors": "Не указаны все необходимые данные"}
        )

    # измененить данные профиля пользователя
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            client = Client.objects.get(id=request.user.id)
            if "email" in request.data.keys() and request.data["email"] != client.email:
                celery_send_note.delay(
                    "email_confirmation", (request.data["email"], client.id)
                )
                request.data["is_active"] = False
            if "is_active" in request.data.keys():
                request.data["is_active"] = client.is_active
            if "type" in request.data.keys():
                request.data["type"] = client.type
            client_serializer = ClientSerializer(
                client, data=request.data, partial=True
            )
            if client_serializer.is_valid():
                try:
                    client_serializer.save()
                except IntegrityError as error:
                    return Response({"Status": False, "Errors": str(error)})
                else:
                    return Response({"Status": True, "info": "Изменения внесены"})
            return Response({"Status": False, "Errors": client_serializer.errors})
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # удалить профиль
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if (
                    request.data
                    and "password" in request.data.keys()
                    and request.data["password"]
                ):
                    if check_password(request.data["password"], request.user.password):
                        celery_send_note.delay(
                            "notific_delete_profile",
                            (request.user.email, request.user.username),
                        )
                        Client.objects.filter(id=request.user.id).delete()
                        return Response({"Status": True, "info": "Профиль удален"})
                    return Response({"Status": False, "Error": "Неверный пароль"})
                return Response(
                    {
                        "Status": False,
                        "Errors": "Не указаны все необходимые данные (password)",
                    }
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


class ConfirmEmail(APIView):
    """
    Для подтверждения адреса электронной почты
    """

    # повторить отправку токена подтверждения на электронную почту
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == False:
                celery_send_note.delay(
                    "email_confirmation", (request.user.email, request.user.id)
                )
                return Response(
                    {
                        "Status": True,
                        "Info": "Письмо отправлено на Вашу электронную почту",
                    }
                )
            return Response({"Status": False, "Error": "Почта уже подтверждена"})
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # подтвердить токеном электронную почту
    def post(self, request, *args, **kwargs):
        if "token" in request.data.keys() and request.data["token"]:
            client = Client.objects.get(email=request.data["email"])
            if client.is_active == False:
                token = ConfirmEmailToken.objects.get(client=client)
                if (
                    token.created_at + datetime.timedelta(hours=24)
                    <= datetime.datetime.now()
                ):
                    celery_send_note.delay(
                        "email_confirmation", (request.data["email"], client.id)
                    )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Устаревший токен. На электронную почту отправлен другой",
                        }
                    )
                if request.data["token"] == token.key:
                    Client.objects.filter(id=client.id).update(is_active=True)
                    return Response({"Status": True, "Info": "Почта подтверждена"})
                return Response({"Status": False, "Error": "Указанные неверные данные"})
            return Response({"Status": False, "Error": "Почта уже подтверждена"})
        return Response({"Status": False, "Error": "Не указан данные в запросе"})


class ProfilContacts(APIView):
    """
    Для работы с контактами профиля
    """

    # узнать контакты профиля
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                contact = Contact.objects.filter(client=request.user.id)
                if contact:
                    return Response(ContactsSerializer(contact[0]).data)
                return Response(
                    {
                        "Status": False,
                        "Error": "Контакты профиля не найдены",
                    }
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # указать контакты профиля
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if {"city", "street", "house", "phone"}.issubset(request.data):
                    request.data["client"] = request.user.id
                    contacts_serializers = ContactsSerializer(data=request.data)
                    if contacts_serializers.is_valid():
                        try:
                            contacts_serializers.save()
                        except IntegrityError as error:
                            return Response({"Status": False, "Errors": str(error)})
                        else:
                            return Response({"Status": True, "Info": "Данные внесены"})
                    return Response(
                        {"Status": False, "Errors": contacts_serializers.errors}
                    )
                return Response(
                    {
                        "Status": False,
                        "Errors": "Не указаны все необходимые данные (city, street, house, phone)",
                    }
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # внести изменения в контакты профиля
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                contact = Contact.objects.filter(client=request.user.id)
                if contact:
                    contacts_serializers = ContactsSerializer(
                        contact[0], data=request.data, partial=True
                    )
                    if contacts_serializers.is_valid():
                        try:
                            contacts_serializers.save()
                        except IntegrityError as error:
                            return Response({"Status": False, "Errors": str(error)})
                        else:
                            return Response(
                                {"Status": True, "Info": "Изменения внесены"}
                            )
                    return Response(
                        {"Status": False, "Errors": contacts_serializers.errors}
                    )
                return Response(
                    {"Status": False, "Error": "Контакты профиля не найдены"}
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # удалить контакты профиля
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                Contact.objects.filter(client=request.user.id).delete()
                return Response({"Status": True, "Info": "Контакты профиля удалены"})
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


# сброс пароля
@api_view(["POST"])
def reset_password_view(request, *args, **kwargs):
    if request.data:
        if Client.objects.filter(**request.data):
            celery_send_note.delay(
                "reset_password_created", (Client.objects.get(**request.data).id)
            )
            return Response(
                {
                    "Status": True,
                    "Info": "Пароль для входа отправлен на электронную почту",
                }
            )
        return Response({"status": False, "Error": "Аккаунт не найден"})
    return Response(
        {
            "status": False,
            "Error": "Необходимо указать какие-нибудь данные о профиле (username, email)",
        }
    )


class LoginClient(APIView):
    """
    Для аутентификации зарегистрированного пользователя сервиса
    """

    # узнать статус аутентификации
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"Status": True, "Info": "Вы прошли аутентификацию"})
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # аутентификация пользователя
    def post(self, request, *args, **kwargs):
        client = authenticate(
            request=request,
            email=request.data["email"],
            password=request.data["password"],
        )
        if client is not None:
            token = Token.objects.get_or_create(user=client)
            return Response(
                {
                    "Status": True,
                    "Info": "Аутентификация прошла успешно",
                    "Token": str(token[0]),
                }
            )
        return Response({"status": False, "Error": "Неверно введен логин или пароль"})


# деаутентификация
@api_view(["GET"])
def logout_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        Token.objects.filter(user=Client.objects.get(id=request.user.id)).delete()
        return Response({"status": True, "info": "Деаутентификация прошла успешно"})
    return Response({"status": False, "Error": "Вы не проходили аутентификацию"})


class ProfileShop(APIView):
    """
    Для управления профилем магазина сервиса
    """

    # узнать данные профиля магазина
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    return Response(
                        ShopSerializer(Shop.objects.get(client=request.user.id)).data
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    }
                )
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # зарегистрировать новый магазин
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active:
                if request.user.type == "buyer":
                    if {"name"}.issubset(request.data):
                        request.data["client"] = request.user.id
                        shop_serializer = ShopSerializer(data=request.data)
                        if shop_serializer.is_valid():
                            try:
                                shop = shop_serializer.save()
                            except IntegrityError as error:
                                return Response({"Status": False, "Errors": str(error)})
                            else:
                                Client.objects.filter(id=request.user.id).update(
                                    type="shop"
                                )
                                return Response(
                                    {
                                        "status": True,
                                        "name shop": shop.name,
                                        "state": shop.state,
                                    }
                                )
                        return Response(
                            {"Status": False, "Errors": shop_serializer.errors}
                        )
                    return Response(
                        {
                            "Status": False,
                            "Errors": "Не указаны все необходимые данные (name)",
                        }
                    )
                return Response(
                    {
                        "Status": False,
                        "Errors": "Нельзя создать более 1 магазина на аккаунт",
                    }
                )
            return Response(
                {
                    "Status": False,
                    "Errors": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # измененить данные профиля магазина
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    shop = Shop.objects.get(client=request.user.id)
                    shop_serializer = ShopSerializer(
                        shop, data=request.data, partial=True
                    )
                    if shop_serializer.is_valid():
                        try:
                            shop_serializer.save()
                        except IntegrityError as error:
                            return Response({"Status": False, "Errors": str(error)})
                        else:
                            return Response(
                                {"Status": True, "Info": "Изменения внесены"}
                            )
                    return Response({"Status": False, "Errors": shop_serializer.errors})
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    }
                )
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)

    # удалить профиль магазина
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    if (
                        request.data
                        and "password" in request.data.keys()
                        and request.data["password"]
                    ):
                        if check_password(
                            request.data["password"], request.user.password
                        ):
                            Shop.objects.filter(client=request.user.id).delete()
                            Client.objects.filter(id=request.user.id).update(
                                type="buyer"
                            )
                            return Response({"Status": True, "Info": "Магазин удален"})
                        return Response({"Status": False, "Error": "Неверный пароль"})
                    return Response(
                        {
                            "Status": False,
                            "Error": "Не указаны все необходимые данные (password)",
                        }
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    }
                )
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)


# изменения статуса приема заказов (только для продавцов)
@api_view(["GET"])
def state_change_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        if request.user.type == "shop":
            if request.user.is_active == True:
                shop = Shop.objects.filter(client=request.user.id)
                if shop[0].state:
                    shop.update(state=False)
                    return Response(
                        {
                            "Status": True,
                            "Info": "Статус - неактивен",
                        }
                    )
                shop.update(state=True)
                return Response(
                    {
                        "Status": True,
                        "Info": "Статус - активен",
                    }
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response({"Status": False, "Error": "Только для магазинов"})
    return Response(
        {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
    )


class ShopPricelist(APIView):
    """
    Для просмотра собственного и загрузки списка товаров (только для продавцов)
    """

    # просмотр списка выставленных товаров (только для продавцов)
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                shop = Shop.objects.get(client=request.user.id)
                if shop.state == True:
                    product_all = ProductInfo.objects.filter(shop=shop.id)
                    if product_all:
                        serializer = ProductInfoSerializer(product_all, many=True)
                        return Response(serializer.data)
                    return Response({"Status": False, "Errors": "Товары не найдены"})
                return Response(
                    {
                        "Status": False,
                        "Error": "Только для магазинов с активным статусом",
                    }
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # загрузка списка товаров из формата json (только для продавцов)
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active == True:
                    shop = Shop.objects.get(client=request.user.id)
                    if shop.state == True:
                        if {"categories", "goods"}.issubset(request.data):
                            if type(request.data["categories"]) == list and type(request.data["goods"]) == list:
                                celery_import_pricelist.delay(request.data, shop.id, request.user.email)
                                return Response(
                                    {"Status": True, "Info": "Список товаров отправлен на загрузку. Ожидайте сообщения на электронную почту"}
                                )
                            return Response(
                            {
                                "Status": False,
                                "Errors": "Неверный тип данных",
                            }
                        )
                        return Response(
                            {
                                "Status": False,
                                "Errors": "Не указаны все необходимые данные",
                            }
                        )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        }
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    }
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # удаление списка выставленных товаров (только для продавцов)
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active == True:
                    if {"password"}.issubset(request.data) and request.data["password"]:
                        if check_password(
                            request.data["password"], request.user.password
                        ):
                            shop = Shop.objects.get(client=request.user.id)
                            ProductInfo.objects.filter(shop=shop).delete()
                            return Response(
                                {"Status": True, "info": "Список товаров удален"}
                            )
                        return Response({"Status": False, "Error": "Неверный пароль"})
                    return Response(
                        {
                            "Status": False,
                            "Errors": "Не указаны все необходимые данные (password)",
                        }
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    }
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


# просмотр всех товаров на сервисе
class ProductsViewSet(ModelViewSet):
    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer
    filter_backends = [SearchFilter]
    search_fields = [
        "model",
        "product__name",
        "product_parameters__value",
        "product__category__name",
    ]
    pagination_class = LimitOffsetPagination


# просмотр всех категорий
class CategoryView(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    pagination_class = LimitOffsetPagination


# просмотр всех магазинов
class ShopView(ModelViewSet):
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopAllSerializer
    search_fields = ["name"]
    pagination_class = LimitOffsetPagination


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    # получить содержимое корзины
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                basket = (
                    Order.objects.filter(client=request.user.id, state="basket")
                    .prefetch_related(
                        "ordered_items__product_info__product__category",
                        "ordered_items__product_info__product_parameters__parameter",
                    )
                    .annotate(
                        total_sum=Sum(
                            F("ordered_items__quantity")
                            * F("ordered_items__product_info__price")
                        )
                    )
                    .distinct()
                )
                if not basket:
                    return Response({"Status": True, "Info": "Ваша корзина пуста"})
                serializer = OrderSerializer(basket, many=True)
                return Response(serializer.data)
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # # добавить в содержимое корзины
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if (
                    {"items"}.issubset(request.data)
                    and request.data["items"]
                    and type(request.data["items"]) == list
                ):
                    objects_created = 0
                    client = Client.objects.get(id=request.user.id)
                    basket = Order.objects.get_or_create(client=client, state="basket")[
                        0
                    ]
                    for items in request.data["items"]:
                        if (
                            "product_info" in items.keys()
                            and "quantity" in items.keys()
                        ):
                            if (
                                type(items["product_info"]) == int
                                and type(items["quantity"]) == int
                            ):
                                items.update({"order": basket.id})
                                serializer = OrderItemSerializer(data=items)
                                if serializer.is_valid():
                                    try:
                                        serializer.save()
                                    except IntegrityError as error:
                                        return Response(
                                            {"Status": False, "Errors": str(error)}
                                        )
                                    else:
                                        objects_created += 1
                                else:
                                    return Response(
                                        {"Status": False, "Errors": serializer.errors}
                                    )
                            else:
                                return Response(
                                    {"Status": False, "Errors": "Неверный тип данных"}
                                )
                        else:
                            return Response(
                                {
                                    "Status": False,
                                    "Errors": "Не указаны все необходимые данные",
                                }
                            )
                    return Response(
                        {
                            "Status": True,
                            "Info": f"Создано объектов - {objects_created}",
                        }
                    )
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"}
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if request.data["id"] and type(request.data["id"]) == list:
                    basket = Order.objects.filter(
                        client=request.user.id, state="basket"
                    )
                    if not basket:
                        return Response({"Status": True, "Info": "Ваша корзина пуста"})
                    query = Q()
                    objects_deleted = False
                    for id in request.data["id"]:
                        if type(id) == int:
                            query = query | Q(order=basket[0].id, id=id)
                            objects_deleted = True
                    if objects_deleted:
                        deleted_count = OrderItem.objects.filter(query).delete()[0]
                        return Response(
                            {
                                "Status": True,
                                "Info": f"Удалено объектов - {deleted_count}",
                            }
                        )
                    return Response({"Status": False, "Errors": "Неверный тип данных"})
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"}
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # редакатировать количество товаров в корзине
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if (
                    request.data
                    and request.data["items"]
                    and type(request.data["items"]) == list
                ):
                    basket = Order.objects.filter(
                        client=request.user.id, state="basket"
                    )
                    if not basket:
                        return Response({"Status": True, "Info": "Ваша корзина пуста"})
                    objects_updated = 0
                    for order_item in request.data["items"]:
                        if (
                            type(order_item["id"]) == int
                            and type(order_item["quantity"]) == int
                        ):
                            objects_updated += OrderItem.objects.filter(
                                order=basket[0].id, id=order_item["id"]
                            ).update(quantity=order_item["quantity"])
                        else:
                            return Response(
                                {"Status": False, "Errors": "Неверный тип данных"}
                            )
                    return Response(
                        {
                            "Status": True,
                            "Info": f"Обновлено объектов - {objects_updated}",
                        }
                    )
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"}
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


class OrderBuyerView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    """

    # получить мои заказы
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                order = (
                    Order.objects.filter(client=request.user.id)
                    .exclude(state="basket")
                    .prefetch_related(
                        "ordered_items__product_info__product__category",
                        "ordered_items__product_info__product_parameters__parameter",
                    )
                    .select_related("contact")
                    .annotate(
                        total_sum=Sum(
                            F("ordered_items__quantity")
                            * F("ordered_items__product_info__price")
                        )
                    )
                    .distinct()
                )
                if not order:
                    return Response(
                        {"Status": True, "Info": "Вы еще не успели сделать заказ"}
                    )
                serializer = OrderSerializer(order, many=True)
                return Response(serializer.data)
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                contacts = Contact.objects.get(client=request.user.id)
                order = Order.objects.filter(client=request.user.id, state="basket")
                order_id = order[0].id
                if order:
                    try:
                        order.update(contact=contacts, state="new")
                    except IntegrityError as error:
                        return Response({"Status": False, "Errors": str(error)})
                    else:
                        celery_send_note.delay(
                            "notific_new_order", (request.user.email, order_id)
                        )
                        return Response({"Status": True, "Info": "Заказ размещен"})
                return Response({"Status": True, "Info": "Ваша корзина пуста"})
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


class OrderShopView(APIView):
    """
    Класс для работы с заказами (только для магазинов)
    """

    # получение заказов
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if request.user.type == "shop":
                    if Shop.objects.get(client=request.user.id).state == True:
                        order = (
                            Order.objects.filter(
                                ordered_items__product_info__shop__client=request.user.id
                            )
                            .exclude(state="basket")
                            .prefetch_related(
                                "ordered_items__product_info__product__category",
                                "ordered_items__product_info__product_parameters__parameter",
                            )
                            .select_related("contact")
                            .annotate(
                                total_sum=Sum(
                                    F("ordered_items__quantity")
                                    * F("ordered_items__product_info__price")
                                )
                            )
                            .distinct()
                        )
                        serializer = OrderSerializer(order, many=True)
                        return Response(serializer.data)
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        }
                    )
                return Response(
                    {"Status": False, "Error": "Только для магазинов"}, status=403
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    # изменение статусов заказа
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if request.user.type == "shop":
                    if Shop.objects.get(client=request.user.id).state == True:
                        if (
                            request.data
                            and request.data["items"]
                            and type(request.data["items"]) == list
                        ):
                            for items in request.data["items"]:
                                if (
                                    "id" in items.keys()
                                    and "state" in items.keys()
                                    and type(items["id"]) == int
                                    and type(items["state"]) == str
                                ):
                                    if (
                                        "basket" not in items["state"]
                                        and "new" not in items["state"]
                                    ):
                                        order = Order.objects.filter(id=items["id"])
                                        try:
                                            order.update(state=items["state"])
                                        except IntegrityError as error:
                                            return Response(
                                                {"Status": False, "Errors": str(error)}
                                            )
                                        else:
                                            if order:
                                                celery_send_note.delay(
                                                    "notific_new_state_order",
                                                    (
                                                        order[0].client,
                                                        order[0].id,
                                                        items["state"],
                                                    ),
                                                )
                                                return Response(
                                                    {
                                                        "Status": True,
                                                        "Info": f"Статус изменен на - {items['state']}",
                                                    }
                                                )
                                    return Response(
                                        {
                                            "Status": False,
                                            "Errors": "На указанный статус невозможно изменить",
                                        }
                                    )
                                return Response(
                                    {"Status": False, "Errors": "Неверный тип данных"}
                                )
                        return Response(
                            {
                                "Status": False,
                                "Errors": "Не указаны все необходимые данные",
                            }
                        )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        }
                    )
                return Response(
                    {"Status": False, "Error": "Только для магазинов"}, status=403
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                }
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )
