"""
models/candidate.py — CandidateRecord dataclass.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateRecord:
    record_id: str = ""
    submitted_at: str = ""
    lang: str = "zh"
    status: str = "新提交"
    name: str = ""
    gender: str = ""
    age: str = ""
    nationality: str = ""
    current_city: str = ""
    telegram_username: str = ""
    telegram_user_id: int = 0
    phone_whatsapp: str = ""
    languages: str = ""
    education: str = ""
    years_experience: str = ""
    industry_experience: str = ""
    desired_position: str = ""
    desired_salary: str = ""
    preferred_locations: str = ""
    available_from: str = ""
    cambodia_experience: str = "No"
    needs_accommodation: str = "Not specified"
    needs_visa_support: str = "Not specified"
    resume_drive_link: str = ""
    attachment_drive_link: str = ""
    notes: str = ""
    ai_summary: str = ""
    ai_tags: str = ""
    ai_recommended_roles: str = ""
    ai_risk_notes: str = ""
    raw_json: str = ""
    internal_notes: str = ""
    assigned_hr: str = ""
    last_updated: str = ""

    def to_row(self) -> list[str]:
        """Return a list of values matching the Sheets column order."""
        return [
            self.record_id, self.submitted_at, self.lang, self.status,
            self.name, self.gender, self.age, self.nationality,
            self.current_city, self.telegram_username, str(self.telegram_user_id),
            self.phone_whatsapp, self.languages, self.education,
            self.years_experience, self.industry_experience,
            self.desired_position, self.desired_salary,
            self.preferred_locations, self.available_from,
            self.cambodia_experience, self.needs_accommodation,
            self.needs_visa_support, self.resume_drive_link,
            self.attachment_drive_link, self.notes,
            self.ai_summary, self.ai_tags, self.ai_recommended_roles,
            self.ai_risk_notes, self.raw_json,
            self.internal_notes, self.assigned_hr, self.last_updated,
        ]
