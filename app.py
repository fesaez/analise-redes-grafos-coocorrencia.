
import pandas as pd
from itertools import combinations
from collections import Counter
import networkx as nx
from pyvis.network import Network
import streamlit as st
import os

# --- 1. Carregar e Preparar os Dados ---
# Assumindo que 'ifood_df.csv' está no mesmo diretório do script.
# Ajuste o caminho conforme necessário se o arquivo estiver em outro local.
try:
    df = pd.read_csv('ifood_df.csv')
except FileNotFoundError:
    # Fallback para o caminho comum do Colab se não encontrar no diretório atual
    df = pd.read_csv('/content/ifood_df.csv')

# Identificar as colunas de produtos (MntWines, MntFruits, etc.)
product_columns = [col for col in df.columns if col.startswith('Mnt')]

# Criar uma nova coluna 'categorias_compradas' que contém uma lista das categorias compradas por cada cliente
df['categorias_compradas'] = df[product_columns].apply(
    lambda row: [col.replace('Mnt', '') for col in product_columns if row[col] > 0], axis=1
)

# A série 'pedidos' agora será baseada nas categorias compradas por cliente (index do DataFrame)
pedidos = df['categorias_compradas']

# 2. Filtrar apenas clientes com mais de 1 item comprado
pedidos_multiplos = [p for p in pedidos if len(p) > 1]

# 3. Gerar pares de co-ocorrência (arestas)
pares_itens = []
for cesta in pedidos_multiplos:
    pares = list(combinations(sorted(set(cesta)), 2))
    pares_itens.extend(pares)

# 4. Contar a frequência de cada conexão (peso da aresta)
contagem_conexoes = Counter(pares_itens)

# --- 2. Construir o Grafo ---
G = nx.Graph()

for (item_a, item_b), peso in contagem_conexoes.items():
    if peso >= 3:  # Filtro de corte para não poluir a rede
        G.add_edge(item_a, item_b, weight=peso)

# Cálculo das métricas de centralidade
grau = nx.degree_centrality(G)
intermediacao = nx.betweenness_centrality(G)

# Salvar as métricas nos próprios nós para visualização
nx.set_node_attributes(G, grau, 'centralidade_grau')
nx.set_node_attributes(G, intermediacao, 'centralidade_pontes')

# --- 3. Criar a Aplicação Streamlit para Visualização ---
st.title("Rede de Conexões e Co-ocorrência de Produtos (Design Melhorado)")

# Configurar a rede visual com opções aprimoradas
net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white",
              notebook=False, # Definir como False ao rodar como script Streamlit
              cdn_resources='remote')

# Adicionar configurações de física para um layout mais estável e interativo
net.set_options("""
var options = {
  "nodes": {
    "font": {
      "size": 12,
      "face": "arial"
    }
  },
  "edges": {
    "color": {
      "inherit": true
    },
    "smooth": {
      "type": "continuous"
    }
  },
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.01,
      "springLength": 100,
      "springConstant": 0.08
    },
    "minVelocity": 0.75,
    "solver": "forceAtlas2Based",
    "stabilization": {
      "enabled": true,
      "iterations": 1000,
      "updateInterval": 25
    }
  }
}
""")

# Configurar tamanho do nó proporcional à centralidade de grau
max_degree = max(grau.values()) if grau else 1
min_node_size = 10
max_node_size = 50

for node in G.nodes():
    degree_centrality = grau.get(node, 0)
    if max_degree > 0:
        node_size = min_node_size + (degree_centrality / max_degree) * (max_node_size - min_node_size)
    else:
        node_size = min_node_size

    info = (
        f"<b>Item:</b> {node}<br>"
        f"<b>Co-ocorrências (Grau):</b> {G.degree[node]}<br>"
        f"<b>Centralidade de Grau:</b> {degree_centrality:.4f}<br>"
        f"<b>Centralidade de Intermediação:</b> {intermediacao.get(node, 0):.4f}"
    )

    net.add_node(node, label=node, size=node_size, title=info,
                 color={'background': '#FFD700', 'border': '#FFA500'}) # Cor dourada para os nós

for edge in G.edges(data=True):
    edge_weight = edge[2]['weight']
    net.add_edge(edge[0], edge[1], value=edge_weight, width=max(1, edge_weight / 50),
                 color={'color': '#888888', 'highlight': '#FFFFFF'}) # Cor das arestas

# Exportar para HTML
html_file_path = "grafo_melhorado.html"
net.save_graph(html_file_path)

with open(html_file_path, 'r', encoding='utf-8') as f:
    html_code = f.read()

st.iframe(html_code, height=750)
