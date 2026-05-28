"""
models/company.py — CompanyRecord dataclass.
"""
from dataclasses import dataclass


@dataclass
class CompanyRecord:
    record_id: str = ""
    submitted_at: str = ""
    lang: str = "zh"
    status: str = "新需求"
    company_name: str = ""
    industry: str = ""
    company_address: str = ""
    contact_name: str = ""
    contact_title: str = ""
    telegram_username: str = ""
    telegram_user_id: int = 0
    phone_whatsapp: str = ""
    position_title: str = ""
    headcount: str = ""
    work_location: str = ""
    salary_range: str = ""
    working_hours: str = ""
    language_requirement: str = ""
    experience_requirement: str = ""
    provides_accommodation: str = "No"
    provides_visa: str = "No"
    start_date_requirement: str = ""
    job_description: str = ""
    accepts_service_fee_terms: str = "No"
    company_docs_drive_link: str = ""
    notes: str = ""
    ai_summary: str = ""
    ai_tags: str = ""
    raw_json: str = ""
    internal_notes: str = ""
    assigned_hr: str = ""
    last_updated: str = ""

    def to_row(self) -> list[str]:
        return [
            self.record_id, self.submitted_at, self.lang, self.status,
            self.company_name, self.industry, self.company_address,
            self.contact_name, self.contact_title,
            self.telegram_username, str(self.telegram_user_id),
            self.phone_whatsapp, self.position_title, self.headcount,
            self.work_location, self.salary_range, self.working_hours,
            self.language_requirement, self.experience_requirement,
            self.provides_accommodation, self.provides_visa,
            self.start_date_requirement, self.job_description,
            self.accepts_service_fee_terms, self.company_docs_drive_link,
            self.notes, self.ai_summary, self.ai_tags, self.raw_json,
            self.internal_notes, self.assigned_hr, self.last_updated,
        ]
