import base64
from typing import Optional
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_user)])


class GenerateIn(BaseModel):
    prompt: str
    mode: str = "text_to_image"          # text_to_image | image_to_image
    source_image_base64: Optional[str] = None


@router.post("/generate")
def generate(body: GenerateIn, db: Session = Depends(get_db)):
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")

    try:
        if body.mode == "image_to_image":
            api_key = services.get_setting(db, "ai_api_key", "")
            if not api_key:
                raise HTTPException(400, "Stability AI API key required (set it in Settings).")
            if not body.source_image_base64:
                raise HTTPException(400, "Source image required for image-to-image.")
            img = base64.b64decode(body.source_image_base64.split(",")[-1])
            resp = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/image-to-image",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"init_image": img},
                data={"text_prompts[0][text]": prompt, "text_prompts[0][weight]": 1,
                      "image_strength": 0.35, "steps": 30},
                timeout=90)
            resp.raise_for_status()
            artifacts = resp.json().get("artifacts", [])
            if not artifacts:
                raise HTTPException(502, "No image returned from AI service.")
            data = base64.b64decode(artifacts[0]["base64"])
        else:
            url = (f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
                   "?width=512&height=512&nologo=true&model=flux")
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            data = resp.content
    except requests.RequestException as e:
        raise HTTPException(502, f"AI service error: {e}")

    return {"image_base64": "data:image/png;base64," + base64.b64encode(data).decode()}


class SaveIn(BaseModel):
    name: Optional[str] = ""
    prompt: Optional[str] = ""
    mode: str = "text_to_image"
    image_base64: str


@router.post("/save")
def save_design(body: SaveIn, db: Session = Depends(get_db)):
    d = models.AIDesign(name=body.name or "Design", prompt=body.prompt, style=body.mode,
                        result_image_path=body.image_base64)
    db.add(d); db.commit(); db.refresh(d)
    return {"id": d.id}


@router.get("/gallery")
def gallery(db: Session = Depends(get_db), limit: int = 20):
    rows = db.query(models.AIDesign).order_by(models.AIDesign.id.desc()).limit(limit).all()
    return [{"id": d.id, "name": d.name, "prompt": d.prompt,
             "image": d.result_image_path,
             "created_at": d.created_at.isoformat() if d.created_at else ""}
            for d in rows]


@router.delete("/gallery/{design_id}")
def delete_design(design_id: int, db: Session = Depends(get_db)):
    d = db.query(models.AIDesign).get(design_id)
    if d: db.delete(d); db.commit()
    return {"ok": True}
