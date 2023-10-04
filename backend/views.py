from django.forms import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.contrib.auth import login, authenticate, logout
import random
import string

from backend.models import Client
from backend.auth import hash_password

def generate_password():
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(10))
    return password

class RegisterClient(APIView):
    
    def get(self, request):
        count_buyer = Client.objects.filter(type='buyer').count()
        count_shop = Client.objects.filter(type='shop').count()
        return Response({"status": 'OK', 'info': f'Our platform is already used by {count_buyer} buyers and {count_shop} shop'})
         
    def post(self, request):
        data = request.data
        if 'password' not in data.keys():
            password = generate_password()
            data['password'] = password
        data['password'] = hash_password(data['password'])
        client = Client.objects.create(**data)
        return Response({'status': 'created', 'email': client.email, 'password': password})
    
class LoginClient(APIView):
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.is_authenticated:
            return Response({'Status': 'OK', 'Info': 'you are already authenticated'})
    
    def post(self, request):
        email = request.data["email"]
        password = request.data["password"]
        client = authenticate(request=request, email=email, password=password)
        if client is not None:
            login(request, client)
            return Response({'status': 'OK', 'Info': 'authentication was successful'})
        else:
            return Response({'status': False, 'Error': 'wrong login or password'})

@api_view(['GET'])
def logout_view(request):
    logout(request)
    return Response({'status': 'OK', 'info': 'you are not authenticated'})

class PricelistUpdate(APIView):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return Response({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})