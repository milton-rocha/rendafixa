from pricer import Bond, BondSolver
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Exemplo 1. Precificando uma NTN-B 2060-08-15
# Data-base : 2022-07-29

val_date = '2022-07-29'

VNA = 3985.783028

# Cria um objeto Bond customizado para a NTNB, que herda todos os atributos e variáveis
ntnb = NTNB('2022-07-29', '2060-08-15', 0.062718, VNA, bucketting = True)
structured_data = ntnb.structured_buckets()
structured_data

# Construção do gráfico de KRDV01 da NTN-B, RiskType = Real
fig, ax = plt.subplots()

structured_data['KRDV01'].plot.bar(color = 'blue', ax = ax)
ax.set_title('Quebra de KRDV01 NTNB 2060 @ 6,2718% para 2022-07-29', fontsize = 30, fontweight = 'bold', family = 'Arial')
ax.tick_params(axis = 'x', rotation = 45, which = 'major', labelsize = 14)
ax.tick_params(axis = 'y', which = 'major', labelsize = 14)


# Exemplo 2. Simulando um portfólio com diversos TPF
# Títulos personalizados com número de quantidades != 1 para cálculo de portfólio
ltn  = LTN('2022-07-29', '2026-01-01', 0.127492, quantity = 132835, bucketting = True)
ntnf = NTNF('2022-07-29', '2033-01-01', 0.129348, quantity = 98475, bucketting = True)
ntnb = NTNB('2022-07-29', '2045-05-15', 0.062480, VNA, quantity = 15684, bucketting = True)
# Buckets são estruturados e calculados
ltn_buck  = ltn.structured_buckets()
ntnf_buck = ntnf.structured_buckets()
ntnb_buck = ntnb.structured_buckets()
# Empilhamento de todas as bases em somente uma
total = ltn_buck.append(ntnf_buck).append(ntnb_buck).copy()
# Pivot table nada mais será do que uma sumarização dos valores já presentes no total (todos os buckets agrupados)
# Visto que a tag de RiskType está presente na coluna de mesmo nome, os valores serão agrupados em colunas representativas
# RiskType da carteira ['Nominal', 'Real']
pivot = pd.pivot_table(total,
                       index = [total.index, 'du'],
                       columns = 'RiskType',
                       values = 'KRDV01',
                       aggfunc = np.sum).sort_values('du').droplevel(1, axis = 0)

# Construção do gráfico
fig, ax = plt.subplots()
pivot.plot.bar(color = ['blue', 'red'], ax = ax)
ax.tick_params(axis = 'x', rotation = 45, which = 'major', labelsize = 14)
ax.tick_params(axis = 'y', which = 'major', labelsize = 14)
ax.set_title('KRDV01 Porfólio Simulado para 2022-07-29', fontsize = 30, fontweight = 'bold', family = 'Arial')


# Exemplo 3. Solucionando Bond com o BondSolver
# Supõe-se aqui que um usuário tenha o valor de ajuste da NTN-F 2033 para a data de 2022-07-29
# Este usuário deseja descobrir qual seria a taxa equivalente ao preço que foi divulgado

# Inicializa-se o objeto com 10% de taxa anual (par price) somente para ter um objeto NTNF criado
ntnf_base = NTNF('2022-07-29', '2033-01-01', 0.1)

# PU divulgado para o título na data: 849.857168
# Resolve-se o problema com o BondSolver
# Cria-se primeiramente o objeto do BondSolver, inicializando suas variáveis
bs = BondSolver(ntnf_base)

# Através da função call calcula-se o objeto novo
result = bs(849.857168)

# Atributos:
# Print do resultado de convergência com objetos utilizados no caminho, em formato de DataFrame
result['convergence_path']

# Número de iterações utilizado
result['iterations'] # 4

# Bond resultante
result['final_bond'] # @ NTNF|2033|12.93%
# Preço
result['final_bond'].price # 849.8571680000019
