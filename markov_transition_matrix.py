import numpy  as np
import pandas as pd
import requests

def get_copom(date_filter : str = '2010-01-01'):
    
    """
    Função para download de série histórica das decisões do COPOM
    """

    url = "https://www.bcb.gov.br/api/servico/sitebcb/historicotaxasjuros"
    response = requests.get(url)
    j = response.json()
    
    # Normaliza o json de conteúdo que o site devolve
    tbl_copom = pd.json_normalize(j['conteudo'])
    
    # Valores com dtype correto
    tbl_copom['DataReuniaoCopom']   = pd.to_datetime(tbl_copom['DataReuniaoCopom']).values.astype('datetime64[D]')
    tbl_copom['DataInicioVigencia'] = pd.to_datetime(tbl_copom['DataInicioVigencia']).values.astype('datetime64[D]')
    tbl_copom['DataFimVigencia']    = pd.to_datetime(tbl_copom['DataFimVigencia']).values.astype('datetime64[D]')
    tbl_copom['Vies'] = tbl_copom['Vies'].values.astype(str)
    
    # Decisão do COPOM
    tbl_copom['Decisão (bps)'] = (tbl_copom['MetaSelic'] - tbl_copom['MetaSelic'].shift(-1)) * 100.
    
    return tbl_copom[tbl_copom['DataReuniaoCopom'] >= date_filter].copy()

class TransitionMatrixCOPOM:
    
    """
    Classe para cálculo e fornecimento de matriz de transição (Markov) para as decisões do COPOM
    """
    
    def __init__(self,
                 decisions,
                 probability : bool = True):
        
        decisions = decisions.astype(str) \
                    if isinstance(decisions, (np.ndarray,
                                             pd.core.series.Series,
                                             pd.core.frame.DataFrame)) \
                    else np.array(decisions).astype(str)
        decisions = np.array([d.split('.')[0] for d in decisions])
        
        self.decisions = decisions
        
        self.__transition_matrix__(probability = probability)
        
    def __transition_matrix__(self,
                              probability : bool = True):
        
        """
        Método para calcular a matriz de transição para as decisões do COPOM já registradas e fornecidas
        
        Variáveis:
            probability : bool
                Se for True, irá calcular a probabilidade de acontecer cada cenário, caso False, calculará a quantidade de ocorrências
                
        Resultado:
            Preenche as propriedades do objeto:
                - self.transition_matrix  : matriz de transição calculada com texto equivalente de decisão, ex: Hike 25
                - self.transition_matrix_ : matriz de transição calculada com números no lugar de texto, na coluna e no índice
        """
        # Headers e Índices
        
        unique_decs = pd.Series(self.decisions).unique().astype(int)
        unique_decs = sorted(unique_decs)
        txt_decs    = [f'Alta {dec}' if int(dec) > 0 else \
                       ('Manutenção' if int(dec) == 0 else \
                        f'Corte {str(dec).replace("-", "")}') \
                           for dec in unique_decs]
        
        self.df_headers = txt_decs
        self.df_index   = self.df_headers
        
        # Decisões
        df = pd.DataFrame(self.decisions,
                          columns = ['Decisão'],
                          dtype = str)
        
        # Pares de transição entre a lista
        # df[:-1] contém as decisões em t
        # df.shift(-1)[:-1] contém as decisões em t+1
        # Colunas são t+1 e linhas t
        decision_pairs = df[:-1] + ',' + df.shift(-1)[:-1]
        
        transition_matrix = pd.DataFrame(columns = unique_decs,
                                         index   = unique_decs).fillna(0)
        
        for idx, vls in transition_matrix.iterrows():
            # Para cada linha do dataframe:
            # row_values.index = índice, decisão t
            # row_values.name  = coluna, decisão t+1
            for cel in vls.index.values:
                # Para cada um dos valores de células irá contar o número de ocorrências
                occ = np.count_nonzero(decision_pairs == f'{cel},{vls.name}')
                transition_matrix.iloc[transition_matrix.index.get_loc(cel),
                                       transition_matrix.columns.get_loc(vls.name)] = occ
        
        # Ignora a divisão por 0 retornando erro no numpy
        np.seterr(divide='ignore', invalid='ignore')
        
        # Caso a resposta desejada seja com a matriz em probabilidade (default)
        if probability:
            for idx, vls in transition_matrix.iterrows():
                transition_matrix.loc[idx,
                                      transition_matrix.columns] = vls.values/np.sum(vls)

        
        # Retorna a transition_matrix
        # Matriz de transição com números (decisão em bps)
        self._transition_matrix = transition_matrix.copy().fillna(0)
        self._transition_matrix.columns = self._transition_matrix.columns.values.astype(str)
        self._transition_matrix.index   = self._transition_matrix.index.values.astype(str)
        # Matriz de transição com decisões completas
        self.transition_matrix = self._transition_matrix.copy()
        self.transition_matrix.columns = self.df_headers
        self.transition_matrix.index   = self.df_index
        
        # Retorna o padrão do numpy error
        np.seterr(divide='warn', invalid='warn')
    
    def probability_pair(self,
                         pair,
                         matrix = None):
        
        """
        Método utilizado para se encontrar um par específico na matriz de transição
        
        Variáveis:
            pair: str
                Par para ser buscado, por exemplo, '25,50', buscará o par +25bps e +50bps
        """
        
        # Busca a probabilidade de um par de decisão
        pair = pair.split(',')
        
        matrix = matrix if not isinstance(matrix, type(None)) else self._transition_matrix
        
        try:
            idx = matrix.index.get_loc(pair[0])
            col = matrix.columns.get_loc(pair[1])
            return matrix.iloc[idx, col]
        except:
            return 0
    
    def path_probability(self,
                         path):
        """
        Método para cálculo de probabilidade de um caminho específico se executar em reuniões do COPOM
        
        Variáveis:
            path : list
                Lista contendo o caminho de juros proposto para as reuniões do COPOM
                ex: [0,50,25,25,50]
                
        Resultado:
            float:
                Probabilidade do caminho
        """
        path = path.astype(str) \
                if isinstance(path, (np.ndarray,
                                      pd.core.series.Series,
                                      pd.core.frame.DataFrame)) \
                else np.array(path).astype(str)
                
        path = pd.Series(np.array([d.split('.')[0] for d in path])) # Caminho de decisões
        n_steps = len(path) - 1 # Número de passos dados desde o estado inicial
        
        matrix = self._transition_matrix
        # Cálculo da potência da matriz pelo número de passos dados ao longo do caminho
        matrix_steps = np.linalg.matrix_power(matrix, n_steps)
        # Construção do dataframe da matriz, já calculada a potência
        matrix_steps = pd.DataFrame(matrix_steps,
                                    columns = matrix.columns,
                                    index   = matrix.index)
                                    
        first_step = path.values[0] # Primeiro estado do caminho
        last_step  = path.values[-1] # Último estado do caminho
        
        # Retorna o par de probabilidade da matriz, já calculada a potência pelos passos
        return self.probability_pair(f'{first_step},{last_step}', matrix_steps)
