from django_restful_admin import site as rest
from django.apps import apps


# Register all models for REST API except the registered ones
for model in apps.get_models():
    if model in rest._registry:
        continue
    rest.register(model)
