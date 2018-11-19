'''
Created on 19.11.2018

@author: klauspopp@gmx.de
'''
import os

def moddyCreateDirsAndOpenOutputFile( filePath ):
    '''
    Create missing directories to <filePath> and open <filePath> for writing
    @return: file descriptor
    '''
    os.makedirs(os.path.dirname(filePath), exist_ok=True);
    return open(filePath, 'w')