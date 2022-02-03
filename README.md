## Install requirements

Install system libraries:
```sh
apt install sox ffmpeg libcairo2 libcairo2-dev
```

Install Latex distribution:
```sh
apt install texlive-full
```

Install manim 
```sh
git clone git@github.com:vmart20/eola_chapter2.git
cd eola_chapter2
virtualenv -p python2 env
source env/bin/activate
pip install -r requirements.txt

```


## How to Use
Try running the following:
```
python extract_scene.py -w example_scenes.py SquareToCircle
```
Writes in files/movies directory

-p is not working
