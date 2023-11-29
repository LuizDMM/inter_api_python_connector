import decimal
import json
import logging
from typing import Literal, Union

import requests

from .api import API
from .error import (
    APIError,
    AuthenticationError,
    Error,
    InvalidRequestError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class InterClient(API):
    # TODO: API Cobrança e Cobrança (Boleto com PIX)
    def emitir_boleto(self, *args, **kwargs):
        raise NotImplementedError()

    def recuperar_colecao_boletos(self, *args, **kwargs):
        raise NotImplementedError()

    def recuperar_sumario_boletos(self, *args, **kwargs):
        raise NotImplementedError()

    def recuperar_boleto_detalhado(self, *args, **kwargs):
        raise NotImplementedError()

    def recuperar_boleto_em_pdf(self, *args, **kwargs):
        raise NotImplementedError()

    def cancelar_boleto(self, *args, **kwargs):
        raise NotImplementedError()

    # TODO: API Banking

    # TODO: API Pix
    def criar_cobranca_pix(
        self,
        calendario: dict,
        valor: dict,
        chave: str,
        txid: Union[str, None] = None,
        **params,
    ):
        # Verifica se está autenticado, tenta re-autenticar (token expirado, por exemplo)
        # se necessário.
        self.__verificar_autenticacao()

        # Valida o valor
        valor = self.__valida_valor_pix(valor)

        # Detecta qual o tipo do pix a ser criado, com base no calendário (imediato ou
        # com vencimento).
        tipo_pix = self.__detectar_tipo_criar_pix(calendario, txid)

        # Determina o caminho da URL com base no tipo do PIX
        url_path = self.__detectar_url_path_criar_pix(tipo_pix, txid)

        # Cria o payload para a requisição
        data = {"calendario": calendario, "valor": valor, "chave": chave, **params}

        # Envia a requisição autenticada
        response = self.enviar_request_autenticada(
            self.__get_metodo_http_criar_pix(tipo_pix, txid),
            url=self.base_url + url_path,
            data=json.dumps(data),
        )
        # Valida o Código HTTP
        if not response.ok:
            self.__raise_erro_criar_pix(response)

        return response.json()

    def __verificar_autenticacao(self):
        if not self.is_autenticated:
            try:
                self.autenticar()
            except ValueError:
                raise ValueError(
                    'Você não está autenticado. Garanta que você chamou "autenticar()" '
                    "corretamente antes continuar."
                )

    def __valida_valor_pix(self, valor: dict):
        if not isinstance(valor, dict) or "original" not in valor:
            raise ValueError(
                'O campo "valor" deve ser um dict contendo, pelo menos, "original".'
            )

        valor_pix = valor.get("original", 0)

        if not isinstance(
            valor_pix, (int, float, decimal.Decimal, str)
        ) or decimal.Decimal(valor_pix) <= decimal.Decimal(0):
            raise ValueError('O campo "original" do valor é um valor inválido.')

        # Formatando o valor com duas casas decimais
        valor["original"] = "{:.2f}".format(float(valor_pix))

        return valor

    def __detectar_tipo_criar_pix(
        self, calendario: dict, txid: Union[str, None] = None
    ) -> str:
        # Valida o calendário. Ele só é válido for um dict que contem a key "expiracao"
        # (PIX imediato) ou as keys "dataDeVencimento" e "validadeAposVencimento"
        # (PIX com vencimento)
        if not isinstance(calendario, dict) or not (
            ("expiracao" in calendario)
            ^ (
                "dataDeVencimento" in calendario
                and "validadeAposVencimento" in calendario
            )
        ):
            raise ValueError(
                '"calendario" deve ser um dict com "expiracao" para PIX imediato ou '
                '"dataDeVencimento" e "validadeAposVencimento" para PIX com vencimento.'
            )

        return "imediato" if "expiracao" in calendario else "com_vencimento"

    def __detectar_url_path_criar_pix(
        self, tipo_pix: Literal["imediato", "com_vencimento"], txid: Union[str, None]
    ):
        if tipo_pix == "com_vencimento":
            if not txid:
                raise ValueError(
                    'É preciso fornecer o "txid" para cobrança PIX com vencimento.'
                )
            return f"pix/v2/cobv/{txid}"
        elif tipo_pix == "imediato":
            return f"pix/v2/cob/{txid}" if txid else "pix/v2/cob"
        else:
            raise ValueError("Tipo de PIX inválido.")

    def __get_metodo_http_criar_pix(
        self, tipo_pix: Literal["imediato", "com_vencimento"], txid: Union[str, None]
    ):
        if tipo_pix not in ("imediato", "com_vencimento"):
            raise ValueError('"tipo_pix" inválido.')
        elif tipo_pix == "imediato" and not txid:
            return "POST"
        else:
            return "PUT"

    def __raise_erro_criar_pix(self, response: requests.Response):
        if response.status_code == 429:
            raise RateLimitError(
                "Você ultrapassou o rate limit. Tente novamente em alguns instantes."
            )
        elif response.status_code == 400:
            raise InvalidRequestError(f"Request inválida: {response.text}")
        elif response.status_code == 403 or response.status_code == 401:
            raise AuthenticationError(f"Error de autenticação: {response.text}")
        elif response.status_code == 404:
            raise InvalidRequestError(f"Resquest inválida: {response.text}")
        elif response.status_code == 500:
            raise APIError(f"Houve um erro no servidor do inter: {response.text}")
        elif response.status_code == 503:
            raise APIError(f"O serviço não está disponível no momento: {response.text}")
        elif not response.ok:
            raise Error(
                f"Erro genérico ao fazer a requisição: {response.status_code} - {response.text}"
            )

    def revisar_cobranca_pix(self, *args, **kwargs):
        raise NotImplementedError()

    def consultar_cobranca_pix(self, *args, **kwargs):
        raise NotImplementedError()

    def consultar_list_cobrancas_pix(self, *args, **kwargs):
        raise NotImplementedError()

    def devolver_cobranca_pix(self, *args, **kwargs):
        raise NotImplementedError()

    def consultar_devolucao_cobranca_pix(self, *args, **kwargs):
        raise NotImplementedError()
