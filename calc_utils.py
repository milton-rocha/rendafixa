# -*- coding: utf-8 -*-
"""
Author : Milton Rocha
Medium : https://medium.com/@milton-rocha
"""

import pandas as pd
import numpy  as np

from date_utils  import (feriados,
                         edate)
from typeguard   import check_type
from typing      import Union

class Fluxos:

        """
        Classe de fluxos que é responsável por fornecer as datas que possuem cupons de juros
        """
        
        def __init__(self,
                     valDate      : Union[str, np.datetime64, None],
                     vencimento   : Union[str, np.datetime64, None],
                     cupomAnual   : Union[float, int],
                     freqCupons   : int = 2,
                     fer          : Union[list, np.ndarray, pd.core.frame.DataFrame, None] = None,
                     busDay_roll  : bool = True,
                     check_inputs : bool = False):

            self.valDate, self.vencimento, self.fer, self.busDay_roll = valDate, vencimento, fer, busDay_roll
            self.cupomAnual, self.freqCupons = cupomAnual, freqCupons

            # Caso o usuário não forneça alguma variável (que possa ser None) a classe atribuirá variável default
            if not self.valDate: self.valDate = np.datetime64('today', 'D')
            self.fer = feriados() if self.fer is None else self.fer
            
            # Caso a valDate ou o vencimento sejam inseridos como str, serão convertidos para datetime64, formato 'YYYY-MM-DD'
            self.valDate = self.valDate if isinstance(self.valDate, np.datetime64) else np.datetime64(self.valDate, 'D')
            self.vencimento = self.vencimento if isinstance(self.vencimento, np.datetime64) else np.datetime64(self.vencimento, 'D')
            
            # Caso o usuário deseje checagem de inputs, irá fazer
            # Piora em 15 a 25% a velocidade do código para grande volume de bonds
            if check_inputs: self.__check_data__()
            self.__calc__()
        
        def __check_data__(self):
            
            # Faz os checks para ver se o usuário está inserindo os inputs de tipo correto para cada variável
            check_type('valDate',     self.valDate, Union[str, np.datetime64, None])
            check_type('vencimento',  self.vencimento, Union[str, np.datetime64, None])
            check_type('cupomAnual',  self.cupomAnual, Union[float, int])
            check_type('freqCupons',  self.freqCupons, int)
            check_type('fer',         self.fer, Union[list, np.ndarray, pd.core.frame.DataFrame, None])
            check_type('busDay_roll', self.busDay_roll, bool)
        
        
        def __calc__(self):
            
            # O valorCupom é definido como o valor de pagamento, em percentual, para um determinado padrão de juros com frequência n
            
            self.valorCupom = (1.0 + self.cupomAnual) ** (1.0 / self.freqCupons) if self.freqCupons != 0 else (1.0 + self.cupomAnual)
            self.cupons = []

            # Começamos ao contrário, estipulado que o primeiro fluxo será o da data de vencimento do papel
            fluxo = self.vencimento

            # Enquanto o fluxo calculado for maior que a data de valuation, o fluxo será considerado e adicionado à lista
            if self.freqCupons != 0:
                while fluxo > self.valDate:
                    self.cupons.append(fluxo)
                    fluxo = edate(fluxo, -int(12.0 / self.freqCupons))
            else:
                self.cupons.append(fluxo)

            #  Caso o usuário deseje que o código retorne o próximo dia útil,
            # o código irá rolar todas as datas de fluxo para o dia útil seguinte
            if self.busDay_roll: self.cupons = np.busday_offset(self.cupons, 0, roll='forward', holidays = self.fer)
            if self.busDay_roll: self.vencimento = np.busday_offset(self.vencimento, 0, roll = 'forward', holidays = self.fer)

            #  Para garantir que os fluxos estejam em ordem crescente (inversa ao que foi construído),
            # é necessário um np.sort()
            self.cupons = np.sort(self.cupons)

            # São calculados os dias úteis para cada um dos fluxos
            self.dus = np.busday_count(self.valDate, self.cupons, holidays = self.fer)

            #  Os fatores de juros são atribuídos como sendo somente juros semestrais para as datas de cupom e
            # semestrais + principal no vencimento
            self.fatores = np.where(self.cupons != self.vencimento, self.valorCupom - 1.0, self.valorCupom)

        def __call__(self):
            
            # É retornado um dict com as datas de 'Cupom', os dias úteis das datas 'du' e os fatores de juros, 'fator'
            return {'Cupom' : self.cupons,
                    'du'    : self.dus,
                    'fator' : self.fatores}
        
        def __len__(self):
            return len(self.cupons)
        
        def __str__(self):
            # Se o usuário solicitar str(Fluxos()) retornará um nome genérico
            return f'Fluxos(valDate = {self.valDate}, vencimento = {self.vencimento}, cupomAnual = {self.cupomAnual}, freqCupons = {self.freqCupons}, busDay_roll = {self.busDay_roll})'

        def __repr__(self):
            # Quando estiver em uma lista retornará os parâmetros fornecidos caso o usuário solicite str(fluxos())
            return f'Fluxos(valDate = {self.valDate}, vencimento = {self.vencimento}, cupomAnual = {self.cupomAnual}, freqCupons = {self.freqCupons}, busDay_roll = {self.busDay_roll})'


