git clone https://github.com/1sh1ro/fucktju250630.git
cd fucktju250630/Agentless

conda create -n agentless python=3.11 
conda activate agentless
conda install -c conda-forge gcc_linux-64 gxx_linux-64
pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:$(pwd)

export DEEPSEEK_API_KEY={key_here}
