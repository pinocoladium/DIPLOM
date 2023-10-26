import datetime

from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.db.models import F, Q, Sum
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse
from backend.auth import check_password, generate_password, hash_password
from backend.models import (
    Category,
    Client,
    ConfirmEmailToken,
    Contact,
    Order,
    OrderItem,
    ProductInfo,
    Shop,
)
from backend.serializers import (
    CategorySerializer,
    ClientSerializer,
    ContactsSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    ShopAllSerializer,
    ShopSerializer,
)
from backend.tasks import celery_import_pricelist, celery_send_note


@extend_schema(tags=["Профиль пользователя сервиса"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение данных профиля",
            description="Для получения данных профиля пользователя сервиса",
            responses={status.HTTP_200_OK: OpenApiResponse(response=ClientSerializer, description="OK", examples=[
                OpenApiExample(
                    "Получение данных профиля",
                    description="Успешное получение данных профиля",
                    value=
                    {   
                        "id": "Ваш индивидуальный номер",
                        "first_name": "Ваше имя",
                        "last_name": "Ваша фамилия",
                        "username": "Ваш логин",
                        "email": "Ваша электронная почта",
                        "company": " Ваша организация",
                        "position": "ваша должность",
                        "contacts": "Ваши контакты" 
                    }
                ),
            ])
            },
        ),
    post=extend_schema(
            summary="Регистрация профиля",
            description="Для регистрации нового профиля пользователя сервиса",
            request=ClientSerializer,
            examples=[
                OpenApiExample(
                    "Регистрация профиля",
                    description="Все параметры обязательны, за исключением пароля. Пароль может быть сформирован сервисом при регистрации",
                    value=
                    {
                        "first_name": "Ваше имя",
                        "last_name": "Ваша фамилия",
                        "username": "Ваш логин",
                        "email": "Ваша электронная почта",
                        "company": " Ваша организация",
                        "position": "ваша должность",
                        "password": "Ваш пароль"
                    }
                ),
            ],
            responses={status.HTTP_200_OK: OpenApiResponse(response=ClientSerializer, description="OK", examples=[
                OpenApiExample(
                    "Регистрация профиля",
                    description="Успешное окончание регистрации. В ответе указаны данные для аутентификации",
                    value=
                    {
                       "status": True,
                        "email": "Ваш адрес электронной почты",
                        "password": "Ваш пароль", 
                    }
                ),
            ])
            },
        ),
    patch=extend_schema(
            summary="Изменение данных профиля",
            description="Для изменения данных профиля пользователя сервиса",
            request=ClientSerializer,
            examples=[
                OpenApiExample(
                    "Изменение данных профиля",
                    description="Все параметры необязательны, при смене почты будет выслан код для подтверждения",
                    value=
                    {
                        "first_name": "Ваше измененное имя",
                        "last_name": "Ваша измененная фамилия",
                        "username": "Ваш измененный логин",
                        "email": "Ваша измененная электронная почта",
                        "company": " Ваша измененная организация",
                        "position": "ваша измененная должность",
                        "password": "Ваш измененный пароль"
                    }
                ),
            ],
            responses={status.HTTP_201_CREATED: OpenApiResponse(response=ClientSerializer, description="OK", examples=[
                OpenApiExample(
                    "Изменение данных профиля",
                    description="Успешное окончание изменение данных профиля",
                    value={"Status": True, "info": "Изменения внесены"}
                ),
            ])
            }
        ),
    delete=extend_schema(
            summary="Удаление профиля",
            description="Для удаления профиля пользователя сервиса",
            responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(response=ClientSerializer, description="УДАЛЕНО", examples=[
                OpenApiExample(
                    "Удаление профиля",
                    description="Успешное удаление профиля",
                    value={"Status": True, "info": "Профиль удален"}
                ),
            ])
            }
        ))
