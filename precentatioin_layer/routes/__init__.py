from .clinic_route import clinicBP
from .doctor_route import doctorBP
from .reception_route import receptionBP
# from .auth_route import auth_bp
from .api_route import apiBP
from .patient_route import patientBP

__all__ = ['clinicBP', 'doctorBP', 'receptionBP', 'auth_bp', 'apiBP', 'patientBP']