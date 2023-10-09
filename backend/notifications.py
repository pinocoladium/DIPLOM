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
    client = Client.objects.filter(id=client_id).update(password=hashed_password)

    # send_mail(
    #     "СБРОС ПАРОЛЯ",
    #     f"НОВЫЙ ПАРОЛЬ ОТ ВАШЕГО АККАУНТА {client.data}: {new_password}",
    #     "from@example.com",
    #     [f"{client.email}"],
    #     fail_silently=False,
    # )
    
    print(f"НОВЫЙ ПАРОЛЬ ОТ ВАШЕГО АККАУНТА {client.data}: {new_password}")


# def new_order_signal(user_id, **kwargs):
#     """
#     отправяем письмо при изменении статуса заказа
#     """
#     # send an e-mail to the user
#     user = User.objects.get(id=user_id)
