import datetime
import logging
from typing import Literal, Union

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from .error import (
    APIError,
    AuthenticationError,
    Error,
    InvalidRequestError,
    RateLimitError,
)
from .patch import HTTPAdapter, patch_requests
from .utils import mask_sensitive_data

logger = logging.getLogger(__name__)


class API(object):
    def __init__(
        self,
        client_certificate: Union[bytes, None] = None,
        client_key: Union[bytes, None] = None,
        client_id: Union[str, None] = None,
        client_secret: Union[str, None] = None,
        base_url: Union[str, None] = None,
        scope: Union[str, None] = None,
        conta_corrente: Union[str, None] = None,
    ):
        self.base_url = base_url or "https://cdpj.partners.bancointer.com.br/"
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token = None
        self.access_token_expiration = None
        patch_requests(adapter=False)
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter())
        self.session.headers.update({"Content-Type": "application/json;charset=utf-8"})
        cert = (
            x509.load_pem_x509_certificate(client_certificate, default_backend())
            if client_certificate
            else None
        )
        key = (
            serialization.load_pem_private_key(client_key, None, default_backend())
            if client_secret
            else None
        )
        self.cert = (cert, key)
        self.conta_corrente = conta_corrente
        if conta_corrente:
            self.session.headers.update({"x-conta-corrente": conta_corrente})
        return

    @property
    def is_autenticated(self):
        return (
            self.access_token
            and self.access_token_expiration is not None
            and self.access_token_expiration > datetime.datetime.now()
        )

    def autenticar(
        self,
        client_id: Union[str, None] = None,
        client_secret: Union[str, None] = None,
        client_certificate: Union[bytes, None] = None,
        client_key: Union[bytes, None] = None,
        scope: Union[str, None] = None,
    ):
        if not client_id and not self.client_id:
            raise ValueError('Você precisa fornecer o "client_id" para se autenticar.')
        if not client_secret and not self.client_secret:
            raise ValueError(
                'Você precisa fornecer o "client_secret" para se autenticar.'
            )
        if (not client_secret or not client_certificate) and not self.cert:
            raise ValueError(
                'Você precisa fornecer o "client_certificate" e o "client_secret" para se autenticar.'
            )
        if not scope and not self.scope:
            raise ValueError('Você precisa fornecer o "scope" para se autenticar.')

        self.client_id = client_id or self.client_id
        self.client_secret = client_secret or self.client_secret
        if client_certificate and client_key:
            cert = (
                x509.load_pem_x509_certificate(client_certificate, default_backend())
                if client_certificate
                else None
            )
            key = (
                serialization.load_pem_private_key(client_key, None, default_backend())
                if client_secret
                else None
            )
            self.cert = (cert, key)
        self.scope = scope or self.scope

        oauth = self.__get_oauth_token()
        self.session.headers.update(
            {"Authorization": f"Bearer {oauth['access_token']}"}
        )
        return True

    def enviar_request_autenticada(
        self,
        metodo_http: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        *args,
        **kwargs,
    ) -> requests.Response:
        if (
            not self.access_token
            or datetime.datetime.now() > self.access_token_expiration
        ):
            logger.debug(
                "O cliente do inter não está autenticado ou o token expirou. "
                "Tentando atualizar access token."
            )
            if not self.client_id or not self.client_secret or not self.cert:
                raise InvalidRequestError(
                    "Você não configurou as suas credenciais corretamente."
                )
            else:
                self.autenticar()
        logger.debug(f"Dados da request: Args {args} Kwargs: {kwargs}")
        return self.__request(metodo_http)(*args, **kwargs)

    def __request(self, metodo_http: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]):
        if metodo_http not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise ValueError("Método HTTP inválido.")
        return {
            "GET": self.session.get,
            "POST": self.session.post,
            "PUT": self.session.put,
            "PATCH": self.session.patch,
            "DELETE": self.session.delete,
        }.get(metodo_http, "GET")

    def __get_oauth_token(
        self, grant_type: str = "client_credentials", scope: Union[str, None] = None
    ):
        if scope:
            self.scope = scope
        params = {
            "client_id": mask_sensitive_data(self.client_id),
            "client_secret": mask_sensitive_data(self.client_secret),
            "grant_type": grant_type,
            "scope": self.scope,
        }
        logger.debug(f"payload: {params}, headers: {self.session.headers}")
        params["client_id"] = self.client_id
        params["client_secret"] = self.client_secret
        response = self.session.post(
            self.base_url + "oauth/v2/token",
            params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            cert=self.cert,
        )
        logger.debug(f"resposta raw: {response.text}")
        if not response.ok:
            logger.debug(f"Inter API Response: {response.text}")
            self.__raise_respostas_erro(response)
        data = response.json()
        self.access_token = data["access_token"]
        self.access_token_expiration = datetime.datetime.now() + datetime.timedelta(
            seconds=data["expires_in"]
        )
        return data

    def __raise_respostas_erro(self, response: requests.Response):
        if response.status_code == 429:
            raise RateLimitError(
                "Você ultrapassou o rate limit. Tente novamente em alguns instantes."
            )
        elif response.status_code == 400:
            raise InvalidRequestError(f"Request inválida: {response.text}")
        elif response.status_code == 403:
            raise AuthenticationError(f"Error de autenticação: {response.text}")
        elif response.status_code == 404:
            raise InvalidRequestError(f"Resquest inválida: {response.text}")
        elif response.status_code == 503:
            raise APIError(f"O serviço não está disponível no momento: {response.text}")
        elif response.status_code != 200:
            raise Error(
                f"Um erro genérico aconteceu: {response.status_code} - {response.text}"
            )
