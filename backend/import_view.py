from django.db import IntegrityError

from backend.models import (Category, Parameter, Product, ProductInfo,
                            ProductParameter, Shop)


def import_pricelist(data, shop_id):
    shop = Shop.objects.get(id=shop_id)
    for category in data["categories"]:
        if (
            "id" in category.keys()
            and category["id"]
            and type(category["id"]) == int
            and "name" in category.keys()
            and category["name"]
        ):
            try:
                category_object = Category.objects.get_or_create(
                    id=category["id"],
                    name=category["name"],
                )[0]
                category_object.shop.add(shop.id)
                category_object.save()
            except IntegrityError as error:
                return {"Errors": str(error)}
            else:
                ProductInfo.objects.filter(shop=shop.id).delete()
                for item in data["goods"]:
                    if type(item) == dict and "name" in item.keys() and item["name"]:
                        try:
                            product = Product.objects.get_or_create(
                                name=item["name"],
                                category=Category.objects.get(id=item["category"]),
                            )[0]
                            product_info = ProductInfo.objects.create(
                                product=product,
                                external_id=item["id"],
                                model=item["model"],
                                price=item["price"],
                                price_rrc=item["price_rrc"],
                                quantity=item["quantity"],
                                shop=shop,
                            )
                        except IntegrityError as error:
                            return {"Errors": str(error)}
                        else:
                            for name, value in item["parameters"].items():
                                if name and value:
                                    try:
                                        parameter_object = (
                                            Parameter.objects.get_or_create(name=name)[
                                                0
                                            ]
                                        )
                                        ProductParameter.objects.create(
                                            product_info=product_info,
                                            parameter=parameter_object,
                                            value=value,
                                        )
                                    except IntegrityError as error:
                                        return {"Errors": str(error)}
                                    else:
                                        continue
                                else:
                                    return {
                                        "Error": "Ошибка при обработки значений 'parameters'. Не указаны даннные - (name and value)"
                                    }
                    else:
                        return {
                            "Error": "Ошибка при обработки значений 'goods'. Не указаны даннные или неверный тип данных (name)"
                        }
        else:
            return {
                "Error": "Ошибка при обработки значений 'categories'. Не указаны даннные или неверный тип данных"
            }
    return True