class ProfileClient(APIView):
    """
    Класс для работы с профилем пользователя сервиса
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                ClientSerializer(Client.objects.get(id=request.user.id)).data,
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    def post(self, request, *args, **kwargs):
        if {"first_name", "last_name", "email"}.issubset(request.data):
            if "type" in request.data.keys() and request.data["type"] == "shop":
                return Response(
                    {"Status": False, "Errors": "Создание магазина сейчас недоступно"},
                    status=403,
                )
            if "is_active" in request.data.keys():
                request.data["is_active"] = False
            if "password" not in request.data.keys():
                request.data["password"] = generate_password()
            hashed_password = hash_password(request.data["password"])
            client_serializer = ClientSerializer(data=request.data)
            if client_serializer.is_valid():
                try:
                    client = client_serializer.save()
                except IntegrityError as error:
                    return Response({"Status": False, "Errors": str(error)}, status=200)
                else:
                    Client.objects.filter(id=client.id).update(password=hashed_password)
                    celery_send_note.delay(
                        "email_confirmation", (client.email, client.id)
                    )
                    return Response(
                        {
                            "status": True,
                            "email": client.email,
                            "password": request.data["password"],
                        },
                        status=201,
                    )
            return Response(
                {"Status": False, "Errors": client_serializer.errors}, status=200
            )
        return Response(
            {"Status": False, "Errors": "Не указаны все необходимые данные"}, status=200
        )

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
                    return Response({"Status": False, "Errors": str(error)}, status=200)
                else:
                    return Response(
                        {"Status": True, "info": "Изменения внесены"}, status=201
                    )
            return Response(
                {"Status": False, "Errors": client_serializer.errors}, status=200
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                        return Response(
                            {"Status": True, "info": "Профиль удален"}, status=204
                        )
                    return Response(
                        {"Status": False, "Error": "Неверный пароль"}, status=200
                    )
                return Response(
                    {
                        "Status": False,
                        "Errors": "Не указаны все необходимые данные (password)",
                    },
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


@extend_schema(tags=["Подтверждение электронной почты"])
@extend_schema_view(
    get=extend_schema(
            summary="Повторная отправка токена на почту",
            description="Для повторения отправки токена подтверждения на электронную почту пользователя сервиса",
        ),
    post=extend_schema(
            summary="Подтверждение почты",
            description="Для подтверждения токеном электронной почты пользователя сервиса",
        )
    )
class ConfirmEmail(APIView):
    """
    Класс для работы с подтверждением адреса электронной почты
    """
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
                    },
                    status=200,
                )
            return Response(
                {"Status": False, "Error": "Почта уже подтверждена"}, status=200
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                        },
                        status=200,
                    )
                if request.data["token"] == token.key:
                    Client.objects.filter(id=client.id).update(is_active=True)
                    return Response(
                        {"Status": True, "Info": "Почта подтверждена"}, status=200
                    )
                return Response(
                    {"Status": False, "Error": "Указанные неверные данные"}, status=200
                )
            return Response(
                {"Status": False, "Error": "Почта уже подтверждена"}, status=200
            )
        return Response(
            {"Status": False, "Error": "Не указан данные в запросе"}, status=200
        )


@extend_schema(tags=["Профиль пользователя сервиса"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение контактов профиля",
            description="Для получения контактных данных профиля пользователя сервиса",
        ),
    post=extend_schema(
            summary="Добавление контактов профиля",
            description="Для указания контактных данных профиля пользователя сервиса",
        ),
    patch=extend_schema(
            summary="Изменение контактов профиля",
            description="Для изменения контактных данных профиля пользователя сервиса",
        ),
    delete=extend_schema(
            summary="Удаление контактов профиля",
            description="Для удаления контактных данных профиля пользователя сервиса",
        )
    )
class ProfilContacts(APIView):
    """
    Класс для работы с контактами профиля пользователя сервиса
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                contact = Contact.objects.filter(client=request.user.id)
                if contact:
                    return Response(ContactsSerializer(contact[0]).data, status=200)
                return Response(
                    {
                        "Status": False,
                        "Error": "Контакты профиля не найдены",
                    },
                    status=404,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                            return Response(
                                {"Status": False, "Errors": str(error)}, status=200
                            )
                        else:
                            return Response(
                                {"Status": True, "Info": "Данные внесены"}, status=201
                            )
                    return Response(
                        {"Status": False, "Errors": contacts_serializers.errors},
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Errors": "Не указаны все необходимые данные (city, street, house, phone)",
                    },
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                            return Response(
                                {"Status": False, "Errors": str(error)}, status=200
                            )
                        else:
                            return Response(
                                {"Status": True, "Info": "Изменения внесены"},
                                status=201,
                            )
                    return Response(
                        {"Status": False, "Errors": contacts_serializers.errors},
                        status=200,
                    )
                return Response(
                    {"Status": False, "Error": "Контакты профиля не найдены"},
                    status=404,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                Contact.objects.filter(client=request.user.id).delete()
                return Response(
                    {"Status": True, "Info": "Контакты профиля удалены"}, status=204
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


@extend_schema(tags=["Профиль пользователя сервиса"],
            summary="Сброс пароля",
            description="Для сброса пароля от профиля и отправки нового на электронную почту пользователя сервиса"
)
# сброс пароля
@api_view(["GET"])
def reset_password_view(request, *args, **kwargs):
    if request.data:
        client = Client.objects.filter(**request.data)
        if client:
            celery_send_note.delay(
                "reset_password_created", (client[0].id)
            )
            Token.objects.filter(user=client[0].id).delete()
            return Response(
                {
                    "Status": True,
                    "Info": "Пароль для входа отправлен на электронную почту",
                },
                status=200,
            )
        return Response({"status": False, "Error": "Аккаунт не найден"}, status=404)
    return Response(
        {
            "status": False,
            "Error": "Необходимо указать какие-нибудь данные о профиле (username, email)",
        },
        status=200,
    )


@extend_schema(tags=["Аутентификация"])
@extend_schema_view(
    get=extend_schema(
            summary="Статус аутентификации пользователя",
            description="Для получения статуса аутентификации пользователя сервиса",
        ),
    post=extend_schema(
            summary="Аутентификация пользователя",
            description="Для аутентификации зарегистрированного пользователя сервиса",
        )
    )
class LoginClient(APIView):
    """
    Класс для работы с аутентификацией пользователей сервиса
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                {"Status": True, "Info": "Вы прошли аутентификацию"}, status=200
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                },
                status=200,
            )
        return Response(
            {"status": False, "Error": "Неверно введен логин или пароль"}, status=200
        )


@extend_schema(tags=["Аутентификация"],
            summary="Деаутентификация пользователя",
            description="Для деаутентификации аутентифицированного пользователя сервиса"
        )
# деаутентификация
@api_view(["GET"])
def logout_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        Token.objects.filter(user=Client.objects.get(id=request.user.id)).delete()
        return Response(
            {"status": True, "info": "Деаутентификация прошла успешно"}, status=200
        )
    return Response(
        {"status": False, "Error": "Вы не проходили аутентификацию"}, status=200
    )


@extend_schema(tags=["Профиль магазина"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение данных магазина",
            description="Для получения данных профиля магазина пользователя сервиса",
        ),
    post=extend_schema(
            summary="Регистрация магазина",
            description="Для регистрации нового профиля магазина пользователя сервиса",
        ),
    patch=extend_schema(
            summary="Изменение данных магазина",
            description="Для изменения данных профиля магазина пользователя сервиса",
        ),
    delete=extend_schema(
            summary="Удаление магазина",
            description="Для удаления профиля магазина пользователя сервиса",
        )
    )
class ProfileShop(APIView):
    """
    Класс для работы с профилем магазина пользователя сервиса
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    return Response(
                        ShopSerializer(Shop.objects.get(client=request.user.id)).data,
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    },
                    status=200,
                )
            return Response({"Status": False, "Error": "Магазин не создан"}, status=404)
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                                return Response(
                                    {"Status": False, "Errors": str(error)}, status=200
                                )
                            else:
                                Client.objects.filter(id=request.user.id).update(
                                    type="shop"
                                )
                                return Response(
                                    {
                                        "status": True,
                                        "name shop": shop.name,
                                        "state": shop.state,
                                    },
                                    status=201,
                                )
                        return Response(
                            {"Status": False, "Errors": shop_serializer.errors},
                            status=200,
                        )
                    return Response(
                        {
                            "Status": False,
                            "Errors": "Не указаны все необходимые данные (name)",
                        },
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Errors": "Нельзя создать более 1 магазина на аккаунт",
                    },
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Errors": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                            return Response(
                                {"Status": False, "Errors": str(error)}, status=200
                            )
                        else:
                            return Response(
                                {"Status": True, "Info": "Изменения внесены"},
                                status=201,
                            )
                    return Response(
                        {"Status": False, "Errors": shop_serializer.errors}, status=200
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    },
                    status=200,
                )
            return Response({"Status": False, "Error": "Магазин не создан"}, status=200)
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)

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
                            return Response(
                                {"Status": True, "Info": "Магазин удален"}, status=204
                            )
                        return Response(
                            {"Status": False, "Error": "Неверный пароль"}, status=200
                        )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Не указаны все необходимые данные (password)",
                        },
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    },
                    status=200,
                )
            return Response({"Status": False, "Error": "Магазин не создан"}, status=404)
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)


