from rest_framework import serializers

from backend.models import Client, Contact, ProductInfo, ProductParameter, Shop, OrderItem, Order, Product


class ContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            "id",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
            "user",
            "phone",
        )
        read_only_fields = ("id",)
        extra_kwargs = {"user": {"write_only": True}}


class ClientSerializer(serializers.ModelSerializer):
    contacts = ContactsSerializer(read_only=True, many=True)

    class Meta:
        model = Client
        fields = (
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "company",
            "position",
            "contacts",
        )
        read_only_fields = ("id",)


class CategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Client
        fields = ("id_category", "name", "shop")


class ParameterSerializer(serializers.ModelSerializer):
    
    parameter = serializers.StringRelatedField()
    
    class Meta:
        model = ProductParameter
        fields = ("parameter", "value")


class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = (
            "name",
            "category",
        )


class ProductInfoSerializer(serializers.ModelSerializer):
    
    product = ProductSerializer(read_only=True)
    product_parameters = ParameterSerializer(read_only=True, many=True)
    
    class Meta:
        model = ProductInfo
        fields = (
            "id",
            "model",
            "product",
            "external_id",
            "shop",
            "quantity",
            "price",
            "price_rrc",
            "product_parameters",
        )
        read_only_fields = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Shop
        fields = ("id", "name", "url", "client", "state")
        read_only_fields = ("id",)


class OrderItemSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product_info', 'quantity')
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactsSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)