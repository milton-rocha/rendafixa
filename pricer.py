# -*- coding: utf-8 -*-
"""
Author : Milton Rocha
Medium : https://medium.com/@milton-rocha
"""

from copy        import deepcopy
from tabulate    import tabulate
from typing      import Union

import pandas as pd
import numpy  as np

from calc_utils import (FlatForward,
                        Fluxos)
from date_utils import feriados
                        

# Desativa a função __array_function__ do numpy, que prejudica performance
import os
os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'

HOLIDAYS = pd.read_parquet('holidays.parquet')['Data'].values.astype('datetime64[D]')

class Bond:
    
    """
        Classe Bond, responsável pela precificação e cálculo de risco para Bonds
    genéricos
    
    **kwargs ACEITOS:
        
        - annual_coupon, float, default = 0:
            Cupom anual de juros
        - coupon_frequency, int, default = 0:
            Frequência anual de pagamento de juros
        - face_value, float, default = 1:
            Valor de FACE do Bond
        - VNA, float, default = 1:
            Valor Nominal Atualizado do Bond
        - yield_curve, object, default = FlatForward flat yield:
            Curva de juros a ser utilizada para descontar os fluxos
        - holidays, (list, np.ndarray), default = feriados():
            Lista ou np.ndarray contendo os feriados do país de precificação
        - bucketting, bool, default = False:
            Caso True, fará o bucketeamento do risco do Bond
        - risk_buckets, dict, default = vide método:
            Buckets nos quais serão alocados os riscos, formato:
                {NOME_BUCKET : prazo}
        - risk_type, str, default = Nominal:
            Tag que facilita a alocação posterior de bucketeamento
        - bond_name, str, default = Bond:
            Nome do bond que será mostrado em listas e str
    
    """
    
    def __init__(self,
                 val_date   : Union[str, np.datetime64, None],
                 maturity   : Union[str, np.datetime64, None],
                 bond_yield : Union[int, float, None],
                 **kwargs):
        
        # Tratamento nomeadas
        self.val_date   = val_date
        self.maturity   = maturity
        self.bond_yield = bond_yield
        
        # Tratamento Kwargs
        self.dict_kw    = dict(**kwargs)
        self.kw_keys    = list(self.dict_kw.keys())
        
        # Inicialização de variáveis
        self.__initialize_variables__()
        
        # Rolagem das datas de início e de fim
        self.__date_roll__()
        
        # Cálculo do PU
        self.__price__()
        
        # Cálculo de riscos e bucketeamento de risco
        self.__risks__()
        if self.bucketting: self.__bucketting__()
    
    def __flat_yc__(self):
        
        return FlatForward([i for i in range(1, 10001)],
                           [self.bond_yield for i in range(1, 10001)],
                           extrapolate = True)
    
    def __initialize_variables__(self):
        
        """
        Rotina de inicialização das variáveis para o objeto
        """
        
        # Variáveis padrão nomeadas ------------------------------------------
        # Inicialização da variável de valuation date (data de precificação)
        self.val_date = self.val_date if not isinstance(self.val_date, type(None)) else \
                        np.datetime64('today', 'D')
        #  Inicialização da variável de maturity (vencimento), caso não tenha
        # nenhum input, título vence em 252du
        self.maturity = self.maturity if not isinstance(self.maturity, type(None)) else \
                        np.busday_offset(self.val_date, 252)
        #  Inicialização da variável de bond_yield (taxa do bond), caso não tenha
        # input, irá considerar 10%
        self.bond_yield = self.bond_yield if not isinstance(self.bond_yield, type(None)) else \
                            0.1
                            
        # Variáveis kwargs nomeadas ------------------------------------------
        self.annual_coupon    = self.__get_variable__(['annual_coupon', 'cupom_anual'], 0)
        self.coupon_frequency = self.__get_variable__(['coupon_frequency', 'frequencia_cupom', 'freq_cupom'], 0)
        self.face_value       = self.__get_variable__(['face_value', 'valor_face', 'face'], 1.)
        self.VNA              = self.__get_variable__(['VNA', 'vna'], 1.)
        self.yield_curve      = self.__get_variable__(['yield_curve', 'yc', 'curva'], None)
        self.bucketting       = self.__get_variable__(['bucketting'], False)
        self.risk_buckets     = self.__get_variable__(['risk_buckets'], None)
        self.risk_type        = self.__get_variable__(['risk_type'], 'Nominal')
        self.bond_name        = self.__get_variable__(['bond_name'], 'Bond')
        self.quantity         = self.__get_variable__(['quantity', 'quantidade'], 1.)
        
        self.holidays         = self.__get_variable__(['feriados', 'holidays', 'fer', 'hol'], HOLIDAYS)
        
        #   Tratamento de variáveis que utilizam outras funções
        # em caso de variável base dependente de método ou fórmula, a função
        # é custosa e diminui a performance, então o tratamento é diferente
        # self.holidays = feriados() if not 'holidays' in self.kw_keys else self.dict_kw['holidays']
        
        self.full_name = f'@ {self.bond_name}|{str(self.maturity).split("-")[0]}|{self.bond_yield:.2%}'
        
        # Primeiros passos de variáveis de fluxos -----------------------------
        # objeto de fluxos
        self.fs = Fluxos(self.val_date,
                         self.maturity,
                         self.annual_coupon,
                         self.coupon_frequency,
                         self.holidays)
        
        # Dados dos fluxos
        self.coupons = self.fs.cupons
        self.dus     = self.fs.dus
        self.fatores = self.fs.fatores
                               
        # Backups dos parâmetros da função
        # self.params = deepcopy(vars(self))
        
        # Checa se o título é indexado
        self.indexed = True if self.VNA != 1. else False
        
    def __get_variable__(self,
                         possible_names,
                         standard_value):
        
        """
        Função feita para localizar variável dentro das fornecidas no **kwargs
        """
        
        possible_names = possible_names if not isinstance(possible_names, str) else [possible_names]
        # Para cada um dos nomes possíveis irá checar as kwargs
        value = standard_value
        found = False
        for pn in possible_names:
            if pn in self.kw_keys and not found:
                value = self.dict_kw[pn]
                found = True
                
        return value
        
    def __date_roll__(self):
        
        """
        Função para rolagem de data de início e fim (dia útil mais próximo)
        
            Caso a data inicial inserida (val_date) não seja dia útil, rolará 
        para o dia útil subsequente mais próximo. O mesmo será feito para o 
        vencimento
        
        """
        
        self.val_date = np.busday_offset(self.val_date, 0,
                                         roll = 'forward',
                                         holidays = self.holidays)
        
        self.maturity = np.busday_offset(self.maturity, 0,
                                           roll = 'forward',
                                           holidays = self.holidays)

    
    def __price__(self):
        
        """
        
        Método de cálculo do preço do Bond
            
            O método se utiliza da curva de juros fornecida ou criada, para
        precificar cada um dos fluxos de investimento
        
        """
        
        self.pz = self.dus/252.
        
        if isinstance(self.yield_curve, type(FlatForward([0], [1]))):
            #   Caso o objeto fornecido em yield_curve exista, fará o cálculo
            # na curva de juros
            self.discount_factors = 1./(1. + self.yield_curve(self.dus)) ** self.pz
        else:
            # Caso não tenha objeto, será calculado utilizando YTM
            self.discount_factors = 1./(1. + self.bond_yield) ** self.pz
        
        
        self.cotacao = self.fatores *  self.discount_factors
        self.vp_fatores = self.face_value * self.VNA * self.cotacao
        self.price = sum(self.vp_fatores)
        self.portfolio_value = self.price * self.quantity
    
    def __risks__(self):
        
        """
        Função de cálculo dos riscos do Bond
        
        Riscos disponíveis:
            - Duration
            - Modified Duration
            - DV01
            - Convexidade
        """
        
        durs = (self.pz * self.cotacao * self.VNA * self.face_value)/self.price
        self.duration = sum(durs)
        self.mod_duration = self.duration/(1.+self.bond_yield)
        self.dvs = self.mod_duration * self.vp_fatores / 10000.
        self.dv01 = -sum(self.dvs)
        cvxs = (1. / (1. + self.bond_yield) ** 2.) * (self.cotacao * self.VNA * self.face_value * self.pz * (self.pz + 1.))/self.price
        self.convexity = sum(cvxs)
        
        # Portfolio
        self.portfolio_dv01 = self.dv01 * self.quantity
        self.portfolio_dvs  = self.dvs * self.quantity
        self.portfolio_convexity = self.convexity * self.quantity
        
    def risk_report(self,
                    suppress : bool = True):
        
        """
        
        Função para cálculo e fornecimento do report de risco do ativo
        
            Cria um report que mostra a quebra do DV01 por KRDV01 nos buckets
        fornecidos pelo usuário
        
        """
        
        if not suppress:
            
            print(tabulate([['Duration'     , self.duration],
                            ['MDuration'    , self.mod_duration],
                            ['DV01'         , self.dv01],
                            ['Convexidade'  , self.convexity]],
                            headers = ['Risco', 'Valor']))
            
            print('\n')
            
            if self.bucketting:
                
                print(tabulate([[x, y, z] for x, [y, z] in self.curve_risks.items()],
                               headers = ['Bucket', 'dus', 'dv01'],
                               floatfmt = [".0f", ".0f", ".4f"]))
        
        # Para gerar um dataframe da quebra de risco:
        # pd.DataFrame(self.risk_report(True)[1], index = ['dus', 'dv01']).T
        
        ans = [{'Duration'           : self.duration,
               'Duration_Modificada' : self.mod_duration,
               'DV01'                : self.dv01,
               'Convexidade'         : self.convexity}]
        
        if self.bucketting: ans.append(self.curve_risks)
        return ans
    
    def __bucketting__(self,
                       quantidade : int = 1,
                       suppress   : bool = True):
        
        """
        Função que fornece o bucketeamento do risco do ativo
        
            Alocação de risco por vértices fixos determinados pelo usuário
        
        """
        
        # Caso o usuário já tenha preenchido a quantidade no init, utilizará ela
        quantidade = self.quantity if self.quantity != 1 else quantidade
        
        # Dentre as funções feitas é a mais lenta, tenho que melhorar
        # Bucketting piora o processamento em 1.5 a 3x o tempo necessário
        self.bucketting = True # Caso o usuário rode manualmente, override
        buckets_default = {'1M'  : 21,   '3M' : 63,   '6M'  : 126,  '9M'  : 189,  '1Y'  : 252,
                           '18M' : 378,  '2Y' : 504,  '3Y'  : 756,  '4Y'  : 1008, '5Y'  : 1260,
                           '7Y' : 1764, '10Y' : 2520, '20Y' : 5040, '30Y' : 7560}
        
        if not self.risk_buckets: self.risk_buckets = buckets_default
        
        buckets_list = np.array([self.risk_buckets[bucket] for bucket in self.risk_buckets])
        buckets_list.sort()
        
        buckets_value = np.zeros(buckets_list.shape)
        
        min_serie = min(buckets_list)
        max_serie = max(buckets_list)
        
        def __find_nearest__(value : float,
                             array : np.ndarray):
    
            """
            Method used to find the nearest points of a given maturity
            """
            
            idx = np.searchsorted(array, value, side="left")
        
            if idx > 0 and (idx == len(array) or np.abs(value - array[idx-1]) < np.abs(value - array[idx])):
                idx = idx - 1
            
            if array[idx] < value and idx < len(array) - 1:
              idx_1, idx_2 = idx, idx + 1
            elif array[idx] > value and idx > 0:
              idx_1, idx_2 = idx - 1, idx
            elif idx == len(array) - 1 or idx == 0:
              idx_1, idx_2 = idx, idx 
        
            return np.array([idx_1, idx_2])
        
        def __closest__(maturity : float,
                        dus : list,
                        dvs : list):
            
            """
            For a given maturity this method will return the pair of maturities and yields closest to it
            """
        
            idxs = __find_nearest__(maturity, dus)
            dus = dus[idxs]
            dvs = dvs[idxs]
        
            return np.array([*dus, *dvs])
        
        for du, exposicao in zip(self.dus, self.dvs):
            if du in buckets_list:
                buckets_value[np.where(buckets_list == du)] += exposicao
            if du < min_serie:
                buckets_value[0] += exposicao * du / min_serie
            if du > max_serie:
                buckets_value[-1] += exposicao * du / max_serie
            if du > min_serie and du < max_serie:
                
                # Método antigo para calcular ant e post, válido mas menos eficaz
                # ant, post = sorted(buckets_list[np.sort(np.argpartition(list(map(lambda x: abs(x - du), buckets_list)), 2)[:2])])
                
                ant, post, dv_ant, dv_post = __closest__(du, buckets_list, buckets_value)
                
                # Cálculo da exposições
                exp_ant  = exposicao * (post - du)/(post - ant)
                exp_post = exposicao * (du - ant)/(post - ant)

                # Preenche os valores da quebra
                buckets_value[np.where(buckets_list == ant)]  = dv_ant + exp_ant
                buckets_value[np.where(buckets_list == post)] = dv_post + exp_post
                
        buckets_value = buckets_value * quantidade

        self.curve_risks = {bucket:[du, risco] for bucket, du, risco in zip(self.risk_buckets, buckets_list, buckets_value)}
        
    def structured_buckets(self):
        
        """
        Função de estruturação de dados de bucketeamento
        """
        
        if self.bucketting:
            df = pd.DataFrame(self.curve_risks,
                              index = ['du', 'KRDV01']).T.copy()
            df['RiskType'] = [self.risk_type] * len(df)
            return df
        
        else:
            
            raise Exception('Se você deseja dados estruturados de bucketting, forneça bucketting = True')
        
    def __str__(self):
        
        return f'{self.bond_name}|{str(self.maturity).replace("-","")}'

    def __repr__(self):
        return self.full_name
    
    def __len__(self):
        return len(self.fs.cupons)
    
    def __call__(self):
        return self.price


