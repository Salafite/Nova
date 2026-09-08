from modules.crm.models.crm import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    SupplierCreate, SupplierUpdate, SupplierResponse,
)
from modules.crm.models.crm_lead import (
    LeadCreate, LeadUpdate, LeadResponse,
    LeadActivityCreate, LeadActivityUpdate, LeadActivityResponse,
    OpportunityCreate, OpportunityUpdate, OpportunityResponse,
    OpportunityLineCreate, OpportunityLineUpdate, OpportunityLineResponse,
)
from modules.crm.models.product_supplier import (
    ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse,
)
from modules.crm.models.customer_communication import (
    CustomerCommunicationCreate, CustomerCommunicationUpdate, CustomerCommunicationResponse,
    CommunicationStatusUpdate, CustomerCommunicationTimelineQuery,
    CustomerReminderPreferencesUpdate, CustomerReminderPreferencesResponse,
    CUSTOMER_COMMUNICATION_REPO,
)
