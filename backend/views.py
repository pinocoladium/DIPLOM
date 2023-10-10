from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.authtoken.models import Token
from django.db import IntegrityError
from django.db.models import Q, Sum, F
import datetime

from backend.auth import generate_password, hash_password, check_password
from backend.models import (Category, Client, ConfirmEmailToken, Parameter,
                            Product, ProductInfo, ProductParameter, Shop, Contact, Order)
from backend.notifications import email_confirmation, reset_password_created, notific_delete_profile
from backend.serializers import (ClientSerializer, ProductInfoSerializer,
                                 ShopSerializer, ContactsSerializer, CategorySerializer, OrderSerializer, OrderItemSerializer)


class ProfileClient(APIView):

    """
    Для управления профилем пользователя сервиса

    """

    # узнать данные профиля пользователя
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_authenticated:
                return Response(ClientSerializer(Client.objects.get(id=request.user.id)).data)
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

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
                client = client_serializer.save()
                Client.objects.filter(id=client.id).update(password=hashed_password)
                email_confirmation(client.email, client.id)
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
                email_confirmation(request.data["email"], client.id)
                request.data["is_active"] = False
            if "is_active" in request.data.keys():
                request.data["is_active"] = client.is_active
            if "type" in request.data.keys():
                request.data["type"] = client.type    
            client_serializer = ClientSerializer(
                client, data=request.data, partial=True
            )
            if client_serializer.is_valid():
                client_serializer.save()
                return Response({"Status": True, "info": "Изменения внесены"})
            else:
                return Response({"Status": False, "Errors": client_serializer.errors})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # удалить профиль
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if check_password(request.data["password"], request.user.password):
                    notific_delete_profile(request.user.email, request.user.username)
                    Client.objects.filter(id=request.user.id).delete()
                    return Response({"Status": True, "info": "Профиль удален"})
                return Response({"Status": False, "Error": "Неверный пароль"})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

class ConfirmEmail(APIView):

    """
    Для подтверждения адреса электронной почты

    """

    # повторить отправку токена подтверждения на электронную почту
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == False:
                email_confirmation(request.user.email, request.user.id)
                return Response(
                    {
                        "Status": True,
                        "Info": "Письмо отправлено на Вашу электронную почту",
                    }
                )
            return Response({"Status": False, "Error": "Почта уже подтверждена"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # подтвердить токеном электронную почту
    def post(self, request, *args, **kwargs):
        if "token" in request.data.keys() and request.data["token"]:
            client = Client.objects.get(email=request.data["email"])
            if client.is_active == False:
                token = ConfirmEmailToken.objects.get(client=client)
                if token.created_at + datetime.timedelta(hours=24) <= datetime.datetime.now():
                    email_confirmation(request.data["email"], client.id)
                    return Response({"Status": False, "Error": "Устаревший токен. На электронную почту отправлен другой"})
                if (request.data["token"] == token.key):
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
                return Response(ContactsSerializer(Contact.objects.get(client=request.user.id)).data)
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)
    
    # указать контакты профиля
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if {"city", "street", "house", "phone"}.issubset(request.data):
                    contacts_serializers = ContactsSerializer(request.data)
                    if contacts_serializers.is_valid():
                        contacts_serializers.save()
                        return Response({"Status": True, "Info": "Данные внесены"})
                return Response({"Status": False, "Errors": "Не указаны все необходимые данные"})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # внести изменения в контакты профиля
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if Contact.objects.filter(client=request.user.id):
                    contacts_serializers = ContactsSerializer(Contact, data=request.data, partial=True)
                    if contacts_serializers.is_valid():
                        contacts_serializers.save()
                        return Response({"Status": True, "Info": "Изменения внесены"})
                return Response({"Status": False, "Error": "Контакты профиля не найдены"})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # удалить контакты профиля
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                Contact.objects.filter(client=request.user.id).delete()
                return Response({"Status": True, "Info": "Контакты профиля удалены"})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)


# сброс пароля
@api_view(["POST"])
def reset_password_view(request, *args, **kwargs):
    if request.data:
        if Client.objects.filter(**request.data):
            reset_password_created(Client.objects.get(**request.data).id)
            return Response({"Status": True, "Info": "Пароль для входа отправлен на электронную почту"})
        return Response({"status": False, "Error": "Аккаунт не найден"})
    return Response({"status": False, "Error": "Необходимо указать какие-нибудь данные о профиле (username, email)"})


