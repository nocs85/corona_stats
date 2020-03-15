# Setup

## debian/ubuntu

```
sudo apt-get install python3
sudo apt-get install python3-pip
pip3 install requests
pip3 install matplotlib
```

## WSL

Install your favourite WSL: https://docs.microsoft.com/en-us/windows/wsl/install-win10

Download XServer for windows: https://sourceforge.net/projects/xming/

Do not forget to redirect your output to the (just installed) X server 
```
export DISPLAY=localhost:0.0
```
