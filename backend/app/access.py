from io import BytesIO
from urllib.parse import urlparse

import qrcode
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from qrcode.image.svg import SvgPathImage


router = APIRouter(prefix="/api/v1/access", tags=["Access"])


def _validate_share_url(value: str) -> str:
    if len(value) > 2048:
        raise HTTPException(status_code=422, detail="Share URL is too long")

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Share URL must be an absolute HTTP or HTTPS URL")
    return value


@router.get("/qr.svg")
def access_qr(
    url: str = Query(min_length=8, max_length=2048),
):
    target = _validate_share_url(url)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(target)
    qr.make(fit=True)

    image = qr.make_image(image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    return Response(
        content=output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )
