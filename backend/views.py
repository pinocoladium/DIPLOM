from django.forms import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.contrib.auth import login, authenticate, logout
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet
import json
import random
import string

from backend.models import Client, Product, Shop
from backend.auth import hash_password
from backend.serializers import ClientSerializer, ProductSerializer


def generate_password():
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(10))
    return password

class RegisterClient(APIView):
    
    """
    Для регистрации пользователей сервиса
    
    """
    # узнать количество зарегистрированных пользователей сервиса
    def get(self, request):
        count_buyer = Client.objects.filter(type='buyer').count()
        count_shop = Client.objects.filter(type='shop').count()
        return Response({"status": True, 'info': f'Our platform is already used by {count_buyer} buyers and {count_shop} shop'})
    
    # зарегистрировать нового пользователя сервиса     
    def post(self, request, *args, **kwargs):
        data = request.data
        if {'first_name', 'last_name', 'email', 'company', 'position'}.issubset(request.data):
            if 'type' in data.keys() and data['type'] != 'shop':
                if 'password' not in data.keys():
                    password = generate_password()
                    data['password'] = password
                data['password'] = hash_password(data['password'])
                client_serializer = ClientSerializer(data=request.data)
                if client_serializer.is_valid():
                    client = client_serializer.save()
                    client.set_password(request.data['password'])
                    client.save()
                    # new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return Response({'status': True, 'email': client.email, 'password': password})
                return Response({'Status': False, 'Errors': client_serializer.errors})
            return Response({'Status': False, 'Errors': 'создание магазина сейчас недоступно'})
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    
class LoginClient(APIView):
    
    """
    Для аутентификации зарегистрированных пользователей сервиса
    
    """
    
    # узнать статус аутентификации
    def get(self, request):
        if request.user.is_authenticated:
            return Response({'Status': True, 'Info': 'you are already authenticated'})
        return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        
    # аутентификация пользователя
    def post(self, request):
        client = authenticate(request=request, email=request.data["email"], password=request.data["password"])
        if client is not None:
            login(request, client)
            return Response({'status': True, 'Info': 'authentication was successful'})
        return Response({'status': False, 'Error': 'wrong login or password'})

# деаутентификация
@api_view(['GET'])
def logout_view(request):
    logout(request)
    return Response({'status': True, 'info': 'you are not authenticated'})

class ProfileClient(APIView):
    
    """
    Для управления данными профиля пользователя
    
    """
    
    # узнать данные профиля пользователя
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_authenticated:
                serializers = ClientSerializer(Client.objects.get(id=request.user.id))
                return Response(serializers.data)
        return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        
    # изменение данных профиля пользователя
    def post(self, request):
        if request.user.is_authenticated:
            client = Client.objects.get(id=request.user.id)
            client_serializer = ClientSerializer(client, data=request.data, partial=True)
            if client_serializer.is_valid():
                if 'email' in request.data.keys():
                    # new_user_registered.send(sender=self.__class__, user_id=user.id)
                    pass
                client_serializer.save()
                return Response({'Status': True})
            else:
                return Response({'Status': False, 'Errors': client_serializer.errors})
        return Response({'Status': False, 'Error': 'Log in required'}, status=403)

# изменения статуса приема заказов (только для продавцов)
# @api_view(['GET'])
# def state_change_view(request):
    # if not request.user.is_authenticated:
    #         return Response({'Status': False, 'Error': 'Log in required'}, status=403)
    # if request.user.type != 'shop':
    #     return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)
    # request.user.id = 11
    # shop = Shop.objects.get(client=request.user.id)
    # if shop.state:
    #     shop.update(state=False)
    #     state = Shop.objects.get(client=request.user.id).state
    #     return Response({'Status': True, 'State': state})
    # else:
    #     shop.update(state=False)
    #     state = Client.objects.get(client=request.user.id).state
    #     return Response({'Status': True, 'State': state})
    

 
# просмотр всех товаров на сервисе            
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [SearchFilter, ]
    search_fields = ['name', 'info__model']
    pagination_class = LimitOffsetPagination


class Pricelist(APIView):
    """
    Для просмотра собственного и загрузки списка товаров (только для продавцов)
    
    """
    # просмотр списка выставленных товаров (только для продавцов)
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.type == 'shop':
                shop = Shop.objects.get(id=request.user.id)
                products = Product.objects.all()
                product_all = products.product_infos.filter(shop=shop)
                product_list = []
                for el in product_all:
                    product_list.append(ProductSerializer(el))
                Response(product_list)
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)    
        return Response({'Status': False, 'Error': 'Log in required'}, status=403)
    
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