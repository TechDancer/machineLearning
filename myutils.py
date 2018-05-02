import time, itertools, os,requests, pandas, io
import matplotlib.pyplot as plt
from sklearn.utils import shuffle
from sklearn.metrics import mean_squared_error,log_loss
import logging as log
import sympy as sp
import numpy as np

#return in array with original result in [0], timing in [1]
def time_fn( fn, *args, **kwargs ):
    start = time.clock()
    results = fn( *args, **kwargs )
    end = time.clock()
    #fn_name = fn.__module__ + "." + fn.__name__
    #print fn_name + ": " + str(end-start) + "s"
    return [results,end-start]

#for data duplications
def churn(d, n):
    for _ in itertools.repeat(None, n):
        d = d.append(d)
    return d

#guess array formatter to 4d%f
def gf(guesses):
    return ["{:0.4f}".format(float(g)) for g in guesses]

def setupBrainData(max=1000):
    if (os.path.isfile("myDataFrame.csv")):
        log.warn('reading cache copy from disk')
        return pandas.read_csv('myDataFrame.csv').head(max)    
    url='http://www.stat.ufl.edu/~winner/data/brainhead.dat'
    data=requests.get(url)
    col_names=('gender', 'age_range', 'head_size', 'brain_weight')
    col_widths=[(8,8),(16,16),(21-24),(29-32)]
    df=pandas.read_fwf(io.StringIO(data.text), names=col_names, colspec=col_widths)
    df.to_csv('myDataFrame.csv')
    return df.head(max)

# copied code from meng - pull in songclass/* lady gaga/class music text data, returns (training[][],yarr[],labels[],fnames[])
def getGagaData(maxrows=200,maxfeatures=4000,gtype=None,stopwords=None):
    import random, sklearn, sklearn.feature_extraction.text, sklearn.naive_bayes
    def append_data(ds,dir,label,size):
        filenames=os.listdir(dir)
        for i,fn in enumerate(filenames):
            if (i>=size):
                break            
            data=open(dir+'/'+fn,'r').read()
            ds.append((data,label,fn))
        return i
    ######## Load the raw data
    dataset=[]
    if (gtype == 1 or gtype == None):
        i = append_data(dataset,'songclass/lyrics/gaga',1,maxrows/2)
        log.warn("gaga test set %i docs"%(i))
    if (gtype == 0 or gtype == None):     
        i = append_data(dataset,'songclass/lyrics/clash',0,maxrows/2)
        log.warn("non gaga test set %i docs"%(i))

    ######## Train the algorithm with the labelled examples (training set)
    data,target,fnames=zip(*dataset)
    vec=sklearn.feature_extraction.text.CountVectorizer(stop_words=stopwords)
    mat=vec.fit_transform(data)
    yarr = list(target)
    data = mat.toarray()
    labels = vec.get_feature_names()[0:maxfeatures]
    # hack trim features by 'maxfeature' param
    if (maxfeatures > len(data[0])):
        maxfeatures = len(data[0]) 
    data = data[:,0:maxfeatures]
    return data,yarr,labels,fnames

#replicate/grow data
def makeFakeData():
    print('setup expanded datasets (dfs[])')
    df = setupBrainData()
    dfs = [df,churn(df,4),churn(df,8),churn(df,12),churn(df,16)]        
    for d in dfs:
        print (d.shape)
    return dfs

# x,y is string column from dataFrame to plot on x,y axes
def plotScatter(initData,xLabel,yLabel):
    fig = plt.figure(figsize=(4,4))
    ax = fig.add_subplot(1,1,1)
    plt.ion()

    #scatter of test pts
    for _,row in initData.iterrows():
        x= row[xLabel]
        y= row[yLabel]
        ax.scatter(x, y)
    plt.pause(0.01)
    return ax

# plot new line Ax+B
def plotLine(ax,A,B,min=0,max=5000):
    if (len(ax.lines) > 0):
        ax.lines.pop()
    ax.plot([min,max],[min*A + B,max*A + B])
    plt.pause(0.01)
    return ax