@extend_schema(tags=["Профиль магазина"], 
            summary="Изменение статуса приема заказов",
            description="Для изменения статуса приема заказов профиля магазина пользователя сервиса")
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
                        },
                        status=201,
                    )
                shop.update(state=True)
                return Response(
                    {
                        "Status": True,
                        "Info": "Статус - активен",
                    },
                    status=201,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response({"Status": False, "Error": "Только для магазинов"}, status=403)
    return Response(
        {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
    )


@extend_schema(tags=["Профиль магазина"])
@extend_schema_view(
    get=extend_schema(
            summary="Просмотр списка товаров",
            description="Для просмотра выставленного списка товаров профиля магазина пользователя сервиса",
        ),
    post=extend_schema(
            summary="Загрузка списка товаров",
            description="Для загрузки списка товаров профиля магазина пользователя сервиса",
        ),
    delete=extend_schema(
            summary="Удаление списка товаров",
            description="Для удаления выставленного списка товаров профиля магазина пользователя сервиса",
        )
    )
class ShopPricelist(APIView):
    """
    Класс для работы со списком товаров профиля магазина пользователя сервиса
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                shop = Shop.objects.get(client=request.user.id)
                if shop.state == True:
                    product_all = ProductInfo.objects.filter(shop=shop.id)
                    if product_all:
                        serializer = ProductInfoSerializer(product_all, many=True)
                        return Response(serializer.data)
                    return Response(
                        {"Status": False, "Error": "Товары не найдены"}, status=404
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Только для магазинов с активным статусом",
                    },
                    status=200,
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active == True:
                    shop = Shop.objects.get(client=request.user.id)
                    if shop.state == True:
                        if {"categories", "goods"}.issubset(request.data):
                            if (
                                type(request.data["categories"]) == list
                                and type(request.data["goods"]) == list
                            ):
                                celery_import_pricelist.delay(
                                    request.data, shop.id, request.user.email
                                )
                                return Response(
                                    {
                                        "Status": True,
                                        "Info": "Список товаров отправлен на загрузку. Ожидайте сообщения на электронную почту",
                                    },
                                    status=202,
                                )
                            return Response(
                                {
                                    "Status": False,
                                    "Errors": "Неверный тип данных",
                                },
                                status=200,
                            )
                        return Response(
                            {
                                "Status": False,
                                "Errors": "Не указаны все необходимые данные",
                            },
                            status=200,
                        )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        },
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    },
                    status=200,
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                                {"Status": True, "Info": "Список товаров удален"},
                                status=204,
                            )
                        return Response(
                            {"Status": False, "Error": "Неверный пароль"}, status=200
                        )
                    return Response(
                        {
                            "Status": False,
                            "Errors": "Не указаны все необходимые данные (password)",
                        },
                        status=200,
                    )
                return Response(
                    {
                        "Status": False,
                        "Error": "Необходимо сначала подтвердить адрес электронной почты",
                    },
                    status=200,
                )
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


@extend_schema(tags=["Товары"])
@extend_schema_view(
    list=extend_schema(
            summary="Просмотр всех товаров",
            description="Для просмотра всех товаров выставленных на сервисе",
        ),
    retrieve=extend_schema(
            summary="Просмотр товара",
            description="Для просмотра данных конкретного товара выставленного на сервисе",
        ))
class ProductsViewSet(ModelViewSet):
    """
    Класс для работы с товарами выставленными на сервисе
    """
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
    http_method_names = http_method_names = ['get']


@extend_schema(tags=["Товары"])
@extend_schema_view(
    list=extend_schema(
            summary="Просмотр всех категорий",
            description="Для просмотра всех категорий товаров выставленных на сервисе",
        ),
    retrieve=extend_schema(
            summary="Просмотр категории",
            description="Для просмотра конкретной категории товаров выставленных на сервисе",
        ))
class CategoryView(ModelViewSet):
    """
    Класс для работы с категориями товаров выставленных на сервисе
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    pagination_class = LimitOffsetPagination
    http_method_names = http_method_names = ['get']


@extend_schema(tags=["Товары"])
@extend_schema_view(
    list=extend_schema(
            summary="Просмотр всех магазинов",
            description="Для просмотра всех магазинов на сервисе",
        ),
    retrieve=extend_schema(
            summary="Просмотр конкретного магазина",
            description="Для просмотра конкретного магазина на сервисе",
        ))
class ShopView(ModelViewSet):
    """
    Класс для работы с магазинами на сервисе
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopAllSerializer
    search_fields = ["name"]
    pagination_class = LimitOffsetPagination
    http_method_names = http_method_names = ['get']


@extend_schema(tags=["Профиль покупателя"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение корзины",
            description="Для получения содержимого корзины пользователя сервиса",
        ),
    post=extend_schema(
            summary="Добавление товара в корзину",
            description="Для добавления товара в содержимое корзины пользователя сервиса",
        ),
    patch=extend_schema(
            summary="Изменение количества товара в корзине",
            description="Для изменения количества содержимого корзины пользователя сервиса",
        ),
    delete=extend_schema(
            summary="Удаление товара из корзины",
            description="Для удаления содержимого корзины пользователя сервиса",
        )
    )
class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя сервиса
    """
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
                    return Response(
                        {"Status": True, "Info": "Ваша корзина пуста"}, status=200
                    )
                serializer = OrderSerializer(basket, many=True)
                return Response(serializer.data, status=200)
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                                            {"Status": False, "Errors": str(error)},
                                            status=200,
                                        )
                                    else:
                                        objects_created += 1
                                else:
                                    return Response(
                                        {"Status": False, "Errors": serializer.errors},
                                        status=200,
                                    )
                            else:
                                return Response(
                                    {"Status": False, "Errors": "Неверный тип данных"},
                                    status=200,
                                )
                        else:
                            return Response(
                                {
                                    "Status": False,
                                    "Errors": "Не указаны все необходимые данные",
                                },
                                status=200,
                            )
                    return Response(
                        {
                            "Status": True,
                            "Info": f"Создано объектов - {objects_created}",
                        },
                        status=200,
                    )
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"},
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if request.data["id"] and type(request.data["id"]) == list:
                    basket = Order.objects.filter(
                        client=request.user.id, state="basket"
                    )
                    if not basket:
                        return Response(
                            {"Status": True, "Info": "Ваша корзина пуста"}, status=200
                        )
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
                            },
                            status=200,
                        )
                    return Response(
                        {"Status": False, "Errors": "Неверный тип данных"}, status=200
                    )
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"},
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                        return Response(
                            {"Status": True, "Info": "Ваша корзина пуста"}, status=200
                        )
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
                                {"Status": False, "Errors": "Неверный тип данных"},
                                status=200,
                            )
                    return Response(
                        {
                            "Status": True,
                            "Info": f"Обновлено объектов - {objects_updated}",
                        },
                        status=200,
                    )
                return Response(
                    {"Status": False, "Errors": "Не указаны все необходимые данные"},
                    status=200,
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


@extend_schema(tags=["Профиль покупателя"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение размещенных заказов",
            description="Для получения размещенных заказов пользователем сервиса",
        ),
    post=extend_schema(
            summary="Размещение заказа",
            description="Для размещени заказов пользователем сервиса",
        )
    )
class OrderBuyerView(APIView):
    """
    Класс для работы с заказами для пользователей сервиса
    """
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
                        {"Status": True, "Info": "Вы еще не успели сделать заказ"},
                        status=200,
                    )
                serializer = OrderSerializer(order, many=True)
                return Response(serializer.data, status=200)
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                contacts = Contact.objects.filter(client=request.user.id)
                if not contacts:
                    return Response(
                            {"Status": False, "Error": "Для оформления заказа необходимо указать контакты"}, status=404
                        )
                order = Order.objects.filter(client=request.user.id, state="basket")
                order_id = order[0].id
                if order:
                    try:
                        order.update(contact=contacts[0], state="new")
                    except IntegrityError as error:
                        return Response(
                            {"Status": False, "Errors": str(error)}, status=200
                        )
                    else:
                        celery_send_note.delay(
                            "notific_new_order", (request.user.email, order_id)
                        )
                        return Response(
                            {"Status": True, "Info": "Заказ размещен"}, status=200
                        )
                return Response(
                    {"Status": True, "Info": "Ваша корзина пуста"}, status=200
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )


