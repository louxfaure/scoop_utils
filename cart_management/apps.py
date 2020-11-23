from django.apps import AppConfig


class CartManagementConfig(AppConfig):
    name = 'cart_management'
    verbose_name = 'Gestion des réservations'

    def ready(self):
        from cart_management import signals
