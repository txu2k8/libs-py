## **vim-config**
[![](https://img.shields.io/badge/Project-vim_config-yellow.svg)]()
[![](https://img.shields.io/badge/shell-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

A easy vim configuration scripts for the modern python (plus some other goodies)
lot of python, autocompletition, fuzzy finder, debugger, ...

1. [**sh-vim-config**](https://github.com/txu2008/tlib/tree/master/tlib/vim-config/sh-vim-config) FYI: https://github.com/JeffXue/vim-config
2. [**fisa-vim-config**](https://github.com/txu2008/tlib/tree/master/tlib/vim-config/fisa-vim-config) FYI: https://github.com/fisadev/fisa-vim-config (http://fisadev.github.io/fisa-vim-config/)

#### Install
    1. sh-vim-config
        Run the *.sh file by shell, then done. Or replace the vimrc file on linux
    2. fisa-vim-config
        0) You will need a vim compiled with python support. Check it with vim --version | grep +python
            Also, your .vim folder should be empty. If you have one, rename it or move to a different location (to keep a backup, just in case you want to go back).        
        1) Install the required dependencies:
            sudo apt-get install curl vim exuberant-ctags git ack-grep
            sudo pip install pep8 flake8 pyflakes isort yapf
        2) Download the .vimrc file and place it in your linux home folder.
        3) Open vim and it will continue the installation by itself. Wait for it to finish... and done! You now have your new shiny powerful vim :)
        
        Optional: If you want fancy symbols and breadcrumbs on your status line, check this small tutorial.
        Docker: Federico Gonzalez (FedeG) made a docker image which runs vim with this config inside, you can find it here or in docker hub.
    
### Others FYI
    https://github.com/fisadev/fisa-vim-config
    http://fisadev.github.io/fisa-vim-config/    
***
[1]: https://txu2008.github.io