from typing import Annotated, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

Money = Annotated[float, Field(allow_inf_nan=False)]
NonNeg = Field(default=0, ge=0)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)
    admin_code: str = Field(default="", max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    citizen: bool = False
    green_card: bool = False
    visa: str = Field(default="", max_length=40)
    country: str = Field(default="", max_length=60)
    first_entry_year: int = Field(default=0, ge=0, le=2100)   # first year in the U.S. (F/J/M/Q: first year in that status)
    days_current: int = Field(default=0, ge=0, le=366)
    days_prior1: int = Field(default=0, ge=0, le=366)
    days_prior2: int = Field(default=0, ge=0, le=366)
    # days of the above spent in F/J/M/Q status (None = all days if the visa is F/J/M/Q, else none)
    exempt_days_current: Optional[int] = Field(default=None, ge=0, le=366)
    exempt_days_prior1: Optional[int] = Field(default=None, ge=0, le=366)
    exempt_days_prior2: Optional[int] = Field(default=None, ge=0, le=366)
    prior_exempt_years: Optional[int] = Field(default=None, ge=0, le=60)
    first_nonexempt_day: str = Field(default="", max_length=10)   # ISO date: residency starting date
    is_student: bool = False
    # Form 8843 details
    visa_entry_date: str = Field(default="", max_length=10)
    visa_history: str = Field(default="", max_length=300)          # 8843 line 10/11: status per prior year
    school_phone: str = Field(default="", max_length=120)
    program_director: str = Field(default="", max_length=200)      # 8843 line 10 (director of program)
    previous_visa: str = Field(default="", max_length=40)
    visa_by_year: dict[str, str] = {}                               # 8843 lines 7/11: {"2023": "F-1", ...}
    passport_country: str = Field(default="", max_length=60)
    passport_number: str = Field(default="", max_length=30)
    tax_residence_country: str = Field(default="", max_length=60)   # Schedule OI item B
    applied_green_card: bool = False                                # Schedule OI C / 8843 line 13
    filed_prior_return: bool = False                                # Schedule OI item I
    prior_return_info: str = Field(default="", max_length=60)       # e.g. "2024 1040-NR"
    treaty_prior_months: int = Field(default=0, ge=0, le=600)       # Schedule OI item L(c)
    trips: list[dict[str, str]] = []                                # Schedule OI item G: [{entered, departed}]
    health_coverage: bool = True                                    # CA 540 line 92 (ISR)


class W2In(BaseModel):
    employer: str = Field(default="", max_length=120)
    ein: str = Field(default="", max_length=12)
    wages: Money = NonNeg                    # box 1
    fed_withholding: Money = NonNeg          # box 2
    ss_wages: Money = NonNeg                 # box 3
    ss_tax: Money = NonNeg                   # box 4
    medicare_wages: Optional[Money] = Field(default=None, ge=0)   # box 5
    medicare_tax: Money = NonNeg             # box 6
    state: str = Field(default="", max_length=2)  # box 15
    state_wages: Money = NonNeg              # box 16
    state_withholding: Money = NonNeg        # box 17


FilingStatus = Literal["single", "mfj", "mfs", "hoh", "qss"]


class DependentIn(BaseModel):
    first_name: str = Field(default="", max_length=40)
    last_name: str = Field(default="", max_length=40)
    ssn: str = Field(default="", max_length=11)
    relationship: str = Field(default="", max_length=30)       # e.g. Son, Daughter, Parent
    lived_with_you: bool = True       # more than half of the year
    lived_in_us: bool = True
    full_time_student: bool = False
    disabled: bool = False
    credit: Literal["ctc", "odc", "none"] = "ctc"   # ctc: under 17 with an SSN; odc: other dependent


class PayerIn(BaseModel):
    name: str = Field(default="", max_length=60)
    amount: Money = NonNeg


class SaleIn(BaseModel):
    """One Form 8949 row (sales that cannot go straight onto Schedule D line 1a/8a)."""
    description: str = Field(default="", max_length=60)      # (a) e.g. "100 sh XYZ"
    date_acquired: str = Field(default="", max_length=10)    # (b) MM/DD/YYYY or VARIOUS
    date_sold: str = Field(default="", max_length=10)        # (c)
    proceeds: Money = NonNeg                                  # (d)
    basis: Money = NonNeg                                     # (e)
    code: str = Field(default="", max_length=6)              # (f) adjustment code(s)
    adjustment: Money = 0                                     # (g) + or -
    term: Literal["short", "long"] = "short"
    reporting: Literal["basis_reported", "basis_not_reported", "no_form"] = "basis_not_reported"
    digital_asset: bool = False                               # reported on 1099-DA (boxes G-L)


class StudentIn(BaseModel):
    """Form 8863 Part III (one student)."""
    name: str = Field(default="", max_length=60)        # blank = the taxpayer
    ssn: str = Field(default="", max_length=11)
    school_name: str = Field(default="", max_length=80)
    school_address: str = Field(default="", max_length=120)
    school_ein: str = Field(default="", max_length=10)
    got_1098t_2025: bool = True
    got_1098t_2024_box7: bool = False
    aotc_claimed_4_years: bool = False      # line 23
    half_time: bool = True                  # line 24
    completed_4_years: bool = False         # line 25
    felony_drug: bool = False               # line 26
    refund_restricted: Optional[bool] = None   # line 7: under-24 rule applies (must answer if under 24)


class BusinessIn(BaseModel):
    """Schedule C. Expenses by category (line numbers in comments)."""
    description: str = Field(default="", max_length=60)      # A: principal business or profession
    code: str = Field(default="", max_length=6)              # B: 6-digit business code
    name: str = Field(default="", max_length=60)             # C
    ein: str = Field(default="", max_length=10)              # D
    gross_receipts: Money = NonNeg                           # 1
    returns: Money = NonNeg                                  # 2
    advertising: Money = NonNeg                              # 8
    car_truck: Money = NonNeg                                # 9
    commissions: Money = NonNeg                              # 10
    contract_labor: Money = NonNeg                           # 11
    insurance: Money = NonNeg                                # 15
    legal_professional: Money = NonNeg                       # 17
    office: Money = NonNeg                                   # 18
    supplies: Money = NonNeg                                 # 22
    taxes_licenses: Money = NonNeg                           # 23
    travel: Money = NonNeg                                   # 24a
    meals_total: Money = NonNeg                              # 24b is 50% of this
    utilities: Money = NonNeg                                # 25
    other_expenses: Money = NonNeg                           # 27b / Part V
    other_description: str = Field(default="", max_length=60)


class IncomeIn(BaseModel):
    filing_status: FilingStatus = "single"
    w2s: list[W2In] = []
    wages_nr_period: Money = NonNeg          # dual-status: wages earned before residency start
    # Form 1042-S
    comp_1042s: Money = NonNeg               # treaty-exempt pay on 1042-S (income codes 17-20)
    scholarship_1042s: Money = NonNeg        # taxable scholarship on 1042-S (income code 16)
    withholding_1042s: Money = NonNeg        # 1042-S federal tax withheld
    # 1099 / other
    interest: Money = NonNeg
    dividends: Money = NonNeg
    qualified_dividends: Money = NonNeg
    capital_gain_lt: Money = 0
    capital_gain_st: Money = 0
    se_income: Money = 0                     # net profit (can be a loss)
    scholarship_taxable: Money = NonNeg      # taxable scholarship not on W-2/1042-S
    withholding_1099: Money = NonNeg
    # deductions
    student_loan_interest: Money = NonNeg
    itemized: Money = NonNeg                 # legacy total itemized override
    state_tax_other: Money = NonNeg          # state income tax paid besides W-2 box 17
    charitable: Money = NonNeg               # Schedule A line 11 (cash/check)
    charitable_noncash: Money = NonNeg       # Schedule A line 12
    medical_expenses: Money = NonNeg         # Schedule A line 1 (unreimbursed)
    real_estate_tax: Money = NonNeg          # Schedule A line 5b
    mortgage_interest: Money = NonNeg        # Schedule A line 8a (Form 1098 box 1)
    other_itemized: Money = NonNeg           # Schedule A line 16 (only items listed in the instructions)
    qualified_tips: Money = NonNeg
    qualified_overtime: Money = NonNeg
    has_ssn: bool = True
    age: int = Field(default=0, ge=0, le=120)
    spouse_age: int = Field(default=0, ge=0, le=120)   # married filing jointly
    # credits
    tuition_paid: Money = NonNeg
    education_credit_type: Literal["none", "aotc", "llc"] = "none"
    qualifying_children: int = Field(default=0, ge=0, le=20)
    other_dependents: int = Field(default=0, ge=0, le=20)
    estimated_payments: Money = NonNeg
    # details for the official forms
    dependents: list[DependentIn] = Field(default=[], max_length=10)
    interest_payers: list[PayerIn] = Field(default=[], max_length=14)     # Schedule B Part I
    dividend_payers: list[PayerIn] = Field(default=[], max_length=15)     # Schedule B Part II
    foreign_accounts: bool = False           # any foreign bank/brokerage account (Schedule B line 7a)
    fbar_required: bool = False              # foreign accounts together over $10,000 at any time
    foreign_account_countries: str = Field(default="", max_length=120)
    foreign_trust: bool = False
    # Form 1099-B totals for sales with basis reported to the IRS and no adjustments (Schedule D 1a / 8a)
    st_proceeds: Money = NonNeg
    st_basis: Money = NonNeg
    lt_proceeds: Money = NonNeg
    lt_basis: Money = NonNeg
    st_loss_carryover: Money = NonNeg        # from last year's Capital Loss Carryover Worksheet
    lt_loss_carryover: Money = NonNeg
    business: Optional[BusinessIn] = None    # Schedule C
    student: Optional["StudentIn"] = None    # Form 8863 Part III
    sales: list[SaleIn] = Field(default=[], max_length=200)   # Form 8949 rows
    # state
    state: str = Field(default="CA", max_length=2)
    ca_full_year_resident: bool = True       # (name kept for compatibility) full-year resident of `state`
    ca_income_ratio: float = Field(default=1.0, ge=0, le=1)
    state_source_income: Optional[Money] = Field(default=None, ge=0)
    state_itemized: Money = NonNeg
    ca_renter: bool = False


class AnswersIn(BaseModel):
    answers: dict


class TaxpayerIn(BaseModel):
    first_name: str = Field(default="", max_length=60)
    middle_initial: str = Field(default="", max_length=1)
    last_name: str = Field(default="", max_length=60)
    ssn: str = Field(default="", max_length=11)
    address: str = Field(default="", max_length=120)
    apt: str = Field(default="", max_length=20)
    city: str = Field(default="", max_length=60)
    state: str = Field(default="", max_length=2)
    zip: str = Field(default="", max_length=10)
    city_state_zip: str = Field(default="", max_length=120)    # legacy single-line field
    foreign_country: str = Field(default="", max_length=60)
    foreign_province: str = Field(default="", max_length=60)
    foreign_postal: str = Field(default="", max_length=20)
    occupation: str = Field(default="", max_length=60)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=120)
    date_of_birth: str = Field(default="", max_length=10)
    school: str = Field(default="", max_length=200)
    school_address: str = Field(default="", max_length=200)

IncomeIn.model_rebuild()
