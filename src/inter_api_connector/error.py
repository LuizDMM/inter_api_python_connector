class Error(Exception):
    pass


class InvalidRequestError(Error):
    """
    Houve algum erro com a request, baseado nos dados fornecidos pelo usuário.
    """


class APIError(Error):
    """
    Houve algum erro do lado do Banco Inter, não relacionado aos dados fornecidos pelo usuário.
    """


class RateLimitError(Error):
    """
    Você está fazendo requisições de mais. Rate Limit ultrapassado.
    """


class AuthenticationError(Error):
    """
    Há algum problema com a sua autenticação do Inter.
    """
