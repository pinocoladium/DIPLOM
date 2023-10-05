from django.contrib.auth import authenticate, login, logout
from django.forms import ValidationError
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from backend.auth import generate_password, hash_password
from backend.models import Client, Product, Shop
from backend.serializers import (ClientSerializer, ProductSerializer,
                                 ShopSerializer)


class ProfileClient(APIView):

    """
    Для управления профилем пользователя сервиса

    """

    # узнать данные профиля пользователя
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_authenticated:
                serializers = ClientSerializer(Client.objects.get(id=request.user.id))
                return Response(serializers.data)
        return Response({"Status": False, "Error": "Log in required"}, status=403)

    # зарегистрировать нового пользователя
    def post(self, request, *args, **kwargs):
        data = request.data
        if {"first_name", "last_name", "email"}.issubset(data):
            if "type" in data.keys() and data["type"] != "shop":
                if "password" not in data.keys():
                    data["password"] = generate_password()
                password = data["password"]
                data["password"] = hash_password(password)
                client_serializer = ClientSerializer(data=data)
                if client_serializer.is_valid():
                    client = client_serializer.save()
                    # client.set_password(data['password'])
                    client.save()
                    # new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return Response(
                        {"status": True, "email": client.email, "password": password}
                    )
                return Response({"Status": False, "Errors": client_serializer.errors})
            return Response(
                {"Status": False, "Errors": "создание магазина сейчас недоступно"}
            )
        return Response(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    # измененить данные профиля пользователя
    def patch(self, request):
        if request.user.is_authenticated:
            client = Client.objects.get(id=request.user.id)
            client_serializer = ClientSerializer(
                client, data=request.data, partial=True
            )
            if client_serializer.is_valid():
                if "email" in request.data.keys():
                    # new_user_registered.send(sender=self.__class__, user_id=user.id)
                    pass
                client_serializer.save()
                return Response({"Status": True})
            else:
                return Response({"Status": False, "Errors": client_serializer.errors})
        return Response({"Status": False, "Error": "Log in required"}, status=403)


class ProfileShop(APIView):

    """
    Для управления профилем магазина сервиса

    """

    # узнать данные профиля магазина
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_authenticated:
                    serializers = ShopSerializer(
                        Shop.objects.get(client=request.user.id)
                    )
                    return Response(serializers.data)
            return Response({"Status": False, "Error": "Только для магазинов"})
        return Response({"Status": False, "Error": "Log in required"}, status=403)

    # зарегистрировать новый магазин
    def post(self, request, *args, **kwargs):
        if {"name"}.issubset(request.data):
            if request.user.type != "shop":
                request.data["client"] = request.user.id
                shop_serializer = ShopSerializer(data=request.data)
                if shop_serializer.is_valid():
                    shop = shop_serializer.save()
                    shop.save()
                    return Response(
                        {"status": True, "name shop": shop.name, "state": shop.state}
                    )
                return Response({"Status": False, "Errors": shop_serializer.errors})
            return Response(
                {
                    "Status": False,
                    "Errors": "Нельзя создать более 1 магазина на аккаунт",
                }
            )
        return Response(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    # измененить данные профиля магазина
    def patch(self, request):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                shop = Shop.objects.get(client=request.user.id)
                shop_serializer = ShopSerializer(shop, data=request.data, partial=True)
                if shop_serializer.is_valid():
                    shop_serializer.save()
                    return Response({"Status": True})
                else:
                    return Response({"Status": False, "Errors": shop_serializer.errors})
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=403)


class LoginClient(APIView):

    """
    Для аутентификации зарегистрированного пользователя сервиса

    """

    # узнать статус аутентификации
    def get(self, request):
        if request.user.is_authenticated:
            return Response({"Status": True, "Info": "you are already authenticated"})
        return Response({"Status": False, "Error": "Log in required"}, status=403)

    # аутентификация пользователя
    def post(self, request):
        client = authenticate(
            request=request,
            email=request.data["email"],
            password=request.data["password"],
        )
        if client is not None:
            login(request, client)
            return Response({"status": True, "Info": "authentication was successful"})
        return Response({"status": False, "Error": "wrong login or password"})


# деаутентификация
@api_view(["GET"])
def logout_view(request):
    logout(request)
    return Response({"status": True, "info": "you are not authenticated"})


# изменения статуса приема заказов (только для продавцов)
@api_view(["GET"])
def state_change_view(request):
    if request.user.is_authenticated:
        if request.user.type == "shop":
            shop = Shop.objects.get(client=request.user.id)
            if shop.state:
                shop.update(state=False)
                state = Shop.objects.get(client=request.user.id).state
                return Response({"Status": True, "State": state})
            else:
                shop.update(state=True)
                state = Client.objects.get(client=request.user.id).state
                return Response({"Status": True, "State": state})
        return Response({"Status": False, "Error": "Только для магазинов"})
    return Response({"Status": False, "Error": "Log in required"}, status=403)


# просмотр всех товаров на сервисе
class ProductsViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [
        SearchFilter,
    ]
    search_fields = ["name", "info__model"]
    pagination_class = LimitOffsetPagination


class Pricelist(APIView):
    """
    Для просмотра собственного и загрузки списка товаров (только для продавцов)

    """

    # просмотр списка выставленных товаров (только для продавцов)
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                shop = Shop.objects.get(id=request.user.id)
                products = Product.objects.all()
                product_all = products.product_infos.filter(shop=shop)
                product_list = []
                for el in product_all:
                    product_list.append(ProductSerializer(el))
                Response(product_list)
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response({"Status": False, "Error": "Log in required"}, status=403)

    # загрузка товаров из формата yaml
    # def post(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         return Response({'Status': False, 'Error': 'Log in required'}, status=403)

    #     if request.user.type != 'shop':
    #         return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

    #     url = request.data.get('url')
    #     if url:
    #         validate_url = URLValidator()
    #         try:
    #             validate_url(url)
    #         except ValidationError as e:
    #             return Response({'Status': False, 'Error': str(e)})
    #         else:
    #             stream = get(url).content

    #             data = load_yaml(stream, Loader=Loader)

    #             shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
    #             for category in data['categories']:
    #                 category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
    #                 category_object.shops.add(shop.id)
    #                 category_object.save()
    #             ProductInfo.objects.filter(shop_id=shop.id).delete()
    #             for item in data['goods']:
    #                 product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

    #                 product_info = ProductInfo.objects.create(product_id=product.id,
    #                                                           external_id=item['id'],
    #                                                           model=item['model'],
    #                                                           price=item['price'],
    #                                                           price_rrc=item['price_rrc'],
    #                                                           quantity=item['quantity'],
    #                                                           shop_id=shop.id)
    #                 for name, value in item['parameters'].items():
    #                     parameter_object, _ = Parameter.objects.get_or_create(name=name)
    #                     ProductParameter.objects.create(product_info_id=product_info.id,
    #                                                     parameter_id=parameter_object.id,
    #                                                     value=value)

    #             return JsonResponse({'Status': True})

    #     return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
