from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from apps.agency.models import ProblemDirection


class ProblemDirectionResource(resources.ModelResource):
    # FK по имени/коду
    department = fields.Field(
        attribute="department",
        column_name="department",
        widget=ForeignKeyWidget(ProblemDirection, "name"),
    )

    class Meta:
        model = ProblemDirection
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True