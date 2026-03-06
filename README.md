## AgiBot Challenge ICRA 2026

This repository contains code and utilities for the **AgiBot Challenge ICRA 2026**.

### Official Links

- **Challenge website**: [`https://agibot-world.com/challenge2026`](https://agibot-world.com/challenge2026)
- **Dataset**: [`https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026`](https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026)
- **Genie simulator**: [`https://agibot-world.com/genie-sim`](https://agibot-world.com/genie-sim)
- **Baseline model (ACoT-VLA)**: [`https://github.com/AgibotTech/ACoT-VLA`](https://github.com/AgibotTech/ACoT-VLA)

---

### 1. Environment Setup (CUDA)

#### 1.1. Create a Python environment

This project currently targets **Python 3.12**.

You can use either `conda` or `venv`. Below is an example using `conda`:

```bash
conda create -n agibot-icra2026 python=3.12 -y
conda activate agibot-icra2026
```

If you prefer `venv`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

#### 1.2. Install CUDA-enabled PyTorch

Follow the official PyTorch instructions for your system and CUDA toolkit version:  
[`https://pytorch.org/get-started/locally/`](https://pytorch.org/get-started/locally/)

For example, for CUDA 12.1:

```bash
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

Make sure that:

- Your NVIDIA drivers are correctly installed.
- `nvidia-smi` works and reports the expected GPU(s).
- The installed PyTorch build reports CUDA support:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

#### 1.3. Install project dependencies

From the repository root (where `pyproject.toml` lives):

```bash
pip install -e ".[dev]"
```

If you just need the runtime (without dev extras):

```bash
pip install -e .
```

---

### 2. Using the Dataset

The main dataset is hosted on Hugging Face:

- [`https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026`](https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026)

You can access it directly via the `datasets` library:

```python
from datasets import load_dataset

ds = load_dataset("agibot-world/AgiBotWorldChallenge-2026")
print(ds)
```

Refer to the dataset card for details on splits, modalities, and licenses.

---

### 3. Genie Simulator

The Genie simulator used in this challenge is documented at:

- [`https://agibot-world.com/genie-sim`](https://agibot-world.com/genie-sim)

Please follow the official simulator documentation for:

- Installation instructions.
- Supported environments and tasks.
- How to connect your policies or agents to the simulator.

---

### 4. Baseline Model (ACoT-VLA)

The official baseline model for the challenge is **ACoT-VLA**:

- [`https://github.com/AgibotTech/ACoT-VLA`](https://github.com/AgibotTech/ACoT-VLA)

We recommend:

- Reading the repository README for architecture details.
- Checking example training and evaluation scripts.
- Using it as a starting point to build your own improvements for the challenge.

---

### 5. Project Structure

The Python package for this repository is rooted at `agibot/`.  
Make sure your code imports follow this convention, for example:

```python
from agibot import some_module
```

More detailed documentation and examples can be added here as the project evolves.
