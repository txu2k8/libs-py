#!/bin/bash

brew install vim --with-lua
brew install ctags
brew install pip
pip install dbgp vim-debug pep8 flake8 pyflakes isort requests

if [ ! -d ~/.vim/bundle/Vundle.vim ];then
    git clone https://github.com/gmarik/vundle ~/.vim/bundle/vundle
fi

timeStramp=`date +%Y%m%d%H%M`

if [ -f ~/.vim/vimrc ];then
    mv ~/.vim/vimrc ~/.vim/vimrc_$timeStramp
fi

ln ./vimrc ~/.vim/vimrc
vim +PluginInstall +qall

