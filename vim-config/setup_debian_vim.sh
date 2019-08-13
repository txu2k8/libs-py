#!/bin/bash

vim_python_flag=`vim --version |grep +python |wc -l`
if [ $vim_python_flag -eq 0 ];then
    wget --no-check-certificate https://raw.githubusercontent.com/JeffXue/common-scripts/master/install_python2.7.sh
    chmod +x install_python2.7.sh
    ./install_python2.7.sh  

    wget --no-check-certificate https://raw.githubusercontent.com/JeffXue/common-scripts/master/install_vim7.4.sh
    chmod +x install_vim7.4.sh
    ./install_vim7.4.sh
fi


vim_lua_flag=`vim --version |grep +lua |wc -l`
if [ $vim_lua_flag -eq 0 ];then
    wget --no-check-certificate https://raw.githubusercontent.com/JeffXue/common-scripts/master/install_vim7.4.sh
    chmod +x install_vim7.4.sh
    ./install_vim7.4.sh
fi

apt-get install exuberant-ctags -y
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