class FlatForward:

  """
  Flat Forward Exponential Interpolation Method
  - This object provides an interpolation for the provided YieldCurve with a simple callable property
  - This method is the official interpolation method for the Pré-DI Brazilian Yield Curve if days_year = 252
  """

  def __init__(self,
               maturities  : np.ndarray,
               yields      : np.ndarray,
               days_year   : int  = 252,
               extrapolate : bool = False):
    
    """
    Variables:
      - maturities  : np.ndarray, maturities provided for the interpolation, in days
      - yields      : np.ndarray, yields provided for the interpolation
      - days_year   : int, days in a year, provided for the interpolation
      - extrapolate : bool, if True, it will extrapolate the Yield Curve
    """

    assert len(maturities) == len(yields), f'Maturities have len ({len(maturities)}) while yields have len ({len(yields)})'

    self.maturities  = maturities
    self.yields      = yields
    self.days_year   = days_year
    self.extrapolate = extrapolate

  def __find_nearest__(self,
                       value : float,
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

  def __closest__(self,
                  maturity : float):
    
    """
    For a given maturity this method will return the pair of maturities and yields closest to it
    """

    idxs = self.__find_nearest__(maturity, self.maturities)
    mats = self.maturities[idxs]
    ys   = self.yields[idxs]

    return np.array([*mats, *ys])
    
  def __forward__(self,
                  long_yield     : float,
                  long_maturity  : float,
                  short_yield    : float,
                  short_maturity : float):
    
    p1 = (1. + long_yield) ** (long_maturity/self.days_year)
    p2 = (1. + short_yield) ** (short_maturity/self.days_year)
    fwd = (p1/p2) ** (self.days_year/(long_maturity - short_maturity)) - 1.
    
    return fwd

  def __interpolation__(self,
                        maturity : float):
    
    """
    General interpolation method, will find the pair of maturities and yields closest and interpolate the yields
    """


    if maturity > self.maturities[-1] or maturity < self.maturities[0]:
      if self.extrapolate == True:
        return self.__extrapolation__(maturity) if maturity > self.maturities[-1] else self.yields[0]
      else:
        raise ValueError(f'Error, this maturity ({maturity}) cannot be interpolated while extrapolate = False')

    if maturity in self.maturities:
        idx = list(np.where(self.maturities == maturity))[0][0]
        return self.yields[idx]

    short_maturity, long_maturity, short_yield, long_yield = self.__closest__(maturity)
    
    fwd = self.__forward__(long_yield, long_maturity, short_yield, short_maturity)
    
    short_factor = (1. + short_yield) ** (short_maturity/self.days_year)
    fwd_factor   = (1. + fwd) ** ((maturity - short_maturity)/self.days_year)

    interp_factor =  short_factor * fwd_factor 
    interp_rate   = interp_factor ** (self.days_year/maturity) - 1.

    return interp_rate.astype(float)

  def __extrapolation__(self,
                        maturity : float):
    
    """
    In the case of extrapolate = True, the method will provide an Flat Forward Extrapolation using the last Forward Factor
    """

    long_yield     = self.yields[-1]
    short_yield    = self.yields[-2]
    long_maturity  = self.maturities[-1]
    short_maturity = self.maturities[-2]

    fwd_factor = ((1. + long_yield) ** (long_maturity / self.days_year)) / ((1. + short_yield) ** (short_maturity / self.days_year))

    ext = (((1. + long_yield) ** (long_maturity / self.days_year)) \
          * (fwd_factor ** ((maturity - long_maturity) / (long_maturity - short_maturity)))) \
          ** (self.days_year / maturity)

    return ext - 1. 

  def __call__(self,
               maturities : np.ndarray):
    
    """
    When called, the object will interpolate the provided maturities
    """
    maturities = maturities if isinstance(maturities, (list, np.ndarray)) else np.array([maturities])

    return np.array(list(map(self.__interpolation__, maturities)))

  def __len__(self):
    return len(self.maturities)

  def __str__(self):
    return f'FlatForward(maturities = {len(self.maturities)}, yields = {len(self.yields)}, days_year = {self.days_year}, extrapolate = {self.extrapolate})'

  def __repr__(self):
    return self.__str__()
