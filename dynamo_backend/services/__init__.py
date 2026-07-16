from .auth_service import AuthDynamoService
from .centres_service import CentresDynamoService
from .sessions_service import SessionsDynamoService
from .children_service import ChildrenDynamoService
from .billing_service import BillingDynamoService
from .progress_service import ProgressDynamoService
from .roles_service import RolesDynamoService
from .otp_service import OtpDynamoService
from .root_access_service import RootAccessDynamoService
from .blacklist_service import BlacklistDynamoService

# Singleton instances
auth_db = AuthDynamoService()
centres_db = CentresDynamoService()
sessions_db = SessionsDynamoService()
children_db = ChildrenDynamoService()
billing_db = BillingDynamoService()
progress_db = ProgressDynamoService()
roles_db = RolesDynamoService()
otp_db = OtpDynamoService()
root_access_db = RootAccessDynamoService()
blacklist_db = BlacklistDynamoService()
