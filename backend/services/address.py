import requests

from backend.services.validation import clean_text, digits_only


VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"


class AddressLookupError(RuntimeError):
    pass


def normalize_cep(value) -> str:
    cep = digits_only(value)
    if len(cep) != 8:
        raise ValueError("CEP deve conter 8 digitos")
    return cep


def lookup_cep(cep_value) -> dict[str, str]:
    cep = normalize_cep(cep_value)
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(VIACEP_URL.format(cep=cep), timeout=5)
    except requests.RequestException as exc:
        raise AddressLookupError("Servico de CEP indisponivel") from exc

    if response.status_code == 400:
        raise ValueError("CEP invalido")
    try:
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise AddressLookupError("Nao foi possivel consultar o CEP") from exc

    if data.get("erro") is True:
        raise LookupError("CEP nao encontrado")

    return {
        "cep": clean_text(data.get("cep") or cep, field="cep", max_length=9),
        "street": clean_text(data.get("logradouro"), field="logradouro", max_length=200),
        "complement": clean_text(data.get("complemento"), field="complemento", max_length=200),
        "neighborhood": clean_text(data.get("bairro"), field="bairro", max_length=100),
        "city": clean_text(data.get("localidade"), field="cidade", max_length=100),
        "state": clean_text(data.get("uf"), field="uf", max_length=2),
        "ibge": clean_text(data.get("ibge"), field="ibge", max_length=20),
    }
