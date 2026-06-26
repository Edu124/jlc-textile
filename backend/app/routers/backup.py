import json
from datetime import datetime, date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from ..db import get_db, Base
from ..auth import require_user
from .. import models  # noqa: F401  (ensures tables are registered)

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(require_user)])


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


@router.get("")
def download_backup(db: Session = Depends(get_db)):
    """Full database export as a portable JSON file (the 'safety copy')."""
    dump = {"_meta": {"app": "JLC Textile Manager", "exported_at": datetime.utcnow().isoformat(),
                      "version": 2}}
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        table = cls.__tablename__
        cols = [c.name for c in inspect(cls).columns]
        rows = db.query(cls).all()
        dump[table] = [{c: _serialize(getattr(r, c)) for c in cols} for r in rows]

    payload = json.dumps(dump, ensure_ascii=False, indent=2)
    fname = f"jlc_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    return Response(content=payload, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
