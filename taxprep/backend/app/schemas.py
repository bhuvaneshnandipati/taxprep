from pydantic import BaseModel, EmailStr, Field

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProfileIn(BaseModel):
    citizen: bool = False
    green_card: bool = False
    visa: str = ""
    country: str = ""
    first_entry_year: int = 0
    days_current: int = 0
    days_prior1: int = 0
    days_prior2: int = 0
    is_student: bool = False

class W2In(BaseModel):
    employer: str = ""
    wages: float = 0
    fed_withholding: float = 0
    state_withholding: float = 0

class IncomeIn(BaseModel):
    filing_status: str = "single"
    w2s: list[W2In] = []
    interest: float = 0
    dividends: float = 0
    qualified_dividends: float = 0
    capital_gain_lt: float = 0
    capital_gain_st: float = 0
    se_income: float = 0
    scholarship_taxable: float = 0
    student_loan_interest: float = 0
    itemized: float = 0
    tuition_paid: float = 0
    education_credit_type: str = "none"
    qualifying_children: int = 0
    other_dependents: int = 0
    estimated_payments: float = 0
    state: str = "CA"
    ca_full_year_resident: bool = True
    ca_income_ratio: float = 1.0
    ca_renter: bool = False

class AnswersIn(BaseModel):
    answers: dict

class TaxpayerIn(BaseModel):
    first_name: str = ""
    last_name: str = ""
    ssn: str = ""
    address: str = ""
    city_state_zip: str = ""
    school: str = ""
