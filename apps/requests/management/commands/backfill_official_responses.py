from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Prefetch

from apps.requests.models import Request, RequestOfficialResponse, RequestStep
from apps.requests.services import create_official_response_for_closed_request


class Command(BaseCommand):
    help = (
        "Create official responses for old closed requests from the latest request step "
        "and send email/Telegram notifications."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually create official responses and send notifications. Without this flag only prints a dry run.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Process at most this many matching requests.",
        )
        parser.add_argument(
            "--public-id",
            action="append",
            default=[],
            help="Limit to one or more public request numbers. Can be passed multiple times.",
        )
        parser.add_argument(
            "--request-id",
            action="append",
            type=int,
            default=[],
            help="Limit to one or more internal request IDs. Can be passed multiple times.",
        )
        parser.add_argument(
            "--source",
            choices=[Request.Source.PUBLIC_WEB, Request.Source.TELEGRAM, Request.Source.ADMIN_PANEL],
            help="Limit by request source.",
        )
        parser.add_argument(
            "--create-only",
            action="store_true",
            help="With --apply, create official response rows but do not send email or Telegram.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Print only the final summary.",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        if limit is not None and limit <= 0:
            raise CommandError("--limit must be greater than 0")

        apply = bool(options["apply"])
        create_only = bool(options["create_only"])
        quiet = bool(options["quiet"])

        qs = self._build_queryset(options)
        total_candidates = qs.count()
        if limit:
            qs = qs[:limit]

        stats = Counter(candidates=total_candidates)
        if not apply:
            self.stdout.write(self.style.WARNING("DRY RUN: add --apply to create responses and send notifications."))

        for request_obj in qs:
            stats["seen"] += 1
            step = self._latest_step(request_obj)
            if not step:
                stats["skipped_no_step"] += 1
                self._write_item(
                    quiet,
                    request_obj,
                    "SKIP no request steps",
                )
                continue

            response_text = (step.text or "").strip()
            if not response_text:
                stats["skipped_empty_step"] += 1
                self._write_item(
                    quiet,
                    request_obj,
                    f"SKIP latest step #{step.pk} is empty",
                )
                continue

            if not apply:
                stats["dry_run_ready"] += 1
                self._write_item(
                    quiet,
                    request_obj,
                    self._dry_run_label(request_obj, step),
                )
                continue

            try:
                result = create_official_response_for_closed_request(
                    request=request_obj,
                    actor=step.author,
                    response_text=response_text,
                    send_notifications=not create_only,
                )
            except Exception as exc:
                stats["errors"] += 1
                self._write_item(
                    quiet,
                    request_obj,
                    f"ERROR {exc}",
                    error=True,
                )
                continue

            response = result.response
            stats["created"] += 1
            stats[f"email_{response.email_status}"] += 1
            stats[f"telegram_{response.telegram_status}"] += 1
            self._write_item(
                quiet,
                request_obj,
                (
                    f"OK response=#{response.pk} "
                    f"email={response.get_email_status_display()} "
                    f"telegram={response.get_telegram_status_display()}"
                ),
            )

        self._print_summary(stats, apply=apply, limit=limit, create_only=create_only)

    def _build_queryset(self, options):
        steps_qs = RequestStep.objects.select_related("author").order_by("-created_at")
        qs = (
            Request.objects
            .filter(status=Request.Status.DONE)
            .annotate(official_response_count=Count("official_responses"))
            .filter(official_response_count=0)
            .select_related("company", "employee", "telegram_profile")
            .prefetch_related(Prefetch("steps", queryset=steps_qs, to_attr="backfill_steps"))
            .order_by("resolved_at", "id")
        )

        if options.get("public_id"):
            qs = qs.filter(public_id__in=options["public_id"])
        if options.get("request_id"):
            qs = qs.filter(id__in=options["request_id"])
        if options.get("source"):
            qs = qs.filter(source=options["source"])

        return qs

    @staticmethod
    def _latest_step(request_obj: Request) -> RequestStep | None:
        steps = getattr(request_obj, "backfill_steps", None)
        if steps is not None:
            return steps[0] if steps else None
        return request_obj.steps.select_related("author").order_by("-created_at").first()

    @staticmethod
    def _recipient_email(request_obj: Request) -> str:
        if request_obj.employee and request_obj.employee.email:
            return request_obj.employee.email
        if request_obj.telegram_profile and request_obj.telegram_profile.email:
            return request_obj.telegram_profile.email
        return ""

    def _dry_run_label(self, request_obj: Request, step: RequestStep) -> str:
        email = "yes" if self._recipient_email(request_obj) else "no"
        telegram = "yes" if request_obj.source == Request.Source.TELEGRAM else "no"
        author = step.author.get_username() if step.author_id else "-"
        return f"READY step=#{step.pk} author={author} email={email} telegram={telegram}"

    def _write_item(self, quiet: bool, request_obj: Request, label: str, *, error: bool = False) -> None:
        if quiet:
            return

        number = request_obj.public_id or request_obj.pk
        line = f"{number} source={request_obj.source}: {label}"
        if error:
            self.stderr.write(self.style.ERROR(line))
        else:
            self.stdout.write(line)

    def _print_summary(self, stats: Counter, *, apply: bool, limit: int | None, create_only: bool) -> None:
        mode = "APPLY" if apply else "DRY RUN"
        if create_only:
            mode += " / CREATE ONLY"

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{mode} summary"))
        self.stdout.write(f"Candidates without official response: {stats['candidates']}")
        if limit:
            self.stdout.write(f"Limit: {limit}")
        self.stdout.write(f"Seen: {stats['seen']}")
        self.stdout.write(f"Ready in dry run: {stats['dry_run_ready']}")
        self.stdout.write(f"Created: {stats['created']}")
        self.stdout.write(f"Skipped without steps: {stats['skipped_no_step']}")
        self.stdout.write(f"Skipped empty latest step: {stats['skipped_empty_step']}")
        self.stdout.write(f"Errors: {stats['errors']}")

        for status, _label in RequestOfficialResponse.DeliveryStatus.choices:
            self.stdout.write(f"Email {status}: {stats[f'email_{status}']}")
        for status, _label in RequestOfficialResponse.DeliveryStatus.choices:
            self.stdout.write(f"Telegram {status}: {stats[f'telegram_{status}']}")
