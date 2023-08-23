# gl3wxpyg
A playground and testing repo to implement **OpenGL 3.3** in a wxPython interface using pyglet as an OpenGL-wrapper.

## Install dependencies [macOS]
```
cd gl3wxpyg/
git pull
python3 -m venv venv
. ./venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 01_Triangle
Currently this repo has only one example. It shows how to create a OpenGL canvas in wxPython and hand it over to pyglet. 
Simply run: ```python 01_Triangle.py```

![Screenshot of 01_Triangle.py OpenGL example.](/images/230823_01_Triangle.jpg)