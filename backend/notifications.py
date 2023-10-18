from django.conf import settings
from django.core.mail import send_mail

from backend.auth import generate_password, hash_password
from backend.models import Client, ConfirmEmailToken


def email_confirmation(email, client_id):
    """
    Отправить письмо для подтрердждения электронной почты
    """

    ConfirmEmailToken.objects.filter(client=client_id).delete()

    token = ConfirmEmailToken.objects.create(client=Client.objects.get(id=client_id))

    # send_mail(
    #     "ПОДТВЕРЖДЕНИЕ ЭЛЕКТРОННОЙ ПОЧТЫ",
    #     f"ТОКЕН ДЛЯ ПОДТВЕРЖДЕНИЯ АККАУНТА {token.client}: {token.key}",
    #     "from@example.com",
    #     [f"{email}"],
    #     fail_silently=False,
    # )

    print(f"ТОКЕН ДЛЯ ПОДТВЕРЖДЕНИЯ АККАУНТА {token.client}: {token.key}")


def reset_password_created(client_id):
    """
    Отправить письмо с новым паролем для аккаунта и зменить его в базе данных
    """

    new_password = generate_password()
    hashed_password = hash_password(new_password)
    client = Client.objects.filter(id=client_id)
    client.update(password=hashed_password)

    # send_mail(
    #     "СБРОС ПАРОЛЯ",
    #     f"НОВЫЙ ПАРОЛЬ ОТ ВАШЕГО АККАУНТА {client[0].username}: {new_password}",
    #     "from@example.com",
    #     [f"{client.email}"],
    #     fail_silently=False,
    # )

    print(f"НОВЫЙ ПАРОЛЬ ОТ ВАШЕГО АККАУНТА {client[0].username}: {new_password}")


def notific_delete_profile(email, username):
    """
    Отправить уведомление об удалении профиля
    """

    # send_mail(
    #     "УДАЛЕНИЕ ПРОФИЛЯ",
    #     f"УВЕДОМЛЯЕМ ВАС ОБ УДАЛЕНИИ ВАШЕГО АККАУНТА {username}",
    #     "from@example.com",
    #     [f"{email}"],
    #     fail_silently=False,
    # )

    print(f"УВЕДОМЛЯЕМ ВАС ОБ УДАЛЕНИИ ВАШЕГО АККАУНТА {username}")


def notific_new_order(email, order_id):
    """
    отправяем письмо при размещении заказа
    """
    # send_mail(
    #     "РАЗМЕЩЕНИЕ ЗАКАЗА",
    #     f"УВЕДОМЛЯЕМ ВАС О РАЗМЕЩЕНИИ ВАШЕГО ЗАКАЗА ПОД НОМЕРОМ - {order_id}",
    #     "from@example.com",
    #     [f"{email}"],
    #     fail_silently=False,
    # )

    print(f"УВЕДОМЛЯЕМ ВАС О РАЗМЕЩЕНИИ ВАШЕГО ЗАКАЗА ПОД НОМЕРОМ - {order_id}")


def notific_new_state_order(client, order_id, state):
    """
    отправяем письмо при изменении статуса заказа
    """

    # send_mail(
    #     "ИЗМЕНЕНИЕ СТАТУСА ЗАКАЗА",
    #     f"УВЕДОМЛЯЕМ ВАС ОБ ИЗМЕНЕНИИ СТАТУСА ВАШЕГО ЗАКАЗА ПОД НОМЕРОМ - {id_order}. НОВЫЙ СТАТУС - {state}",
    #     "from@example.com",
    #     [f"{client.email}"],
    #     fail_silently=False,
    # )

    print(
        f"УВЕДОМЛЯЕМ ВАС ОБ ИЗМЕНЕНИИ СТАТУСА ВАШЕГО ЗАКАЗА ПОД НОМЕРОМ - {order_id}. НОВЫЙ СТАТУС - {state}"
    )
