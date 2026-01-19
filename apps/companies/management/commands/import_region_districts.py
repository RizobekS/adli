from django.core.management.base import BaseCommand
from apps.companies.models import Region, District

import pandas as pd


class Command(BaseCommand):
    help = "Импорт регионов и районов/городов из Excel (коды 4 и 7 знаков)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Путь к Excel файлу (.xlsx)")

    def handle(self, *args, **options):
        path = options["file"]
        df = pd.read_excel(path)

        col_code = "Код района (города)"
        col_name = "Наименование региона (города)"

        created_regions = updated_regions = 0
        created_districts = updated_districts = 0

        # 1) регионы (код длиной 4)
        regions_map = {}
        for _, row in df.iterrows():
            code = str(row[col_code]).strip()
            name = str(row[col_name]).strip()
            if len(code) != 4:
                continue

            obj, created = Region.objects.update_or_create(
                code=code,
                defaults={"name": name},
            )
            regions_map[code] = obj
            if created:
                created_regions += 1
            else:
                updated_regions += 1

        # 2) районы/города (код длиной 7), первые 4 цифры = регион
        for _, row in df.iterrows():
            code = str(row[col_code]).strip()
            name = str(row[col_name]).strip()
            if len(code) != 7:
                continue

            region_code = code[:4]
            region = regions_map.get(region_code) or Region.objects.filter(code=region_code).first()
            if not region:
                self.stdout.write(self.style.WARNING(f"Пропущено: {code} {name} (нет региона {region_code})"))
                continue

            obj, created = District.objects.update_or_create(
                code=code,
                defaults={"name": name, "region": region},
            )
            if created:
                created_districts += 1
            else:
                updated_districts += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово. Регионы: +{created_regions} / обновлено {updated_regions}; "
            f"Районы: +{created_districts} / обновлено {updated_districts}"
        ))
