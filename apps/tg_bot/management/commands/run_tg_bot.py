from django.core.management.base import BaseCommand

from apps.tg_bot.bot.main import run_polling


class Command(BaseCommand):
    help = "Run Telegram bot via long polling"

    def handle(self, *args, **options):
        run_polling()