# generic solver takes in xEvalothesis function, cost func, training matrix, theta array, yarray
def grad_descent4(hFunc, cFunc, trainingMatrix, yArr, step=0.01, loop_limit=50, step_limit=0.00001, batchSize=None):
    guesses = [0.01]*len(trainingMatrix[0])  # @TODO is this right or len(yArr)
    costChange = 1.0
    if (batchSize == None):
        batchSize = len(trainingMatrix)  #@todo can i set this in func param, or reduce to single expr
    batchSize = min(len(trainingMatrix),batchSize)

    # TODO do i really need these 2 here... pass them in?
    ts = sp.symbols('t:'+str(len(trainingMatrix[0])))  #theta weight/parameter array
    xs = sp.symbols('x:'+str(len(trainingMatrix[0])))  #feature array
    
    log.warn('init guesses %s'%(str(guesses)))
    log.warn('init func: %s, training size: %d' %(str(hFunc),trainingMatrix.shape[0]))
    log.debug('ts: %s / xs: %s',ts,xs)

    costF = evalSumF2(cFunc,xs,trainingMatrix,yArr)  # cost fun evaluted for testData
    cost = 0.0+costF.subs(zip(ts,guesses))  
    log.warn('init cost: %f, costF %s',cost,str(costF)) # show first 80 char of cost evaluation

    trainingMatrix = shuffle(trainingMatrix, random_state=0)   
    yArr = shuffle(yArr, random_state=0)   

    i=j=l=0
    while (abs(costChange) > step_limit and l<loop_limit):  # outer loop batch chunk
        i=j=k=0
        k = j+batchSize if j+batchSize<len(trainingMatrix) else len(trainingMatrix)
        dataBatch = trainingMatrix[j:k]
        yBatch = yArr[j:k]
        log.debug('outer - batch %d, j: %d, k: %d'%(len(dataBatch),j,k))

        while (i < len(trainingMatrix)/batchSize):  # inner batch size loop, min 1x loop
            for t,theta in enumerate(ts):
                pd = evalPartialDeriv2(cFunc,theta,ts,xs,dataBatch,guesses,yBatch)
                guesses[t] = guesses[t] - step * pd
            previousCost = cost
            cost = costF.subs(zip(ts,guesses))
            costChange = previousCost-cost
            log.warn('l=%d,bs=%d,costChange=%f,cost=%f, guesses=%s'%(l,batchSize, costChange,cost,gf(guesses)))

            j = k
            k = j+batchSize if j+batchSize<len(trainingMatrix) else len(trainingMatrix)
            dataBatch = trainingMatrix[j:k]
            yBatch = yArr[j:k]
            i += 1
            l += 1
    return guesses

# expnd to avg(sum(f evaluated for xs,testData,yarr)) 
def evalSumF2(f,xs,trainingMatrix,yArr):  # @TODO change testData to matrix
    assert (len(xs) == len(trainingMatrix[0]))
    assert (len(trainingMatrix) == len(yArr))
    n=0.0
    _f = f 
    for i,row in enumerate(trainingMatrix):
        for j,x in enumerate(xs):
            _f = _f.subs(x,row[j])
        n+= _f.subs(sp.symbols('y'),yArr[i])
        log.debug('_f: %s n: %s',_f, n)
        _f = f
        log.info('------ expand: y:(%d) %s to %s ', yArr[i],str(row),str(n))
    n *= (1.0/len(trainingMatrix))
    log.info('f (%d) %s - \n  ->expanded: %s '%(len(trainingMatrix[0]), str(f), str(n)))
    return n 

# generate deriv and sub all x's w/ training data and theta guess values
def evalPartialDeriv2(f,theta,ts,xs,trainingMatrix,guesses,yArr):
    pdcost = evalSumF2(sp.diff(f,theta),xs,trainingMatrix,yArr)
    pdcost = pdcost.subs(zip(ts,guesses))
    log.info ('    --> pdcost %f ;  %s  ;  %s: '%(pdcost,str(f),str(theta)))
    return pdcost