class LoginClient(APIView):

    """
    Для аутентификации зарегистрированного пользователя сервиса

    """

    # узнать статус аутентификации
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"Status": True, "Info": "Вы прошли аутентификацию"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # аутентификация пользователя
    def post(self, request, *args, **kwargs):
        client = authenticate(
            request=request,
            email=request.data["email"],
            password=request.data["password"],
        )
        if client is not None:
            token = Token.objects.get_or_create(user=client)
            return Response({'Status': True,"Info": "Аутентификация прошла успешно", 'Token': str(token)})
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
                if request.user.is_authenticated:
                    serializers = ShopSerializer(
                        Shop.objects.get(client=request.user.id)
                    )
                    return Response(serializers.data)
            return Response({"Status": False, "Error": "Только для магазинов"})
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # зарегистрировать новый магазин
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active:
                if request.user.type == "buyer":
                    if {"name"}.issubset(request.data):
                        request.data["client"] = request.user.id
                        shop_serializer = ShopSerializer(data=request.data)
                        if shop_serializer.is_valid():
                            shop = shop_serializer.save()
                            Client.objects.filter(id=request.user.id).update(type="shop")
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
                            "Errors": "Не указаны все необходимые аргументы",
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
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # измененить данные профиля магазина
    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    shop = Shop.objects.get(client=request.user.id)
                    shop_serializer = ShopSerializer(shop, data=request.data, partial=True)
                    if shop_serializer.is_valid():
                        shop_serializer.save()
                        return Response({"Status": True, "Info": "Изменения внесены"})
                    return Response({"Status": False, "Errors": shop_serializer.errors})
                return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)
    
    # удалить профиль магазина
    def delete(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active:
                    if check_password(request.data["password"], request.user.password):
                        Shop.objects.filter(client=request.user.id).delete()
                        Client.objects.filter(id=request.user.id).update(type="buyer")
                        return Response({"Status": True, "Info": "Изменения внесены"})
                    return Response({"Status": False, "Error": "Неверный пароль"})    
                return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
            return Response({"Status": False, "Error": "Магазин не создан"})
        return Response({"Status": False, "Error": "Нет аутентификации"}, status=401)


# изменения статуса приема заказов (только для продавцов)
@api_view(["GET"])
def state_change_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        if request.user.type == "shop":
            if request.user.is_active == True:
                shop = Shop.objects.get(client=request.user.id)
                if shop.state:
                    shop.update(state=False)
                    return Response({"Status": True, "State": Shop.objects.get(client=request.user.id).state})
                shop.update(state=True)
                return Response({"Status": True, "State": Client.objects.get(client=request.user.id).state})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({"Status": False, "Error": "Только для магазинов"})
    return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)