class BondSolver:
    
    def __init__(self,
                 base_bond : Bond,
                 precision : float = 1e-8,
                 max_iter  : int = 1000):
        """
        Classe de solução de bonds dado preço objetivo
        
        Parâmetros
        ----------
        base_bond : Bond
            Objeto Bond que será utilizado como base para o solver.
        precision : float, optional
            Precisão mínima, em reais, que se deseja atingir. The default is 1e-8.
        max_iter : int, optional
            Máximo de iterações a ser feito. The default is 1000.
        """
        self.bond      = deepcopy(base_bond)
        self.precision = precision
        self.max_iter  = max_iter
        
    def __solve__(self,
                  price_obj : float):
        
        """
        Método principal de solução para um preço desejado
        
        Parâmetros
        ----------
        price_obj : float
            Objetivo em preço a ser atingido.
        """
        
        self.price_obj = price_obj

        bond = deepcopy(self.bond)
        
        d = []
        
        i = 0
        error = bond.price - self.price_obj
        d.append([bond.bond_yield, bond.price, self.price_obj, bond.dv01, error, deepcopy(bond)])
        
        while i < self.max_iter and abs(error) > self.precision:
            
            # Newton-Raphson formalizado:
            # x_n     = x_(n-1) - f(x_n)/f'(x_n)
            
            # x_n     = estimativa
            # x_(n-1) = bond.bond_yield
            # f(x_n)  = bond.price
            # f'(x_n) = bond.dv01
            
            #  Detalhe : sensibilidade por DV01 mostra o shift, em $, para cada
            # variação de 0.01% na taxa de desconto, temos que considerar isso
            # para a derivada que será utilizada
            
            est_yield = bond.bond_yield + (self.price_obj - bond.price)/bond.dv01/10000.
            bond.bond_yield    = est_yield
            bond.__price__()
            bond.__risks__()
            error     = self.price_obj - bond.price
            
            if i > 0: d.append([bond.bond_yield, bond.price, self.price_obj, bond.dv01, error, deepcopy(bond)])
            
            i+=1
        
        df = pd.DataFrame(d,
                          columns = ['Yield', 'Price', 'Price_Objective', 'DV01', 'Error', 'Bond'],
                          index = pd.Series(range(1, i+1), name = 'Iteration'))
        
        return {'Sol_Yield'        : bond.bond_yield,
                'Sol_Precision'    : error,
                'iterations'       : i,
                'initial_bond'     : self.bond,
                'final_bond'       : bond,
                'convergence_path' : df}
    
    def __call__(self,
                 price_obj : float) -> dict:
        """
         Caso o objeto seja chamado, irá retornar a solução para o preço inputado
        no momento de chamada
        """
        return self.__solve__(price_obj)

