from rest_framework import serializers

from backend.models import Client, Contact, ProductInfo, ProductParameter, Shop


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
        fields = ("id", "id_category", "name", "shop")
        read_only_fields = ("id",)


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInfo
        fields = (
            "id",
            "model",
            "external_id",
            "shop",
            "quantity",
            "price",
            "price_rrc",
        )
        read_only_fields = ("id",)


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductParameter
        fields = ("id", "product_info", "parameter", "value")
        read_only_fields = ("id",)


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True, many=True)
    info = ProductInfoSerializer(read_only=True, many=True)
    parameter = ParameterSerializer(read_only=True, many=True)

    class Meta:
        model = Client
        fields = (
            "id",
            "name",
            "category",
            "info",
            "parameter",
        )
        read_only_fields = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ("id", "name", "url", "client", "state")
        read_only_fields = ("id",)
