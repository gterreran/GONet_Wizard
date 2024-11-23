import operator, inspect
import numpy as np

a = np.array([1,2,3,4])

b = np.array([1,2,3,4])


for el in operator.__all__:
    op = getattr(operator, el)
    p = len(inspect.signature(op).parameters)
    if p == 1:
        try:
            op(a)
        except:
            print(el, 'Not supported by numpy')
    
    if p == 2:
        try:
            op(a,b)
        except:
            print(el, 'between numpy arrays is not supported by numpy')
        
        try:
            op(a,2.2)
        except:
            print(el, 'between a numpy array and a float is not supported by numpy')
        
        try:
            op(a,2)
        except:
            print(el, 'between a numpy array and a float is not supported by numpy')
        
        



