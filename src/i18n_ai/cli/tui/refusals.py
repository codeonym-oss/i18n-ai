from ...application.contract import ApplicationException
from ...di import InfraException
from ...domain.contract import DomainException

# What the mediator refuses with: shown, and the screen stays as it was.
REFUSALS = (DomainException, ApplicationException, InfraException)
