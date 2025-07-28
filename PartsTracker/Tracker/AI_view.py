from django.views.generic import TemplateView


class chat_ai_view(TemplateView):
    template_name = "tracker/chat.html"
