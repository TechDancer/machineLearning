import re
import unidecode
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression

import pandas as pd

class FooModel(object):
    def __init__(self, embedding=CountVectorizer, mod=MultinomialNB):
        self.embedding = embedding()
        self.mod = mod()

    def __repr__(self):
        return 'FooModel '+str(type(self.mod))+', '+str(type(self.embedding))

    def embed(self, texts) -> ([],[]):
        self.matrix = self.embedding.fit_transform(texts)
        self.headers = self.embedding.get_feature_names()
        return self.matrix, self.headers

    def train(self, X, y) -> None:
        self.mod.fit(X, y)

    def score(self, X, y) -> float:
        return self.mod.score(X, y)

    def predict(self, X) -> ([str],[float]):
        return self.mod.predict(X), self.mod.predict_proba(X)


class FooNLP(object):
    STOPLIST = ['i', 'you', 'am', 'r', 'a', 'an', 'and']

    def __init__(self, model=FooModel(), stoplist=STOPLIST):
        self.model = model
        self.stoplist = stoplist

    def __repr__(self):
        return 'FooNLP: '+self.corpus +', '+str(type(self.model))

    def full_proc(self, text) -> str:
        text = self.expand(text)
        text = self.clean(text)
        text = self.lemmitize(text)
        text = self.destop(text)
        return text

    def clean(self, text) -> str:
        text = unidecode.unidecode(text)  # clean accents
        text = re.sub(r'[^a-zA-Z\s]', '', text, re.I | re.A)
        text = text.lower()
        text = text.strip()
        return text

    def expand(self, text) -> str:
        text = re.sub(r"i'd", 'i would', text, re.I | re.A)
        text = re.sub(r"i've", 'i have', text, re.I | re.A)
        text = re.sub(r"you've", 'you would', text, re.I | re.A)
        text = re.sub(r"don't", 'do not', text, re.I | re.A)
        text = re.sub(r"doesn't", 'does not', text, re.I | re.A)
        return text

    def lemmitize(self, text) -> str:
        toks = self.tokenize(text)        
        for i, word in enumerate(toks):
            if (len(word) > 4):
                word = re.sub(r"ing\b", '', word, re.I | re.A)
                word = re.sub(r"ed\b", '', word, re.I | re.A)
                word = re.sub(r"s\b", '', word, re.I | re.A)
                toks[i] = word

        return " ".join(toks)

    def lemmitize_word(self, text) -> str:   # not such a good way, complexity merits using nltk lib
        return text

    def destop(self, text,) -> str:
        words = self.tokenize(text)
        return " ".join([x for x in words if x not in self.stoplist])

    def tokenize(self, text) -> [str]:
        toks = text.split(' ')
        return [t.strip() for t in toks if t != '']

    def encode(self, texts) -> []:
        return self.model.embedding.transform(texts)

    def make_embeddings(self, text) -> ([],[]):
        return self.model.embed(text)

    def load_train_stanford(self, samplesize=239232) -> object:
        self.corpus = 'stanford'
        dictfile = 'stanfordSentimentTreebank/dictionary.txt'
        labelfile = 'stanfordSentimentTreebank/sentiment_labels.txt'

        df_dictionary = pd.read_table(dictfile, delimiter='|').sample(samplesize, random_state=5)
        df_labels = pd.read_table(labelfile, delimiter='|').sample(samplesize, random_state=5)
        df_merged = pd.merge(left=df_dictionary, right=df_labels, left_on='id', right_on='id')
        print('merged to corpus size: %d'%len(df_merged))

        # labels need to be changed from float 0.0->1.0 to 5 classes labelea -2,-1,0,1,2 or some strings
        df_merged['labels'] = pd.cut(df_merged['sentiment'], [0.0,0.2,0.4,0.6,0.8,1.1], labels=["real bad", "bad", "medium", "good","real good"])

        # clean and tokenize
        df_merged['text'] = df_merged['text'].apply(lambda row: self.full_proc(row))

        # turn into embeddings
        onehot_dictionary, headers = self.make_embeddings(df_merged['text'].tolist())

        # split sets
        X_train, X_test, y_train, y_test = train_test_split(onehot_dictionary, df_merged['labels'].astype(str), test_size=0.30, random_state=1)

        self.model.train(X_train, y_train)
        print('trained test score: ', self.model, self.model.score(X_test, y_test))
        return self.model
    
    def predict(self, X) -> ([str],[float]):
        return self.model.predict(X)

    def score(self, X, y) -> float:
        return self.model.score(X,y)


if __name__ == "__main__":
    nlp = FooNLP()
    nlp2 = FooNLP(model=FooModel(TfidfVectorizer))
    nlp3 = FooNLP(model=FooModel(mod=LogisticRegression))

    smodel = nlp.load_train_stanford()
    smodel2 = nlp2.load_train_stanford()
    smodel3 = nlp3.load_train_stanford()
    sents = ['I enjoy happy i love it superstar sunshine','I hate kill die horrible','Do you love or hate me?']
    encoded_vect = nlp.encode(sents)
    encoded_tfid = nlp2.encode(sents)

    print(sents)
    print(encoded_vect)
    print(encoded_tfid)

    # print(smodel.headers)
    print(smodel, smodel.predict(encoded_vect))
    print(smodel2, smodel2.predict(encoded_tfid))
    print(smodel3, smodel3.predict(encoded_vect))

    print('ready for inputs, type ^C or empty line to break out')

    while True:
        txt = input('Enter Text> ')
        if (txt == ''):
            print('quitting see ya')
            break
        encoded_vect = nlp.encode([txt])
        encoded_tfid = nlp2.encode([txt])

        print(smodel.predict(encoded_vect), smodel)
        print(smodel2.predict(encoded_tfid), smodel2)
        print(smodel3.predict(encoded_vect), smodel3)



