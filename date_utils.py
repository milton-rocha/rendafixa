# -*- coding: utf-8 -*-
"""
Author : Milton Rocha
Medium : https://medium.com/@milton-rocha
"""

import pandas as pd
import numpy  as np
import tempfile
import os

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Union


def dt_fmt_old(date : str):
    """
    Função que transforma a data inserida em formato de string ("yyyy-mm-dd")
    
    Variaveis:
        date : string de data em formato "yyyy-mm-dd"
        
    Resposta:
        datetime.date : data traduzida para datetime
    """
    return datetime.strptime(date, '%Y-%m-%d')

# strptime equivalent with built-in 90x faster
def isofmt(date : list) -> list:
    """
    Função que transforma mapeando uma série de datas fornecidas em formato de lista
    
    Variaveis:
        date : lista de strings de data em formato "yyyy-mm-dd"
        
    Resposta:
        list : lista de datas traduzida para datetime
        
    """
    if not isinstance(date, list): date = [date]
    return list(map(datetime.fromisoformat, date))


def date_fmt_mapper(date : Union[list, np.ndarray],
                    fmt  : str) -> list:
    """
    Função que transforma mapeando uma série de datas fornecidas em formato de lista
    
    Variaveis:
        date : lista de strings de data em formato "yyyy-mm-dd"
        
    Resposta:
        list : lista de datas traduzida para datetime
        
    """
    f = lambda dt: dt.strftime(fmt)
    return list(map(f, isofmt(date)))

def edate(data          : Union[str, np.datetime64],
          meses         : int,
          dateTypeEntry : str = '%Y-%m-%d') -> np.datetime64:
    """
    Função equivalente ao =EDATE() do excel, adiciona/remove meses de uma data
    """
    # Ajusta a data para ser uma data da classe 'datetime'
    # data = datetime.strptime(str(data), dateTypeEntry)
    data = isofmt(str(data))[0]
    data += relativedelta(months = meses)
    
    # return np.datetime64(data.strftime('%Y-%m-%d')).astype('datetime64[D]')
    # faster implementation:
    return np.datetime64('{}-{:02d}-{:02d}'.format(data.year, data.month, data.day), 'D')

def feriados(override : bool = False) -> np.ndarray:

    """
    Função que faz o download dos feriados do site da Anbima e os compila em um formato a ser utilizado
    
    Resposta:
      np.array(feriados, dtype = 'datetime64[D]')
    """

    # O arquivo fornecido por download possui algumas marcas de fornecimento dos feriados que serão tratadas
    # O arquivo finaliza antes da linha que possui "Fonte: ANBIMA" como valor
    arq_temp = f'{tempfile.gettempdir()}/fer_anbima.parquet'

    # Checa se já existe um arquivo de feriados Anbima gerado na pasta temporária, caso não, cria o arquivo
    if not os.path.isfile(arq_temp) and not override:
        feriados = pd.read_excel(r'https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls')
        feriados = feriados['Data'][ : feriados[feriados['Data'] == 'Fonte: ANBIMA'].index[0]].values # Acha a linha de footer
        feriados = pd.DataFrame({'Feriados ANBIMA' : feriados.astype('datetime64[D]')}) # Cria um dataframe com os dados
        feriados.to_parquet(arq_temp) # Exporta o DataFrame para .parquet
    else:
        feriados = pd.read_parquet(arq_temp) # Caso o arquivo já exista no diretório temporário, lê o .parquet
    
    # A função irá retornar um np.array contendo todas as datas de feriado disponíveis em formato 'datetime64[D]'
    return feriados.values.astype('datetime64[D]').flatten()
