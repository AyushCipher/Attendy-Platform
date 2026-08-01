"""QR generation for student and book ID cards. Encodes the raw entity UUID -- not
"{name} {roll}" or "BOOK:<id>:<name>" like the legacy app, which broke for any
multi-word name once split on a space. A UUID has nothing to parse or split, so it
can't drift out of sync with whatever decodes it (the /ws/recognize scanning path in
this rewrite looks a decoded UUID up in students first, then books).
"""
import io
import uuid

import qrcode


def build_qr_png(entity_id: uuid.UUID) -> bytes:
    img = qrcode.make(str(entity_id))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
