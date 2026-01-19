import re
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .models import Company, Category, Region, District, Unit, Direction, CompanyPhone, EmployeeCompany, Position

DEFAULT_DIRECTOR_POSITION = "Директор"


def _pick_director(company: Company) -> EmployeeCompany | None:
    qs = company.employee_company.select_related("position").all()
    director = qs.filter(position__name__iexact=DEFAULT_DIRECTOR_POSITION).first()
    return director or qs.first()


def _split_list(value: str, sep: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in str(value).split(sep) if x.strip()]


def _norm_phone(p: str) -> str | None:
    if not p:
        return None
    raw = p.strip()
    digits = re.sub(r"\D+", "", raw)

    # УЗ: 9 цифр -> +998..., 12 цифр и начинается с 998 -> +998...
    if len(digits) == 9:
        return "+998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    # иначе вернём хотя бы цифры, если похоже на номер
    if len(digits) >= 7:
        return digits
    return None


class CompanyResource(resources.ModelResource):
    # FK по имени/коду
    category = fields.Field(
        attribute="category",
        column_name="category",
        widget=ForeignKeyWidget(Category, "name"),
    )
    region = fields.Field(
        attribute="region",
        column_name="region_code",
        widget=ForeignKeyWidget(Region, "code"),
    )

    district = fields.Field(
        attribute="district",
        column_name="district_code",
        widget=ForeignKeyWidget(District, "code"),
    )
    unit = fields.Field(
        attribute="unit",
        column_name="unit",
        widget=ForeignKeyWidget(Unit, "short_name"),
    )

    # M2M в одной колонке
    directions = fields.Field(column_name="directions")

    # телефоны в одной колонке
    phones = fields.Field(column_name="phones")

    director_position = fields.Field(column_name="director_position")
    director_last_name = fields.Field(column_name="director_last_name")
    director_first_name = fields.Field(column_name="director_first_name")
    director_middle_name = fields.Field(column_name="director_middle_name")

    class Meta:
        model = Company
        import_id_fields = ("inn",)          # upsert по ИНН (у тебя unique) :contentReference[oaicite:3]{index=3}
        fields = (
            "inn",
            "name",
            "category",
            "region",
            "district",
            "annual_capacity",
            "unit",
            "number_of_jobs",
            "description",
            "directions",
            "phones",

            "director_position",
            "director_last_name",
            "director_first_name",
            "director_middle_name",
        )
        skip_unchanged = True
        report_skipped = True

    # ----- EXPORT -----
    def dehydrate_directions(self, obj):
        # экспортируем названия направлений через |
        return " | ".join(obj.directions.values_list("title", flat=True))

    def dehydrate_phones(self, obj):
        # экспортируем телефоны через ;
        return "; ".join(obj.phones.values_list("phone", flat=True))

    def dehydrate_director_position(self, obj):
        e = _pick_director(obj)
        return e.position.name if e else ""

    def dehydrate_director_last_name(self, obj):
        e = _pick_director(obj)
        return e.last_name or "" if e else ""

    def dehydrate_director_first_name(self, obj):
        e = _pick_director(obj)
        return e.first_name or "" if e else ""

    def dehydrate_director_middle_name(self, obj):
        e = _pick_director(obj)
        return e.middle_name or "" if e else ""

    def dehydrate_director_phone(self, obj):
        e = _pick_director(obj)
        return e.phone or "" if e else ""

    def dehydrate_director_email(self, obj):
        e = _pick_director(obj)
        return e.email or "" if e else ""

    # ----- IMPORT -----
    def before_import_row(self, row, **kwargs):
        # нормализуем ИНН (Excel любит делать 123.0)
        if row.get("inn"):
            row["inn"] = str(row["inn"]).replace(".0", "").strip()

    def after_save_instance(self, instance, row, **kwargs):
        # directions
        dirs_raw = row.get("directions") or ""
        titles = _split_list(dirs_raw.replace(",", "|"), "|")
        if titles and instance.category_id:
            dir_objs = []
            for t in titles:
                d, _ = Direction.objects.get_or_create(category=instance.category, title=t)
                dir_objs.append(d)
            instance.directions.set(dir_objs)

        # phones
        phones_raw = row.get("phones") or ""
        parts = []
        # допускаем ; или , или перенос строки
        tmp = str(phones_raw).replace("\n", ";").replace(",", ";")
        parts = _split_list(tmp, ";")

        cleaned = []
        for p in parts:
            n = _norm_phone(p)
            if n:
                cleaned.append(n)

        if cleaned:
            # делаем "replace": перезаписываем номера компании по файлу
            CompanyPhone.objects.filter(company=instance).delete()
            for i, p in enumerate(dict.fromkeys(cleaned)):  # unique сохраняя порядок
                CompanyPhone.objects.create(
                    company=instance,
                    phone=p,
                    is_primary=(i == 0),
                )

        pos_name = str(row.get("director_position") or "").strip() or DEFAULT_DIRECTOR_POSITION
        last_name = str(row.get("director_last_name") or "").strip()
        first_name = str(row.get("director_first_name") or "").strip()
        middle_name = str(row.get("director_middle_name") or "").strip() or None

        # создаём сотрудника только если есть хоть что-то адекватное по ФИО
        if last_name or first_name:
            position, _ = Position.objects.get_or_create(name=pos_name)

            emp, _ = EmployeeCompany.objects.get_or_create(
                company=instance,
                position=position,
                last_name=last_name or None,
                first_name=first_name or None,
                middle_name=middle_name,
            )
