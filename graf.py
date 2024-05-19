import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def createGraf(data):
    names, values = ogrigationData(data)
    plt.bar(names, values)
    plt.savefig('static/Image/tmp/graf.png')
    

def ogrigationData(data):
    names = []
    values = []
    for name, value in data:
        if name is not None:
            names.append(name)
            values.append(value)
    return names, values

