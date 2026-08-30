import secrets


def generate_contract_number() -> str:
    random_part = secrets.token_hex(4).upper()

    return f"CTR-{random_part}"