class ShopPricelist(APIView):

    """
    Для просмотра собственного и загрузки списка товаров (только для продавцов)

    """

    # просмотр списка выставленных товаров (только для продавцов)
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                shop = Shop.objects.get(client=request.user.id)
                product_all = ProductInfo.objects.filter(shop=shop)
                serializers = ProductInfoSerializer(product_all, many=True)
                # product_list = []
                # for el in product_all:
                #     product_list.append(ProductInfoSerializer(el))
                Response(serializers.data)
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)

    # загрузка списка товаров из формата json (только для продавцов)
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active == True:
                    shop = Shop.objects.get(id=request.user.id)
                    if {"categories", "goods"}.issubset(request.data):
                        for category in request.data["categories"]:
                            category_object = Category.objects.get_or_create(
                                id_category=category["id"],
                                name=category["name"],
                                shop=shop.id,
                            )
                            category_object.save()
                        ProductInfo.objects.filter(shop=shop.id).delete()
                        for item in request.data["goods"]:
                            product = Product.objects.get_or_create(
                                name=item["name"], category=category_object.id
                            )
                            product_info = ProductInfo.objects.create(
                                product=product.id,
                                external_id=item["id"],
                                model=item["model"],
                                price=item["price"],
                                price_rrc=item["price_rrc"],
                                quantity=item["quantity"],
                                shop=shop.id,
                            )
                            for name, value in item["parameters"].items():
                                parameter_object = Parameter.objects.get_or_create(
                                    name=name
                                )
                                ProductParameter.objects.create(
                                    product_info=product_info.id,
                                    parameter=parameter_object.id,
                                    value=value,
                                )
                        return Response({"Status": True, "Info": "Список товаров обновлен"})
                    return Response(
                        {"Status": False, "Errors": "Не указаны все необходимые данные"}
                    )
                return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)
    
    # удаление списка выставленных товаров (только для продавцов)
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.type == "shop":
                if request.user.is_active == True:
                    if check_password(request.data["password"], request.user.password):
                        shop = Shop.objects.get(client=request.user.id)
                        ProductInfo.objects.filter(shop=shop).delete()
                        return Response({"Status": True, "info": "Список товаров удален"})
                    return Response({"Status": False, "Error": "Неверный пароль"})
                return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
            return Response(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        return Response({"Status": False, "Error": "Вы не прошли аутентификацию"}, status=401)


# просмотр всех товаров на сервисе
class ProductsViewSet(ModelViewSet):
    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer
    filter_backends = [
        SearchFilter,
    ]
    search_fields = ["model", "product", "product_parameters"]
    pagination_class = LimitOffsetPagination

# просмотр всех категорий
class CategoryView(ModelViewSet):
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name", "state"]
    pagination_class = LimitOffsetPagination

# просмотр всех магазинов
class ShopView(ModelViewSet):
    
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    search_fields = ["name", "state"]
    pagination_class = LimitOffsetPagination


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    # получить содержимое корзины
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                basket = Order.objects.filter(
                    client=request.user.id, state='basket').prefetch_related(
                    'ordered_items__product_info__product__category',
                    'ordered_items__product_info__product_parameters__parameter').annotate(
                    total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
                serializer = OrderSerializer(basket, many=True)
                return Response(serializer.data)
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({'Status': False, 'Error': 'Вы не прошли аутентификацию'}, status=401)

    # # добавить в содержимое корзины
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active == True:
                if items in request.data["items"]:
                    objects_created = 0
                    basket = Order.objects.get_or_create(client=request.user.id, state='basket')
                    for items in request.data["items"]:
                        if ["product_info", "quantity"] in items.keys():
                            items.update({'order': basket.id})
                            serializer = OrderItemSerializer(data=items)
                            if serializer.is_valid():
                                try:
                                    serializer.save()
                                except IntegrityError as error:
                                    return Response({'Status': False, 'Errors': str(error)})
                                else:
                                    objects_created += 1
                                    return Response({'Status': True, "Info": f"Создано объектов - {objects_created}"})
                            return Response({'Status': False, 'Errors': serializer.errors})
                        return Response({'Status': False, 'Errors': 'Не указаны все необходимые данные'})
                return Response({'Status': False, 'Errors': 'Не указаны все необходимые данные'})
            return Response({"Status": False, "Error": "Необходимо сначала подтвердить адрес электронной почты"})
        return Response({'Status': False, 'Error': 'Вы не прошли аутентификацию'}, status=401)

    # удалить товары из корзины
    # def delete(self, request, *args, **kwargs):
    #     if request.user.is_authenticated:
    #         items_sting = request.data.get('items')
    #         if items_sting:
    #             items_list = items_sting.split(',')
    #             basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
    #             query = Q()
    #             objects_deleted = False
    #             for order_item_id in items_list:
    #                 if order_item_id.isdigit():
    #                     query = query | Q(order_id=basket.id, id=order_item_id)
    #                     objects_deleted = True
    #             if objects_deleted:
    #                 deleted_count = OrderItem.objects.filter(query).delete()[0]
    #                 return Response({'Status': True, 'Удалено объектов': deleted_count})
    #         return Response({'Status': False, 'Errors': 'Не указаны все необходимые данные'})
    #     return Response({'Status': False, 'Error': 'Вы не прошли аутентификацию'}, status=401)
    
    # # добавить позиции в корзину
    # def put(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

    #     items_sting = request.data.get('items')
    #     if items_sting:
    #         try:
    #             items_dict = load_json(items_sting)
    #         except ValueError:
    #             return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
    #         else:
    #             basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
    #             objects_updated = 0
    #             for order_item in items_dict:
    #                 if type(order_item['id']) == int and type(order_item['quantity']) == int:
    #                     objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
    #                         quantity=order_item['quantity'])

    #             return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
    #     return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    
    
    # class OrderView(APIView):
    # """
    # Класс для получения и размешения заказов пользователями
    # """

    # # получить мои заказы
    # def get(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
    #     order = Order.objects.filter(
    #         user_id=request.user.id).exclude(state='basket').prefetch_related(
    #         'ordered_items__product_info__product__category',
    #         'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
    #         total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

    #     serializer = OrderSerializer(order, many=True)
    #     return Response(serializer.data)

    # # разместить заказ из корзины
    # def post(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

    #     if {'id', 'contact'}.issubset(request.data):
    #         if request.data['id'].isdigit():
    #             try:
    #                 is_updated = Order.objects.filter(
    #                     user_id=request.user.id, id=request.data['id']).update(
    #                     contact_id=request.data['contact'],
    #                     state='new')
    #             except IntegrityError as error:
    #                 print(error)
    #                 return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
    #             else:
    #                 if is_updated:
    #                     new_order.send(sender=self.__class__, user_id=request.user.id)
    #                     return JsonResponse({'Status': True})

    #     return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    
    
    # class PartnerOrders(APIView):
    # """
    # Класс для получения заказов поставщиками
    # """
    # def get(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

    #     if request.user.type != 'shop':
    #         return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

    #     order = Order.objects.filter(
    #         ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
    #         'ordered_items__product_info__product__category',
    #         'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
    #         total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

    #     serializer = OrderSerializer(order, many=True)
    #     return Response(serializer.data)
