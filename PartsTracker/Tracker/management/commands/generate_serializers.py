# scripts/generate_serializers.py

from django.apps import apps

HEADER = """# This file is auto-generated. Do not edit manually.
from rest_framework import serializers
from {your_app_name}.models import {model_imports}
"""

TEMPLATE = """
class {serializer_name}(serializers.ModelSerializer):
    class Meta:
        model = {model_name}
        fields = '__all__'
"""

def generate_serializers(output_file, app_label):
    models = apps.get_app_config(app_label).get_models()
    model_names = []
    body = ""

    for model in models:
        model_name = model.__name__
        serializer_name = f"{model_name}Serializer"
        model_names.append(model_name)
        body += TEMPLATE.format(serializer_name=serializer_name, model_name=model_name)

    header = HEADER.format(
        your_app_name=app_label,
        model_imports=", ".join(model_names)
    )

    with open(output_file, "w") as f:
        f.write(header)
        f.write(body)

    print(f"✅ Serializers written to {output_file}")


# Example usage:
# python manage.py shell < scripts/generate_serializers.py
if __name__ == "__main__":
    generate_serializers("tracker/generated_serializers.py", "tracker")