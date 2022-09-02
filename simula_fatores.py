from date_utils import feriados

holidays = feriados()

from markov_transition_matrix import TransitionMatrixCOPOM, get_copom

import numpy  as np
import pandas as pd
from itertools import product as _iter_product

class SimulaCenariosDI:
    
    """
        Classe para precificação e simulação de cenários de fatores de juros e,
    consequentemente, taxas de acordo com decisões do COPOM
    
     Métodos disponíveis:
    __________________________________________________________________________
    
        * _fator:
            cálculo de fator e taxa de juros dado um cenário de decisões
            
        * _possible_copom:
            gerador de caminhos possíveis de COPOM
            
        * _cdv01:
            cálculo de derivadas parciais de cada vencimento fornecido em
        relação à cada um dos COPOM fornecidos
        
        * _fator_multiplo:
            cálculo de fatores múltiplos
        
        
    """
    
    def __init__(self,
                 di_over    : float,
                 val_date   : str,
                 copom      : list,
                 holidays   : list = holidays,
                 **kwargs):
        
        self.di_over  = di_over
        self.dict_kw  = dict(**kwargs)
        self.val_date = val_date
        self.copom    = copom
        self.holidays = holidays
        
        # Caso esteja definido como download_probabilities = True, baixará
        self.download_probabilities = kwargs.get('download_probabilities', False)
        
        if self.download_probabilities: self._get_probabilities()
        
        # Gera as possibilidades de COPOM
        # self.__possible_copom__(self.dict_kw)
        
    
    def _get_probabilities(self,
                           date_filter : str = '2010-01-01'):
        
        
        """
        Método para capturar a matriz de transição de Markov dos últimos COPOM
        """
        self.hist_copom = get_copom(date_filter)
        self._hist_copom = self.hist_copom['Decisão (bps)'].values.flatten()
        
        self.obj_transition_matrix = TransitionMatrixCOPOM(self._hist_copom)
        self.transition_matrix = self.obj_transition_matrix.transition_matrix
        
    
    def _possible_copom(self,
                        n_copom : int,
                        **kwargs):
        
        
        """
        
        Método que calcula todas as possibilidades de copom dadas as decisões possíveis
        
        **********************************************************************
        
            ATENÇÃO: requere parcimônia durante o uso, visto que combinatória
        de possibilidades é infinita
        
            Exemplo de uso NÃO parcimonioso:
                possible_copom = [-100, -75, -50, 25, 0, 25, 50, 75, 100]
                n_copom = 11
                
                Resultado:
                    48.828.125 cenários possíveis
                    
        **********************************************************************
        
        Resultado:
            np.ndarray
                Array contendo todos as possibilidades de cenários com os parâmetros
            fornecidos
        
        """
        
        def generate_copom(decisoes):
            return np.array(list(_iter_product(decisoes, repeat = n_copom)))
        
        possible_copom = kwargs.get(('possible_copom', 'copom_possiveis', 'possibilidades'),
                                    [-50, 25, 0, 25, 50])
        
        self.possible_copom = possible_copom
        possible_scenarios = generate_copom(self.possible_copom)
        
        return possible_scenarios
        
    
    def _fator(self,
               decisions : list,
               maturity  : str,
               **kwargs):
        
        """
        Método de cálculo de fator de DI para um determinado vencimento
        
        Variáveis:
            decisions : list
                Lista contendo as decisões que se deseja simular
            maturity  : str
                Vencimento até onde se deseja calcular o valor de juros
        
        Resultado:
            Dicionário que contém 3 tags principais:
                path   : caminho relevante utilizado para a simulação
                factor : fator de juros registrado até o vencimento inserido
                yield  : taxa de juros implícita pelo fator de juros calculado
                
        """
        
        # DI Over em número (%)
        di_over = self.di_over/100.
        
        # Variáveis de data
        val_date = np.datetime64(self.val_date, 'D')
        maturity = np.datetime64(maturity, 'D')
        
        # Filtra somente as datas de COPOM relevantes
        _copom = np.sort(np.array(self.copom + [maturity]).astype('datetime64[D]'))
        _copom = _copom[np.where(_copom <= maturity)]
        
        assert len(decisions) >= len(_copom) - 1, \
            f'Número de decisões fornecidas deve ser igual ou maior do que o número de COPOM que impacta o vencimento {maturity}'
        
        # Tratamento de variáveis para as decisões
        decisions = decisions[:len(_copom)+1]
        decisions = decisions + [0] # Preenche fim (decisão 0 no vencimento)
        
        # Define o fator de juros como sendo = 1
        _f = 1.
        
        # Calcula a quantidade de dias úteis até cada COPOM
        dus = np.busday_count(val_date,
                              _copom,
                              holidays = self.holidays)
        
        # Calcula a quantidade de dias úteis entre os copoms
        diffs = np.append(dus[0], dus[1:] - dus[:-1])
        
        # Para cada um dos COPOM irá calcular o fator de juros
        # DADOS:
        # _c  : COPOM em questão
        # _i  : contador
        # _du : número de dias úteis entre fluxos (COPOM)
        # CALCULADOS:
            # _decs = soma de decisões até o momento
            # _di   = taxa DI Over válida no momento
            # _f    = fator de juros do DI Over acumulado
        _decs = 0
        
        for _c, _i, _du in zip(_copom, range(len(_copom)), diffs):
        
            _decs += 0 if _i == 0 else decisions[_i - 1]/10000. # Soma das decisões
            _di = di_over + _decs # DI Over
            _f *= (1. + _di) ** (_du/252.) # Fator
        
        if self.download_probabilities:
        
            return {'path'   : decisions,
                    'probability' : self.obj_transition_matrix.path_probability(decisions),
                    'factor' : _f,
                    'yield'  : _f ** (252./dus[-1]) - 1.}
        else:
            
            return {'path'   : decisions,
                    'factor' : _f,
                    'yield'  : _f ** (252./dus[-1]) - 1.}
            
    
    def _cdv01(self,
               maturities : list,
               **kwargs):
        
        
        """
        Método para cálculo de CDV01 (COPOM DV01) para os vencimentos requisitados
        
        Variáveis:
            maturities : list
                Lista de vencimentos para se calcular as derivadas numéricas
        
        Resultado:
            result : pd.DataFrame
                Resultado é uma matriz de colunas = datas COPOM, linhas = VENCIMENTOS
                Esta matriz demonstra o quanto cada um dos vencimentos está sujeito à
            variar, dada uma variação de 1bp (0.01%) para cada uma das decisões implícitas
            nos COPOM em questão
            
            Exemplo:
                Caso a matriz demonstre um impacto de 0.002 em C_1, e o usuário deseje calcular
            qual o montante de choque causado por uma modificação de 50bps na expectativa
            do COPOM 1 (C_1), 50 * 0.0002 = 0.01 = 1% de choque na taxa futura pelo choque de
            expectativa
        """
        
        # Primeiro tem que descobrir o tamanho máximo que impacta o último venc
        copom = np.array(self.copom).astype('datetime64[D]')
        maturities = np.array(maturities).astype('datetime64[D]')
        maturities = np.busday_offset(maturities, 0, roll = 'forward', holidays = self.holidays)
        last_mat = np.max(maturities)
        
        # _n_copom é o número de COPOM que de fato afeta o vencimento
        _n_copom = len(np.where(copom <= last_mat)[0])

        method = kwargs.get('method', 'prog')

        def _derivada_numerica(_m        : str,
                               _n_choque : int,
                               _choque   : float = 1.,
                               **kwargs):
            
            """
            Sub-função de cálculo de derivadas numéricas para o COPOM
            
            Métodos disponíveis (variável 'method'):
                prog    : progressiva
                reg     : regressiva
                central : central
                
            """
            
            method = kwargs.get('method', 'prog')
            
            # Redefine o choque considerando o 0 como início
            # _n_choque -= 1
            
            _base = [0] * _n_copom
            
            _base_up  = [_base[i] \
                         if i != _n_choque else \
                             _base[i] + _choque \
                                 for i in range(len(_base))]
                
            _base_2up  = [_base[i] \
                          if i != _n_choque else \
                              _base[i] + 2 * _choque \
                                  for i in range(len(_base))]
                
            _base_down  = [_base[i] \
                           if i != _n_choque else \
                               _base[i] - _choque \
                                 for i in range(len(_base))]
            _base_2down  = [_base[i] \
                            if i != _n_choque else \
                                _base[i] - 2 * _choque \
                                    for i in range(len(_base))]
                
            _c_base = self.di_over/100. # Cenário base com 0 de decisão será o DI
            
            _c_base_up = self._fator(_base_up,
                                     _m)['yield']
            
            _c_base_2up = self._fator(_base_2up,
                                     _m)['yield']
            
            _c_base_down = self._fator(_base_down,
                                       _m)['yield']
            
            _c_base_2down = self._fator(_base_2down,
                                        _m)['yield']
            
            if method.lower() == 'prog':
                result = ((-3 * _c_base + 4 * _c_base_up - _c_base_2up)/(2 * _choque)) * 100
            if method.lower() == 'reg':
                result = ((_c_base_2down - 4 * _c_base_down + 3 * _c_base)/(2 * _choque)) * 100
            if method.lower() == 'central':
                result = ((_c_base_up - _c_base_down)/(2 * _choque)) * 100
            
            return result
        
        def _trunc(number, digits):
            
            """
            Sub-função para fazer truncamento de valores
            """
            
            return np.trunc(number * (10 ** digits))/(10 ** digits)

        _derivadas = [[_trunc(_derivada_numerica(_m, _i, 1, **kwargs), 10) for _i in range(_n_copom)] for _m in maturities]
    
    
    
        df = pd.DataFrame(_derivadas,
                          columns = copom[:_n_copom],
                          index   = maturities)
        
        return df
    
    def _fator_multiplo(self,
                        decisions   : list,
                        maturities  : list,
                        **kwargs):
        
        
        """
        Método para calcular múltiplos fatores simultaneamente
        
        Aceita:
            decisions  : múltiplos caminhos de decisão, em formato list of lists
            maturities : múltiplas decisões, em formato list
        """
        
        maturities = [maturities] if not isinstance(maturities, (list, np.ndarray)) else maturities
        decisions = [decisions] if not isinstance(decisions[0], (list, np.ndarray)) else decisions
        
        fatores = [[self._fator(_s, _m)['yield'] \
                   for _s in decisions] \
                       for _m in maturities]
        
        return pd.DataFrame(fatores,
                            columns = [f'Cenário {_i}' for _i in range(1, len(decisions) + 1)],
                            index = maturities).T
        
    def __call__(self,
                 decisions  : list,
                 maturities : list,
                 **kwargs):
        
        """
        Caso o objeto seja chamado, irá retornar os resultados do método de fator múltiplo
        """
        
        if isinstance(maturities, (list, np.ndarray)):
            if len(maturities) == 1:
                return self._fator(decisions,
                                   maturities,
                                   **kwargs)
            else:
                return self._fator_multiplo(decisions,
                                            maturities,
                                            **kwargs)
        else:
            return self._fator(decisions,
                               maturities,
                               **kwargs)