class LFT(Bond):
    
    """
    Classe que compila Bond com argumentos predefinidos para pricing de LFT
    """
    
    def __init__(self,
                  val_date   : Union[str, np.datetime64, None],
                  maturity   : Union[str, np.datetime64, None],
                  bond_yield : Union[int, float, None],
                  VNA        : float,
                  **kwargs):

        super().__init__(val_date, maturity,
                         bond_yield,
                         bond_name = 'LFT',
                         VNA = VNA,
                         risk_type = 'Over',
                         **kwargs)

class LTN(Bond):
    
    """
    Classe que compila Bond com argumentos predefinidos para pricing de LTN
    """
    
    def __init__(self,
                  val_date   : Union[str, np.datetime64, None],
                  maturity   : Union[str, np.datetime64, None],
                  bond_yield : Union[int, float, None],
                  **kwargs):

        super().__init__(val_date, maturity,
                         bond_yield, face_value = 1000.,
                         bond_name = 'LTN',
                         **kwargs)
        
class NTNB(Bond):
    
    """
    Classe que compila Bond com argumentos predefinidos para pricing de NTN-B
    """
    
    def __init__(self,
                  val_date   : Union[str, np.datetime64, None],
                  maturity   : Union[str, np.datetime64, None],
                  bond_yield : Union[int, float, None],
                  VNA        : float,
                  **kwargs):

        super().__init__(val_date, maturity,
                         bond_yield,
                         annual_coupon = .06,
                         coupon_frequency = 2,
                         bond_name = 'NTNB',
                         VNA = VNA,
                         risk_type = 'Real',
                         **kwargs)
        
class NTNF(Bond):
    
    """
    Classe que compila Bond com argumentos predefinidos para pricing de NTN-F
    """
    
    def __init__(self,
                  val_date   : Union[str, np.datetime64, None],
                  maturity   : Union[str, np.datetime64, None],
                  bond_yield : Union[int, float, None],
                  **kwargs):

        super().__init__(val_date, maturity,
                         bond_yield, face_value = 1000.,
                         annual_coupon = .1,
                         coupon_frequency = 2,
                         bond_name = 'NTNB',
                         **kwargs)
