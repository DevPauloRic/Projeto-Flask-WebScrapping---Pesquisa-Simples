#Bibliotecas principais do Flask e ORM
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

#Web scraping
from bs4 import BeautifulSoup
import requests

#Plotly para gráficos
import plotly.express as px

#Contador de palavras e stopwords
from collections import Counter
import nltk
from nltk.corpus import stopwords
#Baixa stopwords do nltk se necessário, provavelmente sim.
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


#Configs Flask + Banco de Dados SQLite
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///valores.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

#Molde que vai armazenar resultados do scrapping
class Resultado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    termo = db.Column(db.String(200), nullable=False)
    texto = db.Column(db.Text, nullable=False)   # títulos e snippets raspados

#Scrapping usando o BeautifulSoup 
def scrape_duckduckgo(termo, max_results=10): #Recebe um termo e o max results == numero de resultados esperados..
    
    #Realiza scraping no DuckDuckGo e retorna uma lista de títulos + snippets.
    
    url = f"https://html.duckduckgo.com/html/?q={termo}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    resultados = []
    for div in soup.find_all("div", class_="result__body", limit=max_results):
        titulo = div.find("a", class_="result__a")
        snippet = div.find("a", class_="result__snippet")
        if titulo:
            texto = titulo.get_text()
            if snippet:
                texto += " " + snippet.get_text()
            resultados.append(texto)
    return resultados


#Passando a rota do Flask
@app.route('/', methods=['GET', 'POST'])
def index():
    
    #Rota principal: faz scraping, salva no banco, gera gráfico de barras.
    
    if request.method == 'POST':
        termo = request.form.get('termo')
        if termo:
            # Limpa o banco de dados antes de salvar novos resultados
            Resultado.query.delete()
            db.session.commit()
            # Realiza scraping
            try:
                resultados = scrape_duckduckgo(termo, max_results=20)
            except Exception as e:
                resultados = [f"Erro ao buscar resultados: {e}"]

            # Salva os resultados no banco
            for r in resultados:
                novo = Resultado(termo=termo, texto=r)
                db.session.add(novo)
            db.session.commit()
        # Redireciona para GET após POST
        return redirect(url_for('index'))

    #query de todos os resultados do banco
    todos_resultados = Resultado.query.all()
    textos = [r.texto for r in todos_resultados]
    print(textos) #Verifdica se os textos estão sendo capturados...
    
    head_5 = textos[:5] #usando textos para mostrasr os 5 primeiros resultados no front

    # Geração do gráfico de barras + o top 3 de palavras
    top3 = []
    if textos:
        texto_unico = " ".join(textos)
        stop_words = set(stopwords.words('portuguese'))
        palavras_filtradas = [w for w in texto_unico.split() if w.lower() not in stop_words and len(w) > 2]

        #Conta frequência das palavras
        contagem = Counter([w.lower() for w in palavras_filtradas])
        top3 = contagem.most_common(3)

        # Gráfico de barras com as 15 mais frequentes
        df = [{"Palavra": p, "Frequência": f} for p, f in contagem.most_common(15)]
        fig = px.bar(df, x="Palavra", y="Frequência", title="Palavras mais frequentes")
        grafico_html = fig.to_html(full_html=False)
    else:
        grafico_html = None

    #Renderiza o template com os dados 
    return render_template('index.html', head_5=head_5,grafico=grafico_html,top3=top3)

#Comando para rodar o app
if __name__ == '__main__':
    # Cria as tabelas do banco se não existirem
    with app.app_context():
        db.create_all()
    app.run(debug=True)
