# rendafixa
Repositório dedicado à modelagem e cálculos em renda fixa

Performance do objeto de pricing

![Performance]([https://github.com/milton-rocha/rendafixa/tree/main/example_images/performance_codigo.png](https://github.com/milton-rocha/rendafixa/blob/86559dc44a94be9b96315b9125575181f89ddd08/example_images/performance_codigo.png))

### date_utils.py
- Contém as funções utilitárias de datas, como edate() e feriados() e algumas funções para formatação de datas

## calc_utils.py
### Fluxos
Classe responsável pelo cálculo e disponibilização de objeto de fluxos, desde que sejam padronizados seguindo os valores propostos na classe para inicializá-la

Principais variáveis disponíveis para o objeto:
- obj.fatores fornece todos os fatores dos fluxos de caixa calculados
- obj.cupons fornece todas as datas nas quais ocorrem pagamento de fluxo
- obj.dus fornece todos os vencimentos, em dias úteis, dos fluxos de caixa calculados

### FlatForward
Classe para construção de uma curva de juros que se utiliza de interpolação e extrapolação (quando desejado) FlatForward para os pontos que a compõe

Principais variáveis disponíveis para o objeto:
- obj([lista_vencimentos]) - call do objeto - irá interpolar todas as taxas fornecidas na lista_vencimentos
- obj.maturities, irá fornecer todos os vencimentos que foram inseridos para sua construção
- obj.yields, irá fornecer todas as taxas que foram inseridas para sua construção
- obj.__closest__(maturity) irá fornecer os dois pontos, e suas respectivas taxas, mais próximas ao ponto de vencimento que se deseja interpolar
- obj.__forward__(long_yield, long_maturity, short_yield, short_maturity) irá fornecer a taxa de juros forward calculada com os dados
- len(obj) irá retornar o tamanho da sequência de dados fornecida para sua construção
- str(obj) ou listas que contenham o objeto, irá retornar uma string contento os principais dados da ETTJ construída

## pricer.py
### Bond
Classe responsável por todos os cálculos de precificação e riscos de Bonds de forma generalizada

Melhor prática para aproveitar da performance do código:

- Fornecer YieldCurve (FlatForward, caso necessário) como variável já calculada presente nos kwargs

- Fornecer holidays (feriados) como variável já calculada presente nos kwargs (código lê o parquet salvo na mesma pasta por default)

**kwargs disponíveis:

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
      

Principais variáveis disponíveis para o objeto:

#### Variáveis relativas ao Pricing

- obj.price retorna o preço calculado para o ativo

#### Variáveis de Risco de Mercado

Nível de ativo:

- obj.duration retorna a duration calculada para o ativo
- obj.mod_duration retorna a duration calculada para o ativo
- obj.dv01 retorna o DV01 calculado para o ativo
- obj.dvs retorna os KRDV01 para cada fluxo calculado para o ativo
- obj.convexity retorna a convexidade calculada para o ativo
- obj.curve_risks retorna as medidas de risco principais, só aparece caso obj.bucketting = True
- obj.risk_report(True) irá dar print na tela dos principais riscos em formato tabulate e retornar a matriz obj.curve_risks

Nível de portfólio (só terá diferenças caso obj.quantity != 1):

- obj.portfolio_dv01 retorna o DV01 para o portfólio inteiro (quantidade * obj.dv01)
- obj.portfolio_dvs retorna os KRDV01 para o portfólio inteiro (quantidade * obj.dvs)
- obj.portfolio_convexity retorna a convexidade para o portfólio inteiro (quantidade * obj.convexity)

Bucketting/Bucketeamento:

- obj.risk_buckets retorna os buckets utilizados para fazer a alocação via obj.__bucketting__()
- obj.structured_buckets() método retorna o bucketeamento em formato de Pandas DataFrame, com o RiskType incluso

#### Ferramental Geral:

- str(obj) retorna o bond_name seguido de características do bond, como, vencimento
- caso em uma lista, o obj será descrito com string que adiciona ao str(obj) a taxa do objeto (bond_yield)
- len(obj) retorna o número de fluxos de caixa registrados para o objeto
- obj() retorna o preço do objeto (igual à obj.price)
