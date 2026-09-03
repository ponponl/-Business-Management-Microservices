from pathlib import Path

from fastapi import HTTPException, UploadFile


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
}


def validate_file_metadata(
    file: UploadFile,
) -> None:

    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_FILE_NAME",
                "message": "Tên file không hợp lệ.",
            },
        )

    safe_name = Path(
        file.filename
    ).name

    if not safe_name:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_FILE_NAME",
                "message": "Tên file không hợp lệ.",
            },
        )

    extension = Path(
        safe_name
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FILE_EXTENSION_NOT_ALLOWED",
                "message": (
                    f"Định dạng file '{extension}' "
                    "không được hỗ trợ."
                ),
            },
        )

    if (
        file.content_type
        not in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FILE_TYPE_NOT_ALLOWED",
                "message": (
                    f"Loại file '{file.content_type}' "
                    "không được hỗ trợ."
                ),
            },
        )


async def read_and_validate_file(
    file: UploadFile,
) -> bytes:

    validate_file_metadata(file)

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "EMPTY_FILE",
                "message": "File không được rỗng.",
            },
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": (
                    "Kích thước file vượt quá "
                    "giới hạn 10 MB."
                ),
            },
        )

    return content