@extend_schema(tags=["Профиль магазина"])
@extend_schema_view(
    get=extend_schema(
            summary="Получение заказов",
            description="Для получения размещенных заказов пользователями сервиса",
        ),
    patch=extend_schema(
            summary="Изменение статуса заказа",
            description="Для изменения статуса размещенных заказов пользователями сервиса",
        )
    )
class OrderShopView(APIView):
    """
    Класс для работы с заказами для профилей магазинов
    """
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
                        if not order:
                            return Response(
                                {"Status": True, "Info": "Заказов нет"},
                                status=200,
                            )
                        serializer = OrderSerializer(order, many=True)
                        return Response(serializer.data, status=200)
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        },
                        status=200,
                    )
                return Response(
                    {"Status": False, "Error": "Только для магазинов"}, status=403
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )

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
                                                {"Status": False, "Errors": str(error)},
                                                status=200,
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
                                                    },
                                                    status=200,
                                                )
                                    return Response(
                                        {
                                            "Status": False,
                                            "Errors": "На указанный статус невозможно изменить",
                                        },
                                        status=200,
                                    )
                                return Response(
                                    {"Status": False, "Errors": "Неверный тип данных"},
                                    status=200,
                                )
                        return Response(
                            {
                                "Status": False,
                                "Errors": "Не указаны все необходимые данные",
                            },
                            status=200,
                        )
                    return Response(
                        {
                            "Status": False,
                            "Error": "Только для магазинов с активным статусом",
                        },
                        status=200,
                    )
                return Response(
                    {"Status": False, "Error": "Только для магазинов"}, status=403
                )
            return Response(
                {
                    "Status": False,
                    "Error": "Необходимо сначала подтвердить адрес электронной почты",
                },
                status=200,
            )
        return Response(
            {"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401
        )