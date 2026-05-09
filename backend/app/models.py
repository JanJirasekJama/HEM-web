"""Import all SQLAlchemy models so test and migration metadata is complete."""

from app.core import models as core_models  # noqa: F401
from app.modules.backups import models as backup_models  # noqa: F401
from app.modules.cash import models as cash_models  # noqa: F401
from app.modules.catalog import models as catalog_models  # noqa: F401
from app.modules.communication import models as communication_models  # noqa: F401
from app.modules.dashboard import models as dashboard_models  # noqa: F401
from app.modules.housekeeping import models as housekeeping_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.invoicing import models as invoicing_models  # noqa: F401
from app.modules.migration import models as migration_models  # noqa: F401
from app.modules.reporting import models as reporting_models  # noqa: F401
from app.modules.tasks import models as task_models  # noqa: F401

