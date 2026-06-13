import secrets

import requests


class InfinitePayError(RuntimeError):
    def __init__(self, message, status_code=502, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class InfinitePayClient:
    def __init__(self, handle, api_base='https://api.checkout.infinitepay.io'):
        self.handle = str(handle or '').strip().lstrip('$')
        self.api_base = api_base.rstrip('/')

    @property
    def configured(self):
        return bool(self.handle)

    def create_link(self, payload):
        return self._request('POST', '/links', json={
            'handle': self.handle,
            **payload,
        })

    def check_payment(self, order_nsu, transaction_nsu, slug):
        return self._request('POST', '/payment_check', json={
            'handle': self.handle,
            'order_nsu': order_nsu,
            'transaction_nsu': transaction_nsu,
            'slug': slug,
        })

    def _request(self, method, path, json=None):
        if not self.configured:
            raise InfinitePayError('InfinitePay não foi configurada', status_code=503)

        try:
            response = requests.request(
                method,
                f'{self.api_base}{path}',
                json=json,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                timeout=20,
            )
        except requests.RequestException as exc:
            raise InfinitePayError('Não foi possível conectar à InfinitePay') from exc

        try:
            data = response.json()
        except ValueError:
            data = {'message': response.text or 'Resposta inválida da InfinitePay'}

        if not response.ok:
            message = (
                data.get('message')
                or data.get('error')
                or 'Não foi possível iniciar o pagamento na InfinitePay'
            )
            raise InfinitePayError(message, status_code=502, details=data)

        return data


def checkout_token():
    return secrets.token_urlsafe(24)
