from django.core.management.base import BaseCommand
from django.db import transaction

from apps.companies.models import Company, Direction, CompanyDirectionStat

DEFAULT_YEAR = 2026
LEGACY_DIRECTION_TITLE = "Общая мощность"


class Command(BaseCommand):
    help = "Move Company.annual_capacity/unit into CompanyDirectionStat and keep data unified."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
        parser.add_argument("--dry-run", action="store_true", default=False)

    @transaction.atomic
    def handle(self, *args, **opts):
        year = opts["year"]
        dry = opts["dry_run"]

        qs = (
            Company.objects
            .select_related("category", "unit")
            .exclude(annual_capacity__isnull=True)
        )

        created = 0
        updated = 0
        skipped = 0

        for c in qs.iterator(chunk_size=500):
            if not c.category_id:
                skipped += 1
                continue

            # direction "Общая мощность" внутри категории
            direction, _ = Direction.objects.get_or_create(
                category=c.category,
                title=LEGACY_DIRECTION_TITLE,
            )

            stat, was_created = CompanyDirectionStat.objects.update_or_create(
                company=c,
                direction=direction,
                year=year,
                defaults={
                    "unit": c.unit,
                    "quantity": c.annual_capacity,
                    "volume_bln_sum": None,
                }
            )
            created += int(was_created)
            updated += int(not was_created)

        if dry:
            raise SystemExit(f"[DRY RUN] created={created} updated={updated} skipped(no category)={skipped}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. created={created} updated={updated} skipped(no category)={skipped}"
        ))
