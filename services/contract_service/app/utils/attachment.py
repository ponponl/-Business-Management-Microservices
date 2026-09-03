from uuid import UUID


def build_attachment_object_key(
    contract_id: UUID,
    version_id: UUID,
    attachment_id: UUID,
) -> str:

    return (
        f"contracts/"
        f"{contract_id}/"
        f"{version_id}/"
        f"{attachment_id}"
    )