#reference impl for mean_square cost
def gradient_descent_simple(step, xMatrix, yArr, step_limit):
    m = len(xMatrix) # number of samples
    theta = [0.01]*len(xMatrix[0]) # init guesses
    x_transpose = xMatrix.transpose()
    for iter in range(0, step_limit):
        hypothesis = np.dot(xMatrix, theta)
        error = hypothesis - yArr   # error/cost
        J = np.sum(error ** 2) * (2.0 / m)  # sum of errors (total cost)
        gradient = np.dot(x_transpose, error) * (2.0/m)         
        theta = theta - step * gradient  # update
        log.warn("iter %s | J: %.3f | theta %s grad %s" % (iter, J, theta, gradient))
    return theta


# generic solver, errorFunc(y,x), costFunc(y,x), xArr (np.array), yArr (np.array)
def grad_descent5(eFunc, cFunc, xArr, yArr, step=0.01, loop_limit=50, step_limit=0.00001, batchSize=None):
    if (batchSize == None):
        batchSize = len(xArr)  #@todo can i set this in func param, or reduce to single expr
    batchSize = min(len(xArr),batchSize)
    guesses = [0.01]*len(xArr[0])  # initial guess for all 
    costChange = 1.0
    costSum = 1.0  # dummy start
    xArr = shuffle(xArr, random_state=0)  # must shuffle both xArr,yArr together w/ same seed !!
    yArr = shuffle(yArr, random_state=0) 
    
    i=j=l=0
    while (abs(costChange) > step_limit and l<loop_limit):  # outer loop batch chunk
        i=j=k=0
        k = j+batchSize if j+batchSize<len(xArr) else len(xArr)
        xBatch = xArr[j:k]
        yBatch = yArr[j:k]
        log.debug('outer - batch %d, j: %d, k: %d'%(len(xBatch),j,k))

        while (i < len(xArr)/batchSize):  # inner batch size loop, min 1x loop
            previousCost = costSum
            xEval = np.dot(xBatch, guesses)  # array of X*0 "scores"
            error = eFunc(yBatch, xEval)     # errorFunc could be x-y or sig(x)-y   
            costSum = cFunc(yBatch,error+yBatch)  # xEval derived ~= error+yBatch [error = sig(x)-y or x-y which works]
            guesses = guesses - step * np.dot(xBatch.T, error) * 2.0/len(xBatch)  #ng: 0:=0 - a/m * X.T*(g(X*0) - Y)
            costChange = previousCost-costSum
            log.warn('l=%d,i=%d,bs=%d,costChange=%f,cost=%f, guesses=%s'%(l,i,batchSize, costChange,costSum,gf(guesses)))

            j = k
            k = j+batchSize if j+batchSize<len(xArr) else len(xArr)
            xBatch = xArr[j:k]
            yBatch = np.asarray(yArr[j:k])
            i += 1
            l += 1
    return guesses

# replaced by log_loss scikit function, this one is easier because it doesn't need both 0's and 1's...
def sigmoidCost(y,x):
    ret=[]
    for i,x_ in enumerate(x):
        p = sigmoid(x_) 
        cost = -y[i]*np.log(p) - (1-y[i])*np.log(1.0-p)
        ret.append(cost)
    return sum(ret)/len(y)

def sigmoid(x):
    return 1.0 / (1 + np.exp(-x))

## test section
if __name__ == "__main__":
    trainingMatrix = np.array([[0,10],[1,12],[10,5],[12,3]])  # 2 features
    yArr = [1,1,0,0]
    guesses = [0.01]*len(trainingMatrix[0])
    xEval = trainingMatrix.dot(guesses)
    err = log_loss(yArr, xEval)
    log.warn('init err/cost: %f'%err)

    gs = grad_descent5(lambda y,x: sigmoid(x)-y,log_loss,trainingMatrix,yArr,step=0.005,loop_limit=100)    
    log.warn('final: %s'%gs)

    # gs = gradient_descent_simple_log(0.005, trainingMatrix, yArr, 10)
    # log.warn('final: %s'%gs)

    X = np.asmatrix(trainingMatrix)
    Y = yArr
    log.warn ('target Linear Reg sol: %s'% str((X.T.dot(X)).I.dot(X.T).dot(Y)))

    from sklearn.linear_model import LogisticRegression
    log_reg = LogisticRegression()
    log_reg.fit(X,Y)
    print ('scikit solution:',log_reg.coef_)
    print ('scikit intercept?',log_reg.intercept_)

