'''
Created on 19.11.2018

@author: klauspopp@gmx.de
'''
import os


def create_dirs_and_open_output_file(file_path):
    '''
    Create missing directories to <file_path> and open <file_path> for writing
    @return: file descriptor
    '''
    if os.path.dirname(file_path) != "":
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return open(file_path, 'w')
