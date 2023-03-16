# testbeam-app

A simple web-browser based app to inspect the SiPM-on-tile testbeam data.

## Installation

1. Clone repository:

```
git clone https://github.com/matt-komm/testbeam-app.git
cd testbeam-app
```

2. Download miniconda:

```
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o Miniconda3-latest-Linux-x86_64.sh
```

3. Install miniconda in the current directory under env:

```
bash Miniconda3-latest-Linux-x86_64.sh -p $PWD/env -b
```

4. Setup environment:

```
export PATH=$PWD/env/bin:$PATH
conda env create -f testbeam-app/environment.yml
```

## Enter environment

```
export PATH=$PWD/env/bin:$PATH
source activate tb
```

Specify the basepath of the data directories

```
export QLDATA=<path to data>
```

## Start the server

```
bokeh serve quickLook.py
```
