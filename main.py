import matplotlib.pyplot as plt
from numpy import sin, cos, tan
import sys
import os
import numpy as np

def cot(x):
    return 1/tan(x)
def sqrt(x):
    return x**0.5

function_str = sys.argv[1]
def my_function(x):
    return eval(function_str)

x = np.linspace(-10, 10, 100)
y = my_function(x)

fig, ax = plt.subplots(facecolor='none')
ax.plot(x, y)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_title('The graph of the function: y = {}'.format(function_str))

ax.set_facecolor('none')
ax.spines['bottom'].set_color('gray')
ax.spines['top'].set_color('gray')
ax.spines['right'].set_color('gray')
ax.spines['left'].set_color('gray')
ax.tick_params(axis='x', colors='gray')
ax.tick_params(axis='y', colors='gray')
ax.title.set_color('gray')
ax.xaxis.label.set_color('gray')
ax.yaxis.label.set_color('gray')

filename = 'graphs{}.png'.format(function_str.replace("*", "_"))

fig.savefig(filename, dpi=300, transparent=True)

plt.close(fig)

print("Path to Graphics:", os.getcwd()+"/"+filename)
