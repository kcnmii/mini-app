from __future__ import annotations

import base64
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db, SupplierProfile as SupplierProfileModel
from app.schemas.profile import SupplierProfile, SupplierProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])

UPLOADS_DIR = Path("data/uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
IMAGE_FIELDS = {"logo", "signature", "stamp"}


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _get_or_create_profile(db: Session) -> SupplierProfileModel:
    profile = db.query(SupplierProfileModel).filter(SupplierProfileModel.id == 1).first()
    if profile:
        return profile
    
    new_profile = SupplierProfileModel(id=1)
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


@router.get("", response_model=SupplierProfile)
async def get_profile(db: Session = Depends(get_db)) -> SupplierProfile:
    profile_model = _get_or_create_profile(db)
    # Convert model to dict for Pydantic
    data = {c.name: getattr(profile_model, c.name) for c in profile_model.__table__.columns}
    return SupplierProfile(**data)


@router.put("", response_model=SupplierProfile)
async def update_profile(payload: SupplierProfileUpdate, db: Session = Depends(get_db)) -> SupplierProfile:
    profile_model = _get_or_create_profile(db)
    fields = payload.model_dump(exclude_unset=True)
    
    for key, value in fields.items():
        setattr(profile_model, key, value)
        
    db.commit()
    db.refresh(profile_model)
    
    data = {c.name: getattr(profile_model, c.name) for c in profile_model.__table__.columns}
    return SupplierProfile(**data)


@router.post("/{image_type}")
async def upload_image(image_type: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> JSONResponse:
    if image_type not in IMAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {image_type}. Must be one of {IMAGE_FIELDS}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Accepted: {ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE // 1024 // 1024}MB")

    _ensure_uploads_dir()
    filename = f"{image_type}{ext}"
    file_path = UPLOADS_DIR / filename
    file_path.write_bytes(content)

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db)
    
    setattr(profile_model, path_column, str(file_path))
    db.commit()

    return JSONResponse({"status": "ok", "path": str(file_path), "image_type": image_type})


@router.delete("/{image_type}")
async def delete_image(image_type: str, db: Session = Depends(get_db)) -> JSONResponse:
    if image_type not in IMAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {image_type}")

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db)
    current_path = getattr(profile_model, path_column)

    if current_path:
        p = Path(current_path)
        if p.exists():
            p.unlink()

    setattr(profile_model, path_column, "")
    db.commit()

    return JSONResponse({"status": "ok", "image_type": image_type})


@router.get("/{image_type}/preview")
async def get_image_preview(image_type: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Return base64-encoded image for preview in the frontend."""
    if image_type not in IMAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {image_type}")

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db)
    current_path = getattr(profile_model, path_column)

    if not current_path:
        return JSONResponse({"has_image": False, "data": ""})

    p = Path(current_path)
    if not p.exists():
        return JSONResponse({"has_image": False, "data": ""})

    raw = p.read_bytes()
    ext = p.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
    b64 = base64.b64encode(raw).decode("ascii")

    return JSONResponse({"has_image": True, "data": f"data:{mime};base64,{b64}"})
