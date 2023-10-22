import datetime

import backend.notifications as note
from backend.import_view import import_pricelist
from marketplace.celery import celery_app


@celery_app.task
def celery_send_note(name_function, args):
    if name_function == "email_confirmation" in name_function:
        note.email_confirmation(*args)
        return
    if name_function == "notific_delete_profile":
        note.notific_delete_profile(*args)
        return
    if name_function == "reset_password_created":
        note.reset_password_created(args)
        return
    if name_function == "notific_new_order":
        note.notific_new_order(*args)
        return
    if name_function == "notific_new_state_order":
        note.notific_new_state_order(*args)
        return


@celery_app.task
def celery_import_pricelist(data, shop, email):
    result = import_pricelist(data, shop)
    note.notific_import_pricelist(email, result, datetime.datetime.now())
