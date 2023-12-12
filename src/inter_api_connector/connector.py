import datetime
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
    def verificar_scope(self, scope: str):
        return scope in self.scope

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
    def consultar_extrato(
        self,
        data_inicio: datetime.datetime,
        data_fim: datetime.datetime,
        tipo_extrato: Literal["padrao", "pdf", "enriquecido"] = "padrao",
        conta_corrente: Union[str, None] = None,
        **params,
    ):
        self.__verificar_autenticacao()

        self.__validar_tipo_extrato(tipo_extrato)

        url_path = self.__detectar_url_path_consultar_extrato(tipo_extrato)

        query_params = {
            "dataInicio": data_inicio.date().isoformat(),
            "dataFim": data_fim.date().isoformat(),
            **params,
        }
        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, params=query_params, headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def __detectar_url_path_consultar_extrato(
        self, tipo_extrato: Literal["padrao", "pdf", "enriquecido"]
    ):
        paths = {
            "padrao": "banking/v2/extrato",
            "pdf": "banking/v2/extrato/exportar",
            "enriquecido": "banking/v2/extrato/completo",
        }
        return paths[tipo_extrato]

    def __validar_tipo_extrato(self, tipo_extrato):
        if not isinstance(tipo_extrato, str) or tipo_extrato not in (
            "padrao",
            "pdf",
            "enriquecido",
        ):
            raise ValueError(
                'O "tipo_extrato" deve ser "padrao", "pdf", ou "enriquecido", '
                f"valor fornecido: {tipo_extrato}"
            )

    def consultar_saldo(self, *args, **kwargs):
        raise NotImplementedError()

    def incluir_pagamento(
        self, tipo: Literal["cod_barras", "darf", "pix"], *args, **kwargs
    ):
        raise NotImplementedError()

    def consultar_pagamentos(
        self, tipo: Literal["cod_barras", "darf", "pix"], *args, **kwargs
    ):
        raise NotImplementedError()

    def incluir_pagamentos_em_lote(self, *args, **kwargs):
        raise NotImplementedError()

    def consultar_pagamentos_em_lote(self, *args, **kwargs):
        raise NotImplementedError()

    def cancelar_agendamento_pagamento(self, *args, **kwargs):
        raise NotImplementedError()

    # TODO: API Pix
    def criar_cobranca_pix(
        self,
        calendario: dict,
        valor: dict,
        chave: str,
        txid: Union[str, None] = None,
        conta_corrente: Union[str, None] = None,
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
        url_path = self.__get_url_path_criar_pix(tipo_pix, txid)

        # Cria o payload para a requisição
        data = {"calendario": calendario, "valor": valor, "chave": chave, **params}
        headers = self.__get_headers(conta_corrente)
        # Envia a requisição autenticada
        response = self.enviar_request_autenticada(
            self.__get_metodo_http_criar_pix(tipo_pix, txid),
            url=self.base_url + url_path,
            data=json.dumps(data),
            headers=headers,
        )

        # Valida o Código HTTP
        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

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

    def __get_url_path_criar_pix(
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

    def __get_headers(self, conta_corrente: Union[str, None]):
        if conta_corrente:
            headers = {"x-conta-corrente": conta_corrente}
        else:
            headers = None
        return headers

    def __get_metodo_http_criar_pix(
        self, tipo_pix: Literal["imediato", "com_vencimento"], txid: Union[str, None]
    ):
        if tipo_pix not in ("imediato", "com_vencimento"):
            raise ValueError('"tipo_pix" inválido.')
        elif tipo_pix == "imediato" and not txid:
            return "POST"
        else:
            return "PUT"

    def __raise_erro_codigo_http_invalido(self, response: requests.Response):
        if response.status_code == 429:
            raise RateLimitError(
                "Você ultrapassou o rate limit. Tente novamente em alguns instantes."
            )
        elif response.status_code == 400:
            raise InvalidRequestError(f"Request inválida: {response.text}")
        elif response.status_code == 403 or response.status_code == 401:
            raise AuthenticationError(f"Error de autenticação: {response.text}")
        elif response.status_code == 404:
            raise InvalidRequestError(
                f"O objeto solicitado não foi encontrado: {response.text}"
            )
        elif response.status_code == 500:
            raise APIError(f"Houve um erro no servidor do inter: {response.text}")
        elif response.status_code == 503:
            raise APIError(f"O serviço não está disponível no momento: {response.text}")
        elif not response.ok:
            raise Error(
                f"Erro genérico ao fazer a requisição: {response.status_code} - {response.text}"
            )

    def revisar_cobranca_pix(
        self,
        tipo_cobranca: Literal["imediata", "com_vencimento"],
        txid,
        conta_corrente: Union[str, None] = None,
        **params,
    ):
        self.__verificar_autenticacao()

        if tipo_cobranca == "imediata":
            url_path = f"pix/v2/cob/{txid}"
        elif tipo_cobranca == "com_vencimento":
            url_path = f"pix/v2/cobv/{txid}"

        data = {**params}
        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "PATCH",
            url=self.base_url + url_path,
            data=json.dumps(data),
            headers=headers,
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def consultar_cobranca_pix(
        self, e2eId, conta_corrente: Union[str, None] = None, **params
    ):
        # Verifica se está autenticado, tenta re-autenticar (token expirado, por exemplo)
        # se necessário.
        self.__verificar_autenticacao()

        # Caminho da URL
        url_path = f"pix/v2/pix/{e2eId}"

        # Criar o payload para a requisição
        headers = self.__get_headers(conta_corrente)

        # Envia a requisição autenticada
        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, headers=headers
        )

        # Valida o código HTTP
        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def consultar_cobrancas_pix_recebidas(
        self,
        inicio: datetime.datetime,
        fim: datetime.datetime,
        pagina_atual: int = 0,
        itens_por_pagina: int = 100,
        conta_corrente: Union[str, None] = None,
        **params,
    ):
        # Verifica se está autenticado, tenta re-autenticar (token expirado, por exemplo)
        # se necessário.
        self.__verificar_autenticacao()

        # Valida os tipos e se fim é maior que início
        self.__valida_inicio_fim(inicio, fim)

        # Caminho da URL
        url_path = "pix/v2/pix"

        # Criar dados para a requisição
        queries = {
            "inicio": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fim": fim.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "paginacao.paginaAtual": pagina_atual,
            "paginacao.itensPorPagina": itens_por_pagina,
            **params,
        }
        headers = self.__get_headers(conta_corrente)

        # Envia a requisição autenticada
        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, headers=headers, params=queries
        )

        # Valida o código HTTP
        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def __valida_inicio_fim(self, inicio: datetime.datetime, fim: datetime.datetime):
        if (
            not all(isinstance(i, datetime.datetime) for i in (inicio, fim))
            and fim > inicio
        ):
            raise ValueError(
                '"inicio" deve ser menor que "fim" e ambos devem ser datetimes.'
            )

    def devolver_cobranca_pix(
        self,
        e2eid: str,
        id_devolucao: str,
        valor: str,
        conta_corrente: Union[str, None] = None,
    ):
        self.__verificar_autenticacao()

        url_path = f"pix/v2/pix/{e2eid}/devolucao/{id_devolucao}"
        data = {"valor": valor}
        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "PUT", url=self.base_url + url_path, data=json.dumps(data), headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def consultar_devolucao_cobranca_pix(
        self, e2eid: str, id_devolucao: str, conta_corrente: Union[str, None] = None
    ):
        self.__verificar_autenticacao()

        url_path = f"pix/v2/pix/{e2eid}/devolucao/{id_devolucao}"
        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    # Interfaces dos Webhooks
    def criar_webhook(
        self,
        api: Literal["banking", "cobranca", "cobranca_com_pix", "pix"],
        webhook_url: str,
        path_parameter: Union[str, None] = None,
        conta_corrente: Union[str, None] = None,
    ):
        self.__verificar_autenticacao()

        url_path = self.__get_url_path_criar_webhook(api, path_parameter)

        data = {"webhookUrl": webhook_url}
        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "PUT", url=self.base_url + url_path, data=json.dumps(data), headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return True

    def __get_url_path_criar_webhook(self, api, path_parameter):
        if api == "banking":
            url_path = f"banking/v2/webhooks/{path_parameter}"
        elif api == "cobranca":
            url_path = "cobranca/v2/boletos/webhook"
        elif api == "cobranca_com_pix":
            url_path = "cobranca/v3/cobrancas/webhook"
        elif api == "pix":
            url_path = f"pix/v2/webhook/{path_parameter}"
        return url_path

    def obter_webhook_cadastrado(
        self,
        api: Literal["banking", "cobranca", "cobranca_com_pix", "pix"],
        path_parameter: Union[str, None] = None,
        conta_corrente: Union[str, None] = None,
    ):
        self.__verificar_autenticacao()

        url_path = self.__get_url_path_criar_webhook(api, path_parameter)

        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def excluir_webhook(
        self,
        api: Literal["banking", "cobranca", "cobranca_com_pix", "pix"],
        path_parameter: Union[str, None] = None,
        conta_corrente: Union[str, None] = None,
    ):
        self.__verificar_autenticacao()

        url_path = self.__get_url_path_criar_webhook(api, path_parameter)

        headers = self.__get_headers(conta_corrente)

        response = self.enviar_request_autenticada(
            "DELETE", url=self.base_url + url_path, headers=headers
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return True

    def consultar_callbacks_webhook(
        self,
        api: Literal["banking", "cobranca", "cobranca_com_pix", "pix"],
        inicio: datetime.datetime,
        fim: datetime.datetime,
        conta_corrente: Union[str, None] = None,
        **params,
    ):
        self.__verificar_autenticacao()

        url_path = self.__get_url_path_consultar_callbacks(api)

        headers = self.__get_headers(conta_corrente)

        query_params = {
            "dataHoraInicio": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dataHoraFim": fim.strftime("%Y-%m-%dT%H:%M:%SZ"),
            **params,
        }

        response = self.enviar_request_autenticada(
            "GET", url=self.base_url + url_path, headers=headers, params=query_params
        )

        if not response.ok:
            self.__raise_erro_codigo_http_invalido(response)

        return response.json()

    def __get_url_path_consultar_callbacks(self, api):
        if api == "banking":
            url_path = "banking/v2/webhooks/pix-pagamento/callbacks"
        elif api == "cobranca":
            url_path = "cobranca/v2/boletos/webhook/callbacks"
        elif api == "cobranca_com_pix":
            url_path = "cobranca/v3/cobrancas/webhook/callbacks"
        elif api == "pix":
            url_path = "pix/v2/webhook/callbacks"
        return url_path
