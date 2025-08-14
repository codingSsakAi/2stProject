from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self):
        # 템플릿 태그 라이브러리 등록
        import chatbot.templatetags.markdown_extras
