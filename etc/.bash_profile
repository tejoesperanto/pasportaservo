source $HOME/.bashrc

# virtualenvwrapper
export WORKON_HOME=/opt/envs
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
source /usr/local/bin/virtualenvwrapper.sh

# Node Version Manager
export NVM_DIR="/home/ps/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm
