from typing import Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/settings", tags=["settings"],
                   dependencies=[Depends(require_user)])

# Keys the UI is allowed to read/write.
EDITABLE = [
    "company_name", "company_tagline", "company_slogan", "address", "gst_number",
    "phone", "email", "instagram", "footer_note1", "footer_note2",
    "logo_mode", "ai_api_key",
]


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    rows = {s.key: s.value for s in db.query(models.Setting).all()}
    return {k: rows.get(k, "") for k in EDITABLE}


class SettingsIn(BaseModel):
    values: Dict[str, str]


@router.put("")
def update_settings(body: SettingsIn, db: Session = Depends(get_db)):
    for key, value in body.values.items():
        if key in EDITABLE:
            services.set_setting(db, key, value)
    db.commit()
    return {"ok": True}
