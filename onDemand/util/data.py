# encoding: utf-8
'''
Created on 19 août 2015

@author: Bertrand Verdu
'''


class MyClass(object):
    '''
    classdocs
    '''

    def __init__(self, params):
        '''
        Constructor
        '''


def remove_unicode(data):
    def conv(char):
        if char in 'ëêéè':
            return 'e'
        elif char in 'ïî':
            return 'i'
        elif char in ':;,.!§%$£=+-+°&~#"':
            return '_'
        elif char in 'öô':
            return 'o'
        elif char in 'äâ':
            return 'a'
        elif char in 'üûù':
            return 'u'
    l = ''
    if isinstance(data, str):
        print('ascii')
        data = data.decode('utf-8')
    for char in data:
        if char in u'-ëïïîöôéèà&!§,?:êüûâä':
            l += conv(char.encode('utf-8'))
        else:
            l += char
    return bytes(l)

if __name__ == '__main__':
    print(remove_unicode(u'Buëch'))
    print(remove_unicode('Marseille'))
    print(remove_unicode('Bu\\xc3\\xabch'))
