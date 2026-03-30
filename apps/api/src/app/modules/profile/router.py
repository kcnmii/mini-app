from __future__ import annotations

import base64
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db, SupplierProfile as SupplierProfileModel
from app.core.auth import get_current_user_id
from app.core import s3
from app.schemas.profile import SupplierProfile, SupplierProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
IMAGE_FIELDS = {"logo", "signature", "stamp"}


def _get_or_create_profile(db: Session, user_id: int) -> SupplierProfileModel:
    import uuid as _uuid
    profile = db.query(SupplierProfileModel).filter(SupplierProfileModel.user_id == user_id).first()
    if profile:
        # Backfill profile_uuid if missing
        if not profile.profile_uuid:
            profile.profile_uuid = str(_uuid.uuid4())
            db.commit()
        return profile

    new_profile = SupplierProfileModel(user_id=user_id, profile_uuid=str(_uuid.uuid4()))
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


@router.get("", response_model=SupplierProfile)
async def get_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SupplierProfile:
    profile_model = _get_or_create_profile(db, user_id)
    data = {}
    for c in profile_model.__table__.columns:
        val = getattr(profile_model, c.name)
        if c.name == "notifications_enabled" and val is None:
            val = True
        data[c.name] = val
    return SupplierProfile(**data)


@router.put("", response_model=SupplierProfile)
async def update_profile(
    payload: SupplierProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SupplierProfile:
    profile_model = _get_or_create_profile(db, user_id)
    fields = payload.model_dump(exclude_unset=True)

    for key, value in fields.items():
        setattr(profile_model, key, value)

    # ── EDO Linkage Fix ──
    # If the user changed their IIN/BIN, or is just saving their profile,
    # find all documents sent to this user's stated IIN/BIN and lock them
    # to this specific user_id so they don't lose them if they change IIN/BIN later.
    if profile_model.company_iin:
        my_bin = profile_model.company_iin.strip()
        if my_bin:
            from app.core.db import Document
            db.query(Document).filter(
                Document.receiver_bin == my_bin,
                Document.receiver_user_id.is_(None)
            ).update({"receiver_user_id": user_id}, synchronize_session=False)

    db.commit()
    db.refresh(profile_model)

    data = {}
    for c in profile_model.__table__.columns:
        val = getattr(profile_model, c.name)
        if c.name == "notifications_enabled" and val is None:
            val = True
        data[c.name] = val
    return SupplierProfile(**data)


@router.post("/{image_type}")
async def upload_image(
    image_type: str,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
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

    filename = f"{image_type}{ext}"
    s3_key = f"uploads/{user_id}/{filename}"
    
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "application/octet-stream")
    await s3.upload_file(s3_key, content, content_type=mime)

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db, user_id)

    setattr(profile_model, path_column, s3_key)
    db.commit()

    return JSONResponse({"status": "ok", "path": s3_key, "image_type": image_type})


@router.delete("/{image_type}")
async def delete_image(
    image_type: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    if image_type not in IMAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {image_type}")

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db, user_id)
    current_path = getattr(profile_model, path_column)

    if current_path:
        await s3.delete_file(current_path)

    setattr(profile_model, path_column, "")
    db.commit()

    return JSONResponse({"status": "ok", "image_type": image_type})


@router.get("/{image_type}/preview")
async def get_image_preview(
    image_type: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return base64-encoded image for preview in the frontend."""
    if image_type not in IMAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {image_type}")

    path_column = f"{image_type}_path"
    profile_model = _get_or_create_profile(db, user_id)
    current_path = getattr(profile_model, path_column)

    if not current_path:
        return JSONResponse({"has_image": False, "data": ""})

    raw = await s3.download_file(current_path)
    if not raw:
        return JSONResponse({"has_image": False, "data": ""})

    ext = Path(current_path).suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
    b64 = base64.b64encode(raw).decode("ascii")

    return JSONResponse({"has_image": True, "data": f"data:{mime};base64,{b64}"})
