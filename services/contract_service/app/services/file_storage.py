from pathlib import Path

from app.core.config import settings


class LocalFileStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def resolve_path(
        self,
        object_key: str,
    ) -> Path:
        path = (
            self.base_path / object_key
        ).resolve()

        base = self.base_path.resolve()

        if (
            path != base
            and base not in path.parents
        ):
            raise ValueError(
                "Invalid object key"
            )

        return path

    def build_path(
        self,
        object_key: str,
    ) -> Path:
        path = self.resolve_path(
            object_key
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    def save(
        self,
        file_bytes: bytes,
        object_key: str,
    ) -> str:
        path = self.build_path(
            object_key
        )

        path.write_bytes(
            file_bytes
        )

        return object_key

    def delete(
        self,
        object_key: str,
    ) -> None:
        path = self.resolve_path(
            object_key
        )

        if path.exists():
            path.unlink()

    def exists(
        self,
        object_key: str,
    ) -> bool:
        return self.resolve_path(
            object_key
        ).exists()


storage = LocalFileStorage(
    settings.ATTACHMENT_STORAGE_PATH
)