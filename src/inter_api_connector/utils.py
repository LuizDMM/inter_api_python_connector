def mask_sensitive_data(value):
    """
    Esta função recebe um valor sensível, como uma senha ou informação confidencial,
    e retorna uma versão mascarada do mesmo.

    Parâmetros:
    - value (str): O valor sensível que será mascarado.

    Retorna:
    - str: Uma versão mascarada do valor, onde apenas o primeiro caractere é revelado
    e os caracteres restantes são substituídos por '*'. Se o valor não for uma string
    ou tiver apenas um caractere, o valor original é retornado sem alterações.
    """
    if isinstance(value, str) and len(value) > 1:
        return value[0] + "*" * (len(value) - 1)
    return value
