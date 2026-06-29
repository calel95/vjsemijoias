from tests.helpers import client


def test_address_lookup_by_cep_uses_viacep(monkeypatch):
    calls = []

    class CepResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                'cep': '01001-000',
                'logradouro': 'Praça da Sé',
                'complemento': 'lado ímpar',
                'bairro': 'Sé',
                'localidade': 'São Paulo',
                'uf': 'SP',
                'ibge': '3550308',
            }

    def fake_get(self, url, timeout):
        calls.append((url, timeout, self.trust_env))
        return CepResponse()

    monkeypatch.setattr('backend.services.address.requests.Session.get', fake_get)

    response = client.get('/api/address/cep/01001-000')

    assert response.status_code == 200
    data = response.json()
    assert data['street'] == 'Praça da Sé'
    assert data['neighborhood'] == 'Sé'
    assert data['city'] == 'São Paulo'
    assert data['state'] == 'SP'
    assert calls == [('https://viacep.com.br/ws/01001000/json/', 5, False)]

def test_address_lookup_rejects_invalid_or_missing_cep(monkeypatch):
    invalid = client.get('/api/address/cep/123')

    class MissingCepResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {'erro': True}

    monkeypatch.setattr(
        'backend.services.address.requests.Session.get',
        lambda self, url, timeout: MissingCepResponse(),
    )
    missing = client.get('/api/address/cep/99999999')

    assert invalid.status_code == 400
    assert missing.status_code == 404

def test_address_lookup_returns_bad_gateway_when_provider_fails(monkeypatch):
    import requests

    def fail_get(self, url, timeout):
        raise requests.Timeout('timeout')

    monkeypatch.setattr('backend.services.address.requests.Session.get', fail_get)

    response = client.get('/api/address/cep/01001000')

    assert response.status_code == 502
