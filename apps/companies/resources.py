import re
from decimal import Decimal, InvalidOperation

from import_export import resources, fields
from import_export.results import RowResult
from import_export.widgets import ForeignKeyWidget

from .models import (
    Company,
    Category,
    Region,
    District,
    Unit,
    Direction,
    CompanyPhone,
    EmployeeCompany,
    Position,
    CompanyDirectionStat,
)

DEFAULT_DIRECTOR_POSITION = "Директор"
DEFAULT_YEAR = 2026


# ---------------- helpers ----------------

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
    raw = str(p).strip()
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


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "x":
        return None
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _to_int(v) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _get_unit(unit_raw: str) -> Unit | None:
    s = (unit_raw or "").strip()
    if not s:
        return None
    return (
        Unit.objects.filter(short_name__iexact=s).first()
        or Unit.objects.filter(name__iexact=s).first()
    )

def _norm_name_key(s: str) -> str:
    s = (s or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    # маленькая нормализация кириллицы
    s = s.replace("Ё", "Е").replace("Й", "И")
    # выкинем точки/запятые и прочий шум
    s = re.sub(r"[^A-ZА-Я0-9 ]+", "", s)
    return s

def _director_key(last_name: str, first_name: str, middle_name: str | None) -> str:
    return " ".join(filter(None, [
        _norm_name_key(last_name),
        _norm_name_key(first_name),
        _norm_name_key(middle_name or ""),
    ])).strip()

def _find_or_create_director(company: Company, position: Position,
                             last_name: str, first_name: str, middle_name: str | None) -> EmployeeCompany:
    # кандидаты в пределах компании+позиции
    qs = EmployeeCompany.objects.filter(company=company, position=position)

    incoming_key = _director_key(last_name, first_name, middle_name)

    # 1) ищем точное совпадение по текущим полям (быстро)
    emp = qs.filter(
        last_name__iexact=last_name or "",
        first_name__iexact=first_name or "",
        middle_name__iexact=middle_name or "",
    ).first()
    if emp:
        return emp

    # 2) ищем "похожего" по нормализованному ключу
    for candidate in qs.only("id", "last_name", "first_name", "middle_name"):
        cand_key = _director_key(candidate.last_name or "", candidate.first_name or "", candidate.middle_name)
        if cand_key and incoming_key and cand_key == incoming_key:
            # обновим более полными данными, если у кандидата пусто
            changed = False
            if last_name and not candidate.last_name:
                candidate.last_name = last_name; changed = True
            if first_name and not candidate.first_name:
                candidate.first_name = first_name; changed = True
            if middle_name and not candidate.middle_name:
                candidate.middle_name = middle_name; changed = True
            if changed:
                candidate.save(update_fields=["last_name", "first_name", "middle_name"])
            return candidate

    # 3) не нашли - создаём
    emp, _ = EmployeeCompany.objects.get_or_create(
        company=company,
        position=position,
        last_name=last_name or None,
        first_name=first_name or None,
        middle_name=middle_name,
    )
    return emp


# ---------------- CompanyResource (паспорт компании) ----------------

class CompanyResource(resources.ModelResource):
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

    directions = fields.Field(column_name="directions")
    phones = fields.Field(column_name="phones")

    director_position = fields.Field(column_name="director_position")
    director_last_name = fields.Field(column_name="director_last_name")
    director_first_name = fields.Field(column_name="director_first_name")
    director_middle_name = fields.Field(column_name="director_middle_name")
    director_email = fields.Field(column_name="director_email")

    class Meta:
        model = Company
        import_id_fields = ("inn",)
        fields = (
            "inn",
            "name",
            "category",
            "region",
            "district",
            "description",
            "directions",
            "phones",
            "director_position",
            "director_last_name",
            "director_first_name",
            "director_middle_name",
            "director_email",
        )
        skip_unchanged = True
        report_skipped = True

    # ----- EXPORT -----
    def dehydrate_directions(self, obj):
        return " | ".join(obj.directions.values_list("title", flat=True))

    def dehydrate_phones(self, obj):
        return "; ".join(obj.phones.values_list("phone", flat=True))

    def dehydrate_director_position(self, obj):
        e = _pick_director(obj)
        return e.position.name if e and e.position else ""

    def dehydrate_director_last_name(self, obj):
        e = _pick_director(obj)
        return (e.last_name or "") if e else ""

    def dehydrate_director_first_name(self, obj):
        e = _pick_director(obj)
        return (e.first_name or "") if e else ""

    def dehydrate_director_middle_name(self, obj):
        e = _pick_director(obj)
        return (e.middle_name or "") if e else ""

    def dehydrate_director_email(self, obj):
        e = _pick_director(obj)
        return (e.email or "") if e else ""

    # ----- IMPORT -----
    def before_import_row(self, row, **kwargs):
        if row.get("inn"):
            row["inn"] = str(row["inn"]).replace(".0", "").strip()

        if (row.get("directions") or "").strip() and not (row.get("category") or "").strip():
            raise ValueError("Указаны directions, но не указана category (нельзя привязать направления).")

    def after_save_instance(self, instance, row, **kwargs):
        # sync primary -> m2m
        if instance.category_id:
            instance.categories.add(instance.category)

        # directions: "A | B | C"
        dirs_raw = row.get("directions") or ""
        titles = _split_list(str(dirs_raw).replace(",", "|"), "|")
        if titles:
            if not instance.category_id:
                raise ValueError("directions указаны, но company.category пустой.")
            dir_objs = []
            for t in titles:
                d, _ = Direction.objects.get_or_create(category=instance.category, title=t)
                dir_objs.append(d)
            instance.directions.set(dir_objs)

        # --- 3) phones MERGE (если заполнено) ---
        phones_raw = str(row.get("phones") or "").strip()
        if phones_raw:
            tmp = phones_raw.replace("\n", ";").replace(",", ";")
            parts = _split_list(tmp, ";")

            cleaned = []
            for p in parts:
                n = _norm_phone(p)
                if n:
                    cleaned.append(n)

            if cleaned:
                # уже имеющиеся телефоны компании
                existing = set(
                    CompanyPhone.objects.filter(company=instance).values_list("phone", flat=True)
                )

                has_primary = CompanyPhone.objects.filter(company=instance, is_primary=True).exists()

                # добавляем только новые
                for p in dict.fromkeys(cleaned):
                    if p in existing:
                        continue
                    CompanyPhone.objects.create(
                        company=instance,
                        phone=p,
                        is_primary=(not has_primary),
                    )
                    has_primary = True

        # director (email only)
        pos_name = str(row.get("director_position") or "").strip() or DEFAULT_DIRECTOR_POSITION
        last_name = str(row.get("director_last_name") or "").strip()
        first_name = str(row.get("director_first_name") or "").strip()
        middle_name = str(row.get("director_middle_name") or "").strip() or None
        email = str(row.get("director_email") or "").strip() or None

        if last_name or first_name:
            position, _ = Position.objects.get_or_create(name=pos_name)
            emp, _ = EmployeeCompany.objects.get_or_create(
                company=instance,
                position=position,
                last_name=last_name or None,
                first_name=first_name or None,
                middle_name=middle_name,
            )
            if email:
                emp.email = email
                emp.save(update_fields=["email"])


# ---------------- CompanyDirectionStatResource (главный импорт) ----------------

class CompanyDirectionStatResource(resources.ModelResource):
    """
    Импорт: 1 строка = 1 показатель (Company + Direction + Year).
    INN может повторяться сколько угодно раз — это нормально.
    """

    class Meta:
        model = CompanyDirectionStat
        fields = (
            "inn",
            "name",
            "category",
            "region_code",
            "district_code",
            "phones",
            "directions",
            "director_position", "director_last_name",
            "director_first_name", "director_middle_name", "director_email",
            "year",
            "unit",
            "annual_capacity",
            "volume_bln_sum",
            "number_of_jobs",
        )

    def before_import_row(self, row, **kwargs):
        if row.get("inn"):
            row["inn"] = str(row["inn"]).replace(".0", "").strip()

        if not (row.get("category") or "").strip():
            raise ValueError("category обязательна (нужна для направлений).")
        if not (row.get("directions") or "").strip():
            raise ValueError("directions обязательна (одно направление на строку).")

        if not (row.get("year") or "").strip():
            row["year"] = DEFAULT_YEAR

    def import_row(self, row, instance_loader, **kwargs):
        # --- 1) upsert Company ---
        inn = str(row.get("inn") or "").strip()
        if not inn:
            raise ValueError("inn пустой")

        name = str(row.get("name") or "").strip()
        category_name = str(row.get("category") or "").strip()

        category = Category.objects.filter(name=category_name).first()
        if not category:
            raise ValueError(f"Категория не найдена: {category_name}")

        region = None
        if row.get("region_code"):
            region = Region.objects.filter(code=str(row["region_code"]).strip()).first()

        district = None
        if row.get("district_code"):
            district = District.objects.filter(code=str(row["district_code"]).strip()).first()

        company, created = Company.objects.get_or_create(
            inn=inn,
            defaults={
                "name": name or inn,
                "category": category,
                "region": region,
                "district": district,
                "data_source": Company.DataSource.IMPORT,
                "verification_level": Company.VerificationLevel.HIGH,
            }
        )

        if created:
            pass
        else:
            changed_meta = False

            if company.data_source != Company.DataSource.IMPORT:
                company.data_source = Company.DataSource.IMPORT
                changed_meta = True

            if company.verification_level != Company.VerificationLevel.HIGH:
                company.verification_level = Company.VerificationLevel.HIGH
                changed_meta = True

            if changed_meta:
                company.save(update_fields=["data_source", "verification_level"])

        changed = False
        if name and company.name != name:
            company.name = name
            changed = True
        if company.category_id != category.id:
            company.category = category
            changed = True
        if region and company.region_id != region.id:
            company.region = region
            changed = True
        if district and company.district_id != district.id:
            company.district = district
            changed = True
        if changed:
            company.save()

        company.categories.add(category)

        # --- 2) Direction + M2M ---
        direction_title = str(row.get("directions") or "").strip()
        direction, _ = Direction.objects.get_or_create(category=category, title=direction_title)
        company.directions.add(direction)

        # --- 3) phones MERGE (если заполнено) ---
        phones_raw = str(row.get("phones") or "").strip()
        if phones_raw:
            tmp = phones_raw.replace("\n", ";").replace(",", ";")
            parts = _split_list(tmp, ";")

            cleaned = []
            for p in parts:
                n = _norm_phone(p)
                if n:
                    cleaned.append(n)

            if cleaned:
                # уже имеющиеся телефоны компании
                existing = set(
                    CompanyPhone.objects.filter(company=company).values_list("phone", flat=True)
                )

                has_primary = CompanyPhone.objects.filter(company=company, is_primary=True).exists()

                # добавляем только новые
                for p in dict.fromkeys(cleaned):
                    if p in existing:
                        continue
                    CompanyPhone.objects.create(
                        company=company,
                        phone=p,
                        is_primary=(not has_primary),
                    )
                    has_primary = True

        # --- 3.5) director upsert/merge ---
        pos_name = str(row.get("director_position") or "").strip() or DEFAULT_DIRECTOR_POSITION
        last_name = str(row.get("director_last_name") or "").strip()
        first_name = str(row.get("director_first_name") or "").strip()
        middle_name = str(row.get("director_middle_name") or "").strip() or None
        email = str(row.get("director_email") or "").strip() or None

        if last_name or first_name:
            position, _ = Position.objects.get_or_create(name=pos_name)

            # 1) Попытка найти существующего директора "умно"
            emp = _find_or_create_director(
                company=company,
                position=position,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            )

            # 2) Заполним email, если пришел
            if email and not emp.email:
                emp.email = email
                emp.save(update_fields=["email"])

        # --- 4) Stat upsert ---
        year = int(row.get("year") or DEFAULT_YEAR)
        qty = _to_decimal(row.get("annual_capacity"))
        unit_obj = _get_unit(str(row.get("unit") or ""))
        jobs = _to_int(row.get("number_of_jobs"))
        vol = _to_decimal(row.get("volume_bln_sum"))

        obj, created = CompanyDirectionStat.objects.update_or_create(
            company=company,
            direction=direction,
            year=year,
            defaults={
                "unit": unit_obj,
                "quantity": qty,
                "volume_bln_sum": vol,
                "jobs": jobs,
            }
        )

        res = RowResult()
        res.import_type = RowResult.IMPORT_TYPE_NEW if created else RowResult.IMPORT_TYPE_UPDATE
        res.object_id = obj.pk
        res.object_repr = str(obj)
        res.instance = obj
        return res


    def get_instance(self, instance_loader, row):
        return None